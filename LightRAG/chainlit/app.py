import os
import json
from typing import Dict, List, Optional

import chainlit as cl
import chainlit.data as cl_data
from chainlit.step import StepDict
from chainlit.types import ThreadDict

from typing import Dict, List, Optional

import chainlit as cl
import chainlit.data as cl_data
from chainlit.data.utils import queue_until_user_message
from chainlit.element import Element, ElementDict
from chainlit.socket import persist_user_session
from chainlit.step import StepDict
from chainlit.types import (
    Feedback,
    PageInfo,
    PaginatedResponse,
    Pagination,
    ThreadDict,
    ThreadFilter,
)

from literalai.helper import utc_now

import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm import hf_embedding, gpt_4o_mini_complete
from lightrag.utils import EmbeddingFunc
import numpy as np
import os
import json
from ragutils.utils import load_chat_history, construct_prompt, save_chat_history, simple_token_count, summarize_chat_history, is_url, insert_txt_rag
from transformers import AutoModel, AutoTokenizer
from utils import *

now = utc_now()

deleted_thread_ids=[]
THREAD_HISTORY_JSON_PATH = "./thread_history.json"

def load_thread_history() -> List[Dict]:
    if os.path.exists(THREAD_HISTORY_JSON_PATH):
        with open(THREAD_HISTORY_JSON_PATH, "r") as f:
            return json.load(f)
    return []

# Hàm lưu thread history vào file JSON
def save_thread_history(thread_history: List[Dict]):
    with open(THREAD_HISTORY_JSON_PATH, "w") as f:
        json.dump(thread_history, f, indent=4)

# Đường dẫn file JSON để lưu history
os.environ["OPENAI_API_KEY"] = "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"

class CustomDataLayer(cl_data.BaseDataLayer):
    async def get_user(self, identifier: str):
        return cl.PersistedUser(id="test", createdAt=now, identifier=identifier)

    async def create_user(self, user: cl.User):
        return cl.PersistedUser(id="test", createdAt=now, identifier=user.identifier)

    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ):
        thread = next((t for t in thread_history if t["id"] == thread_id), None)
        if thread:
            if name:
                thread["name"] = name
            if metadata:
                thread["metadata"] = metadata
            if tags:
                thread["tags"] = tags
        else:
            thread_history.append(
                {
                    "id": thread_id,
                    "name": name,
                    "metadata": metadata,
                    "tags": tags,
                    "createdAt": utc_now(),
                    "userId": user_id,
                    "userIdentifier": "admin",
                    "steps": [],
                }
            )

    @cl_data.queue_until_user_message()
    async def create_step(self, step_dict: StepDict):
        # Đảm bảo giá trị counter không bị None
        current_counter = cl.user_session.get("create_step_counter", 0)
        cl.user_session.set("create_step_counter", current_counter + 1)

        thread = next(
            (t for t in thread_history if t["id"] == step_dict.get("threadId")), None
        )
        if thread:
            thread["steps"].append(step_dict)

    async def get_thread_author(self, thread_id: str):
        return "admin"

    async def list_threads(
        self, pagination: Pagination, filters: ThreadFilter
    ) -> PaginatedResponse[ThreadDict]:
        return PaginatedResponse(
            data=[t for t in thread_history if t["id"] not in deleted_thread_ids],
            pageInfo=PageInfo(hasNextPage=False, startCursor=None, endCursor=None),
        )

    async def get_thread(self, thread_id: str):
        thread = next((t for t in thread_history if t["id"] == thread_id), None)
        if not thread:
            return None
        thread["steps"] = sorted(thread["steps"], key=lambda x: x["createdAt"])
        return thread

    async def delete_thread(self, thread_id: str):
        global thread_history
        thread_history = [t for t in thread_history if t["id"] != thread_id]
        save_thread_history(thread_history)

    async def delete_feedback(
        self,
        feedback_id: str,
    ) -> bool:
        return True

    async def upsert_feedback(
        self,
        feedback: Feedback,
    ) -> str:
        return ""

    @queue_until_user_message()
    async def create_element(self, element: "Element"):
        pass

    async def get_element(
        self, thread_id: str, element_id: str
    ) -> Optional["ElementDict"]:
        pass

    @queue_until_user_message()
    async def delete_element(self, element_id: str, thread_id: Optional[str] = None):
        pass

    @queue_until_user_message()
    async def update_step(self, step_dict: "StepDict"):
        pass

    @queue_until_user_message()
    async def delete_step(self, step_id: str):
        pass

    async def build_debug_url(self) -> str:
        return ""

cl_data._data_layer = CustomDataLayer()
rag_manager = RAGManager()
thread_history = load_thread_history()


@cl.on_chat_start
async def on_chat_start():
    thread_id = cl.context.session.thread_id
    # Khởi tạo RAG instance nếu chưa có
    rag_manager.create_rag(thread_id)
    await cl.Message("Xin chào, hãy trò chuyện với tôi!").send()


@cl.on_message
async def handle_message(message: cl.Message):
    thread_id = cl.context.session.thread_id
    workspace = '../assets/workspace{}'.format(message.thread_id)

    database = os.path.join(workspace, "database")
    chat_history_file = os.path.join(database, "chat_history.json")
    chat_history = load_chat_history(chat_history_file)

    # Lấy RAG instance từ RAGManager
    rag = rag_manager.get_rag(thread_id)

    if not rag:
        await cl.Message(content="RAG instance or workspace not initialized. Please restart the chat session.").send()
        return
    prompt = message.content

    # Xử lý tin nhắn hoặc tải dữ liệu vào RAG
    if message.elements:
        text_files = [file for file in message.elements if "text/plain" in file.mime]
        if text_files:
            for txt in text_files:
                link = txt.path
                await insert_data_to_rag(link, workspace, rag)
        pdf_files = [file for file in message.elements if "application/pdf" in file.mime]
        if pdf_files:
            for pdf in pdf_files:
                link = pdf.path
                await insert_data_to_rag(link, workspace, rag)
    query_split = prompt.split(' ')
    for sub_query in query_split:
        if is_url(sub_query):
            link = sub_query
            prompt = prompt.replace(link, "")
            await insert_data_to_rag(link, workspace, rag)

    # Tải lịch sử hội thoại
    chat_history = load_chat_history(chat_history_file)

    # Đếm token trong lịch sử chat
    total_tokens = simple_token_count(
        "\n".join([message['content'] for message in chat_history])
    )
    print(f"Tổng số token trong lịch sử: {total_tokens}")

    if total_tokens > 5000:
        summarized_history = await summarize_chat_history(chat_history)
        chat_history = summarized_history
        save_chat_history(chat_history, chat_history_file)
        print("Lịch sử hội thoại đã được tóm tắt.")

    # Tạo prompt cho RAG
    prompt = construct_prompt(prompt, chat_history)

    response_message = cl.Message(content="")

    # Thực hiện truy vấn với RAG
    response = await rag.aquery(
        prompt,
        param=QueryParam(mode="hybrid"),
    )
    print(response)

    assistant_content = ""
    for token in response:
        assistant_content += token
        await response_message.stream_token(token)

    # Gửi phản hồi
    response_message.content = assistant_content
    await response_message.send()

    # Lưu lịch sử hội thoại
    new_entries = [
        {"role": "user", "content": message.content},
        {"role": "system", "content": assistant_content},
    ]
    save_chat_history(new_entries, chat_history_file)
    save_thread_history(thread_history)

@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
    if (username, password) == ("admin", "admin"):
        return cl.User(identifier="admin")
    else:
        return None

@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    thread_id = cl.context.session.thread_id
    # Khởi tạo RAG instance nếu chưa có
    rag_manager.create_rag(thread_id)
    pass


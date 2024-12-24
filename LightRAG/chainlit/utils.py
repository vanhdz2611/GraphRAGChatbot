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
from processData.extractData import crawl_to_txt, convert_to_txt
from crawler.luatvncrawler import LuatvnCrawler
from crawler.vbplvncrawler import VbplvnCrawler
from crawler.lawnetcrawler import LawnetCrawler
from crawler.dlplcrawler import DLPLCrawler
from crawler.miccrawler import MicCrawler
import os
import json
from ragutils.utils import load_chat_history, construct_prompt, save_chat_history, simple_token_count, summarize_chat_history, is_url, insert_txt_rag
from transformers import AutoModel, AutoTokenizer

THREAD_HISTORY_JSON_PATH = "./thread_history.json"
now = utc_now()

deleted_thread_ids=[]


def init_workspace(workspace):
    if not os.path.exists(workspace):
        os.makedirs(workspace)
        print(f"Thư mục '{workspace}' đã được tạo thành công.")

    database = os.path.join(workspace, "database")
    if not os.path.exists(database):
        os.makedirs(database)
        print(f"Thư mục '{database}' đã được tạo thành công.")

    originalData = os.path.join(workspace, "originalData")
    if not os.path.exists(originalData):
        os.makedirs(originalData)
        print(f"Thư mục '{originalData}' đã được tạo thành công.")

    chat_history_file = os.path.join(database, "chat_history.json")
    if not os.path.exists(chat_history_file):
        with open(chat_history_file, "w", encoding="utf-8") as f:
            json.dump([] ,f, ensure_ascii=False, indent=4)
        print(f"File {chat_history_file} đã được tạo thành công.")
    return database, originalData, chat_history_file

async def insert_data_to_rag(link, originalData, rag):
    if is_url(link): # nếu là link web
        if "https://luatvietnam.vn" in link:
            crawler = LuatvnCrawler(link, originalData)
            crawler.crawl_links_to_txt()
        elif "https://vbpl.vn/" in link:
            crawler = VbplvnCrawler(link, originalData)
            crawler.crawl_links_to_txt()
        elif "https://mic.gov.vn" in link:
            crawler = MicCrawler(link, originalData)
            crawler.crawl_links_to_txt()
        elif "https://dulieuphapluat.vn" in link:
            crawler = DLPLCrawler(link, originalData)
            crawler.crawl_links_to_txt()
        elif "https://lawnet.vn" in link:
            crawler = LawnetCrawler(link, originalData)
            crawler.crawl_links_to_txt()
        else:
            crawl_to_txt(link, originalData)
            print("Trường hợp link khác domain")
    else: # nếu là link local
        convert_to_txt(link, originalData)
    
    await insert_txt_rag(rag, originalData)
    
# Hàm load thread history từ file JSON
def load_thread_history() -> List[Dict]:
    if os.path.exists(THREAD_HISTORY_JSON_PATH):
        with open(THREAD_HISTORY_JSON_PATH, "r") as f:
            return json.load(f)
    return []

# Hàm lưu thread history vào file JSON
def save_thread_history(thread_history: List[Dict]):
    with open(THREAD_HISTORY_JSON_PATH, "w") as f:
        json.dump(thread_history, f, indent=4)

# Load dữ liệu ban đầu
thread_history = load_thread_history()

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
        deleted_thread_ids.append(thread_id)

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


class RAGManager:
    def __init__(self):
        # Dùng dictionary để lưu RAG instances theo thread_id
        self.instances = {}

    def get_rag(self, thread_id: str):
        # Trả về instance nếu đã tồn tại
        return self.instances.get(thread_id, None)

    def create_rag(self, thread_id: str):
        # Nếu chưa tồn tại, tạo một instance mới và lưu lại
            # embedding_func=EmbeddingFunc(
            #     embedding_dim=384,
            #     max_token_size=512,
            #     func=lambda texts: hf_embedding(
            #         texts,
            #         tokenizer=AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small"),
            #         embed_model=AutoModel.from_pretrained("intfloat/multilingual-e5-small")
            #     )
            # )
        workspace = '../assets/workspace{}'.format(thread_id)
        database, originalData, chat_history_file = init_workspace(workspace)
        rag = LightRAG(
            embedding_func=EmbeddingFunc(
                embedding_dim=384,
                max_token_size=512,
                func=lambda texts: hf_embedding(
                    texts,
                    tokenizer=AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small"),
                    embed_model=AutoModel.from_pretrained("intfloat/multilingual-e5-small")
                )
            ),
            working_dir=database,
            llm_model_func=gpt_4o_mini_complete,
        )
        self.instances[thread_id] = rag
        return self.instances[thread_id]

    def remove_rag(self, thread_id: str):
        # Xóa instance khi không cần thiết
        if thread_id in self.instances:
            del self.instances[thread_id]

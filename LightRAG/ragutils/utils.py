import os
import json
from lightrag.llm import gpt_4o_mini_complete
import re

def load_chat_history(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def construct_prompt(user_input, chat_history):
    prompt = "Lịch sử chat:\n"
    for message in chat_history:
        if message["role"] == "user":
            prompt += f"user: {message['content']}\n"
        elif message["role"] == "system":
            prompt += f"system: {message['content']}\n"
    prompt += f" Câu hỏi hiện tại:\n user: {user_input}\nsystem:"
    return prompt

def save_chat_history(new_entries, file_path):
    with open(file_path, 'r') as f:
        chat_history = json.load(f)
        chat_history.extend(new_entries)
        with open(file_path, 'w') as f:
            json.dump(chat_history, f, indent=4, ensure_ascii=False)

def simple_token_count(text):
    return len(text.split())

async def summarize_chat_history(chat_history):
    full_history = "\n".join(
        [f"{message['role']}: {message['content']}" for message in chat_history]
    )
    prompt = (
        "Bạn là một AI trợ lý, nhiệm vụ của bạn là tóm tắt cuộc hội thoại dưới đây một cách ngắn gọn, "
        "giữ lại các ý chính và thông tin quan trọng sao cho số lượng token khoảng 3000 tokens:\n\n"
        f"{full_history}"
    )

    print("Đang tóm tắt hội thoại...")
    response = await gpt_4o_mini_complete(prompt)
    return [{"role": "system", "content": response}]

def is_url(input):
    """
    Kiểm tra input có phải là URL web hay không.
    """
    url_pattern = re.compile(
        r'^(https?|ftp)://'  # Bắt đầu bằng http://, https:// hoặc ftp://
        r'[a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})'  # Tên miền
        r'(:\d+)?(/.*)?$'  # Cổng và đường dẫn (tùy chọn)
    )
    return re.match(url_pattern, input) is not None



async def insert_txt_rag(rag, originalData):
    file_contents = []
    # Lặp qua tất cả các file trong thư mục
    for filename in os.listdir(originalData):
        if filename.endswith(".txt"):  # Chỉ xử lý các file có đuôi .txt
            filepath = os.path.join(originalData, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                file_contents.append(file.read())
    print(len(file_contents))
    # Insert tất cả nội dung vào RAG
    await rag.ainsert(file_contents)
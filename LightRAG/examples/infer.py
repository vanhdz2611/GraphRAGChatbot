import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from processData.extractData import crawl_to_txt, convert_to_txt
from crawler.luatvncrawler import LuatvnCrawler
from crawler.vbplvncrawler import VbplvnCrawler
import os
import json
from ragutils.utils import load_chat_history, construct_prompt, save_chat_history, simple_token_count, summarize_chat_history, is_url, insert_txt_rag
from lightrag.llm import hf_embedding, gpt_4o_mini_complete
from transformers import AutoModel, AutoTokenizer

#export PYTHONPATH=$PYTHONPATH:
os.environ["OPENAI_API_KEY"] = "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"

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
        else:
            crawl_to_txt(link, originalData)
            print("Trường hợp link khác domain")
    else: # nếu là link local
        convert_to_txt(link, originalData)
    
    await insert_txt_rag(rag, originalData)

async def main(rag, workspace, user_query):
    try:
        database = os.path.join(workspace, "database")
        chat_history_file = os.path.join(database, "chat_history.json")

        chat_history = load_chat_history(chat_history_file)
        
        # Đếm token trong lịch sử chat
        total_tokens = simple_token_count(
            "\n".join([message['content'] for message in chat_history])
        )
        print(f"Tổng số token trong lịch sử: {total_tokens}")

        if total_tokens > 5000:
            summarized_history = await summarize_chat_history(chat_history)
            chat_history = summarized_history

            with open(chat_history_file, "w", encoding="utf-8") as f:
                json.dump(chat_history, f, ensure_ascii=False, indent=4)
            
            print("Lịch sử hội thoại đã được tóm tắt và thay thế trong file.")


        prompt = construct_prompt(user_query, chat_history)
        response = await rag.aquery(
            prompt,
            param=QueryParam(mode="hybrid"),
        )

        new_entries = [
                    {"role": "User", "content": user_query},
                    {"role": "AI", "content": response},
                ]
        save_chat_history(new_entries, chat_history_file)

        print("------------------------ Chat History ------------------------")
        chat_history = load_chat_history(chat_history_file)
        for message in chat_history:
            print(f"{message['role']}: {message['content']}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    workspace = '/mnt/dunghd/LightRAG/assets/test4hf'
    link = 'https://vbpl.vn/hagiang/Pages/vbpq-toanvan.aspx?ItemID=172992'
    rag = LightRAG(
        working_dir=init_workspace(workspace)[0],
        llm_model_func=gpt_4o_mini_complete,
        embedding_func=EmbeddingFunc(
            embedding_dim=384,
            max_token_size=512,
            func=lambda texts: hf_embedding(
                texts,
                tokenizer=AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small"),
                embed_model=AutoModel.from_pretrained("intfloat/multilingual-e5-small")
            ),
        ),
    )


    # asyncio.run(insert_data_to_rag(link, init_workspace(workspace)[1], rag))
    asyncio.run(main(rag, workspace, "Tôi tên là gì?"))

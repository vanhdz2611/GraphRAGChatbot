import os

from lightrag import LightRAG, QueryParam
from lightrag.llm import hf_embedding, gpt_4o_mini_complete
from lightrag.utils import EmbeddingFunc
from transformers import AutoModel, AutoTokenizer
os.environ["OPENAI_API_KEY"] = "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"

WORKING_DIR = "/mnt/dunghd/LightRAG/assets/test1"

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

rag = LightRAG(
    working_dir=WORKING_DIR,
    llm_model_func=gpt_4o_mini_complete,
        embedding_func=EmbeddingFunc(
            embedding_dim=768,
            max_token_size=8192,
            func=lambda texts: hf_embedding(
                texts,
                tokenizer=AutoTokenizer.from_pretrained(
                    "dangvantuan/vietnamese-document-embedding",
                    trust_remote_code=True
                ),
                embed_model=AutoModel.from_pretrained(
                    "dangvantuan/vietnamese-document-embedding",
                    trust_remote_code=True
                ),
            ),
        ),
    )



# with open("/mnt/dunghd/LightRAG/bogiaoducdaotao_Pages_vbpq_toanvan_aspx_ItemID_149789.txt", "r", encoding="utf-8") as f:
#     rag.insert(f.read())


# Perform hybrid search
print(
    rag.query("tìm trong chat history xem tôi tên là gì?", param=QueryParam(mode="hybrid"))
)

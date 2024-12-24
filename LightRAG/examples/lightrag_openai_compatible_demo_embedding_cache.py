import os
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm import openai_complete_if_cache, openai_embedding, gpt_4o_mini_complete
from lightrag.utils import EmbeddingFunc
import numpy as np
from lightrag.llm import hf_embedding
from transformers import AutoModel, AutoTokenizer

os.environ["OPENAI_API_KEY"] = "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"

WORKING_DIR = "/mnt/dunghd/LightRAG/assets/test1"
if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)


async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], keyword_extraction=False, **kwargs
) -> str:
    return await openai_complete_if_cache(
        "gpt-4o-mini-2024-07-18",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
         **kwargs,
    )

async def main():
    try:
        rag = LightRAG(
            working_dir=WORKING_DIR,
            embedding_cache_config={
                "enabled": True,
                "similarity_threshold": 0.90,
            },
            llm_model_func=llm_model_func,
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

        with open("/mnt/dunghd/LightRAG/bogiaoducdaotao_Pages_vbpq_toanvan_aspx_ItemID_148690.txt", "r", encoding="utf-8") as f:
             await rag.ainsert(f.read())

        # Perform hybrid search
        print(
            await rag.aquery(
                "Dataset của tôi có gì",
                param=QueryParam(mode="hybrid"),
            )
        )
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())

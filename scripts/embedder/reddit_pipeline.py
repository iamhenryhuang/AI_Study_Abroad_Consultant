#!/usr/bin/env python3
"""
Reddit 資料的 Chunking + Embedding 流水線。
"""
import json
import sys
from pathlib import Path

# 讓 scripts 目錄在 path 中
CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
ROOT_DIR = SCRIPTS_DIR.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db.connection import get_connection
from langchain_text_splitters import RecursiveCharacterTextSplitter
from embedder.store import upsert_chunks
from embedder.vectorize import embed_texts

# Reddit 貼文通常較長且包含完整案例，增加 chunk_size 以維持內容完整性
_reddit_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=150,
    separators=["\n\n", "\n", "。", ".", " ", ""],
)

def run_reddit_pipeline(data_dirname: str = "reddit_data") -> bool:
    """讀取 reddit_data 下的所有 JSON，切片 → 向量化 → 寫入 DB。"""
    data_dir = ROOT_DIR / data_dirname
    if not data_dir.is_dir():
        print(f"找不到目錄 {data_dir}")
        return False

    json_files = sorted(data_dir.glob("*_reddit.json"))
    if not json_files:
        print(f"目錄 {data_dir} 下沒有符合 *_reddit.json 的檔案")
        return False

    conn = get_connection()
    if not conn:
        print("無法連線至資料庫，請確認 .env 中的 DATABASE_URL。")
        return False

    total_chunks = 0
    try:
        for path in json_files:
            # 從檔名解析基礎名稱，例如 uiuc_reddit.json -> uiuc
            base_name = path.stem.replace("_reddit", "")
            
            # 嘗試從對應的 data/base_name.json 讀取正式的 school_id
            official_data_path = ROOT_DIR / "data" / f"{base_name}.json"
            if official_data_path.exists():
                try:
                    official_data = json.loads(official_data_path.read_text(encoding="utf-8"))
                    school_id = official_data.get("school_id", base_name)
                    university_name = official_data.get("university", base_name)
                except Exception as e:
                    print(f"  警告: 無法讀取 {official_data_path}: {e}")
                    school_id = base_name
                    university_name = base_name
            else:
                school_id = base_name
                university_name = base_name

            print(f"正在處理學校: {university_name} (ID: {school_id}, 檔案: {path.name})")
            
            posts = json.loads(path.read_text(encoding="utf-8"))
            if not posts:
                print(f"  [{school_id}] 檔案內容為空，跳過。")
                continue

            # 將所有貼文組合起來
            combined_text = ""
            for post in posts:
                title = post.get("title", "")
                content = post.get("content", "")
                
                post_text = f"Title: {title}\nContent: {content}\n\n"
                combined_text += post_text

            if not combined_text.strip():
                print(f"  [{school_id}] 無有效內容，跳過。")
                continue

            # 1. Chunking
            chunks = _reddit_splitter.split_text(combined_text)
            print(f"  [{school_id}] 切成 {len(chunks)} 個 chunk")

            # 2. Embedding
            print(f"  [{school_id}] 向量化中...")
            embeddings = embed_texts(chunks)

            # 3. 寫入 DB，source 設為 'reddit'
            # Reddit 資料暫時不提供像官方資料那樣的結構化 meta，設為 None 或基本的 school_id
            meta = {"school_id": school_id, "source": "reddit"}
            
            n = upsert_chunks(conn, school_id, chunks, embeddings, meta, source="reddit")
            total_chunks += n
            print(f"  [{school_id}] ✓ 已寫入 {n} 筆 reddit chunk")

        print(f"\n完成！共處理 {total_chunks} 筆 reddit chunk。")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Reddit Pipeline 失敗: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    run_reddit_pipeline()

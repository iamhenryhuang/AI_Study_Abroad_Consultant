"""共用：專案根目錄、載入 .env、取得連線。"""
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# 專案根目錄（scripts/db/ -> 上兩層）
ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"連線錯誤: {e}")
        return None

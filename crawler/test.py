import asyncio
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from browser_use import Agent

load_dotenv()

async def main():
    # 1. 建立物件 (這是最標準的定義方式)
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=os.environ.get("GROQ_API_KEY")
    )


    # 3. 初始化 Agent (只傳入核心參數，避開錯誤的 BrowserConfig)
    agent = Agent(
        task="前往 https://www.gradoffice.caltech.edu/ 找到 CS 碩士的入學 TOEFL 要求數字。",
        llm=llm,
    )
    
    # 4. 執行
    try:
        result = await agent.run()
        print("\n--- 🕵️ 爬取結果 ---")
        print(result)
    except Exception as e:
        print(f"❌ 執行時發生錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy 
from crawl4ai import LLMConfig
from crawl4ai.chunking_strategy import RegexChunking
from crawl4ai.content_filter_strategy import PruningContentFilter
#from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerationStrategy
from pydantic import BaseModel, Field
from typing import Optional, List
import litellm
import os
import sys

import requests
from get_website import get_website
from dotenv import load_dotenv
from pathlib import Path
from bs4 import BeautifulSoup


#litellm._turn_on_debug()

load_dotenv()
os.environ["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY")

class ConsolidatedAdmissionPost(BaseModel):
    applicant_id: str
    gpa: Optional[float]
    toefl: Optional[int]
    ielts: Optional[float]
    gre: Optional[str]
    admissions: List[str] = Field(description="錄取的學校與學位")
    rejections: List[str] = Field(description="拒絕的學校與學位")
    key_advice: List[str] = Field(description="作者提到的檢討或建議事項")
    pros: List[str] = Field(description="這間學校的優點")
    cons: List[str] = Field(description="這間學校的缺點")

# --- 傳統方法：快速抓取連結 ---
def get_ptt_links(keyword, board="studyabroad"):
    url = f"https://www.ptt.cc/bbs/{board}/search?q={keyword}"
    # PTT 必備：過 18 歲的 Cookie
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    cookies = {'over18': '1'}
    
    print(f"📡 正在發送傳統 Request 搜尋: {keyword}")
    res = requests.get(url, headers=headers, cookies=cookies)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    links = []
    # 這裡就是傳統爬蟲的精髓：精準切片
    for entry in soup.select('div.r-ent div.title a'):
        title = entry.text.strip()

        if "CS" not in title and "Computer Science" not in title:
            continue

        links.append(f"https://www.ptt.cc{entry['href']}")
    
    return links

# --- 現代 AI 方法：分析內文 ---
async def analyze_posts(urls):
    api_key = os.getenv("GROQ_API_KEY")
    if not urls:
        print("沒有找到任何連結。")
        return

    # AI 配置
    strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(provider="groq/llama-3.1-8b-instant"),
        schema=ConsolidatedAdmissionPost.model_json_schema(),
        extraction_type="schema", 
        instruction="""
        請將整篇 PTT 文章彙整為一個 JSON 物件。
        1. 提取 GPA、TOEFL、GRE 等量化指標。
        2. 整理錄取(Admission)與拒絕(Rejection)的清單。
        3. 請整理出作者的建議事項，不要遺漏
        4. 請整理出這間學校的優點和缺點 並列典表示
        """
    )

    async with AsyncWebCrawler() as crawler:
        for url in urls[:5]:  
            print(f" AI 正在分析文章: {url}")
            result = await crawler.arun(
                url=url,
                config=CrawlerRunConfig(extraction_strategy=strategy)
            )
            if result.success:

                print(f"✅ 結果: {result.extracted_content}")
            await asyncio.sleep(5) 
        


# --- 執行 ---
if __name__ == "__main__":
    # 第一步：傳統找網址
    target_urls = get_ptt_links("CMU")
    print(f"✅ 找到 {len(target_urls)} 筆網址")
    
    # 第二步：非同步 AI 分析
    asyncio.run(analyze_posts(target_urls))
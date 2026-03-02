from __future__ import annotations # 解決 ForwardRef 的魔術代碼
import asyncio
import json
import os
import time
from urllib.parse import urljoin

from DrissionPage import ChromiumPage, ChromiumOptions
from bs4 import BeautifulSoup

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from dotenv import load_dotenv
from typing import Optional, List
from pydantic import BaseModel, Field

# 載入環境變數
load_dotenv()

# =========================
# Pydantic 資料結構 (參考 PTT 版)
# =========================
class ConsolidatedAdmissionPost(BaseModel):
    applicant_id: Optional[str] = None
    gpa: Optional[float] = None
    toefl: Optional[int] = None
    gre: Optional[str] = None
    admissions: List[str] = Field(description="錄取的學校與學位")
    rejections: List[str] = Field(description="拒絕的學校與學位")
    key_advice: List[str] = Field(description="作者提到的建議")
    original_school: Optional[str] = Field(None, description="本科學校名稱")

# =========================
# 傳統方法：使用 DrissionPage 獲取內容與解鎖
# =========================
def get_1point3_links(page, fid=82):
    url = f"https://www.1point3acres.com/bbs/forum.php?mod=forumdisplay&fid={fid}"
    print(f"📡 正在搜尋列表頁...")
    page.get(url)
    time.sleep(2)
    
    soup = BeautifulSoup(page.html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        if "thread-" in a["href"] and "-1-1.html" in a["href"]:
            full_url = urljoin("https://www.1point3acres.com/bbs/", a["href"])
            links.append(full_url)
    return list(set(links)) # 去重

def get_thread_html_content(page, url):
    print(f"📥 正在讀取文章並解鎖隱藏內容: {url}")
    page.get(url)
    time.sleep(2)
    
    # 模仿你提到的「點擊查看」處理
    buttons = page.eles('text:点击查看')
    for btn in buttons:
        try:
            btn.click(by_js=True)
            page.wait(1)
        except: pass
    
    return page.html

# =========================
# 現代 AI 方法：分析內文 (參考你的 PTT 正確版本)
# =========================
async def analyze_1point3_posts(html_contents):
    # AI 配置 - 採用與你範例一致的寫法
    strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(provider="groq/llama-3.1-8b-instant"),
        schema=ConsolidatedAdmissionPost.model_json_schema(),
        extraction_type="schema",
        instruction="""
        請將這篇一畝三分地的錄取匯報文章彙整為 JSON。
        1. 提取 GPA、TOEFL (T单项)、GRE (G单项) 等量化指標。
        2. 整理錄取(Admissions)與拒絕(Rejections)清單。
        3. 提取作者的本科學校 (Original School)。
        """
    )

    async with AsyncWebCrawler() as crawler:
        all_results = []
        for html in html_contents:
            print(f"🤖 AI 正在分析內容...")
            # 注意：這裡使用 url="raw://" 傳遞我們已經抓好的 HTML
            result = await crawler.arun(
                url=f"raw://{html}",
                config=CrawlerRunConfig(extraction_strategy=strategy)
            )
            
            if result.success:
                print(f"✅ 抽取成功: {result.extracted_content[:100]}...")
                all_results.append(json.loads(result.extracted_content))
            
            await asyncio.sleep(2) # 避免 Groq 頻率限制
        return all_results

# =========================
# 執行主流程
# =========================
async def main_async():
    # 初始化 DrissionPage
    co = ChromiumOptions()
    co.set_user_data_path("acres_profile")
    page = ChromiumPage(co)

    # 第一步：登入 (一畝三分地必須)
    page.get("https://auth.1point3acres.com/login")
    print("請在瀏覽器完成登入與 Cloudflare 驗證...")
    input("👉 好了嗎？按 Enter 繼續...")

    # 第二步：獲取網址
    target_urls = get_1point3_links(page)
    print(f"✅ 找到 {len(target_urls)} 筆網址")

    # 第三步：獲取所有 HTML (因為我們需要 DrissionPage 解鎖，所以先抓 HTML)
    html_list = []
    for url in target_urls[:3]: # 測試前 3 篇
        html_content = get_thread_html_content(page, url)
        html_list.append(html_content)

    # 第四步：非同步 AI 分析
    final_data = await analyze_1point3_posts(html_list)

    # 儲存結果
    with open("1point3_final_analysis.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print("\n🎉 全部任務完成！資料已存入 json 檔。")
    page.quit()

if __name__ == "__main__":
    asyncio.run(main_async())
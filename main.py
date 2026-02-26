import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse
import json
import re

async def get_page_content(page, url):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        })

        # 增加等待時間，讓頁面完整加載
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        # --- 核心修改：自動尋找並點擊所有具備「下拉/展開」特徵的元素 ---
        # 遍歷頁面上所有可能是開關的元素 (Accordion, Dropdown, Menu items)
        expandable_selectors = [
            "button[aria-expanded='false']",
            ".accordion-header",
            ".dropdown-toggle",
            ".menu-item-has-children > a",
            "[data-toggle='collapse']",
            "span:has-text('more')",
            "i.fa-chevron-down"
        ]
        
        for selector in expandable_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    if await el.is_visible():
                        # 使用 force=True 強制點擊隱藏或被遮擋的按鈕
                        await el.click(force=True)
                        # 給予短暫時間讓選單動畫跑完
                        await asyncio.sleep(0.4)
            except:
                continue

        # 再次捲動頁面，確保點開後的內容如果長度增加，也能被渲染
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)

        # --- 抓取所有文字，包含原本隱藏但現在被點開的部分 ---
        content = await page.evaluate("""
            () => {
                // 排除不必要的雜訊標籤
                const ignoreSelectors = 'script, style, nav, footer, header, .footer, .header, noscript';
                const clones = document.body.cloneNode(true);
                clones.querySelectorAll(ignoreSelectors).forEach(el => el.remove());
                
                // 為了抓取選單文字，我們不限制在 main 區塊，直接抓 body 的完整 innerText
                return clones.innerText;
            }
        """)

        if content:
            # 清理文字：移除重複換行
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            content = "\n".join(lines)
            
        return content if len(content) > 50 else f"--- 內容過短 ({len(content)}) ---"

    except Exception as e:
        print(f"無法抓取 {url}: {e}")
        return None

async def main(start_urls):
    async with async_playwright() as p:
        # headless=False 讓你檢查視窗，slow_mo 讓你跟得上速度
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context()
        page = await context.new_page()

        final_data = {}

        for root_url in start_urls:
            parsed_root = urlparse(root_url)
            domain = parsed_root.netloc
            base_path = parsed_root.path.rstrip('/')
            
            visited = set()
            to_visit = [root_url]

            while to_visit and len(visited) < 30: 
                current_url = to_visit.pop(0)
                if current_url in visited:
                    continue

                print(f"正在掃描: {current_url}")
                text = await get_page_content(page, current_url)
                
                if text:
                    visited.add(current_url)
                    final_data[current_url] = text

                    # 提取下層連結
                    hrefs = await page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
                    for href in hrefs:
                        full_url = href.split('#')[0].rstrip('/')
                        parsed = urlparse(full_url)
                        # 確保遞迴邏輯：同網域且路徑向下
                        if parsed.netloc == domain and parsed.path.startswith(base_path):
                            if full_url not in visited and full_url not in to_visit:
                                to_visit.append(full_url)

        await browser.close()
        return final_data

# --- 執行 ---
target_schools = ["https://www.cs.cmu.edu/academics/graduate-admissions","https://www.gradoffice.caltech.edu/admissions"]
loop = asyncio.get_event_loop()
results = loop.run_until_complete(main(target_schools))

with open("school_data_clean_cmu_cal.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
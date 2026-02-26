import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse
import json
import re
import os

# --- get_page_content 保持不變 (負責單頁抓取、點擊選單與文字清洗) ---
async def get_page_content(page, url):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        })

        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

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
                        await el.click(force=True)
                        await asyncio.sleep(0.4)
            except:
                continue

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)

        content = await page.evaluate("""
            () => {
                const ignoreSelectors = 'script, style, nav, footer, header, .footer, .header, noscript';
                const clones = document.body.cloneNode(true);
                clones.querySelectorAll(ignoreSelectors).forEach(el => el.remove());
                return clones.innerText;
            }
        """)

        if content:
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            content = "\n".join(lines)
            
        return content if len(content) > 50 else None

    except Exception as e:
        print(f"無法抓取 {url}: {e}")
        return None

# --- 修改 main 函數：增加檔案分開儲存的邏輯 ---
async def main(start_urls):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context()
        page = await context.new_page()

        for root_url in start_urls:
            parsed_root = urlparse(root_url)
            domain = parsed_root.netloc
            # 使用網域作為檔名一部分，並過濾特殊字元
            safe_filename = re.sub(r'[^\w\s-]', '_', domain) + ".json"
            
            base_path = parsed_root.path.rstrip('/')
            visited = set()
            to_visit = [root_url]
            school_data = {} # 每一間學校獨立一個字典

            print(f"\n>>> 開始爬取學校: {domain} <<<")

            while to_visit and len(visited) < 30: 
                current_url = to_visit.pop(0)
                if current_url in visited:
                    continue

                print(f"正在掃描: {current_url}")
                text = await get_page_content(page, current_url)
                
                if text:
                    visited.add(current_url)
                    school_data[current_url] = text

                    hrefs = await page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
                    for href in hrefs:
                        full_url = href.split('#')[0].rstrip('/')
                        parsed = urlparse(full_url)
                        if parsed.netloc == domain and parsed.path.startswith(base_path):
                            if full_url not in visited and full_url not in to_visit:
                                to_visit.append(full_url)

            # --- 完成一間學校後立即存檔 ---
            with open(safe_filename, "w", encoding="utf-8") as f:
                json.dump(school_data, f, ensure_ascii=False, indent=2)
            print(f"完成！資料已存至: {safe_filename}")

        await browser.close()

# --- 執行 ---
target_schools = [
    "https://www.cs.cmu.edu/academics/graduate-admissions",
    "https://www.gradoffice.caltech.edu/admissions",
    "https://www.cs.stanford.edu/admissions"
]

if __name__ == "__main__":
    asyncio.run(main(target_schools))
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse
import json
import re
import os

# --- 設定區：請在此填入不希望爬取的關鍵字 ---
# 只要 URL 包含這些字，就跳過不爬 (例如排除新聞、動態 ID、登入頁)
URL_BLACKLIST = ["linux","windows","wp-content","alumni","staff","history","video","news", "event", "announcement", "press-release", "gallery", "wp-admin", "p=", "post=", "action=", "mailman"]

# 只要 HTML 的 class 或 id 包含這些字，內容就整塊移除 (不存入 JSON)
CONTENT_BLACKLIST = ["nav", "footer", "header", "sidebar", "menu", "social", "breadcrumb", "banner"]

# 紀錄已經點擊過的選單文字
expanded_elements = set()

async def get_page_content(page, url, school_domain):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        })

        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        # --- 保持原邏輯：自動展開選單 (同文字只點一次) ---
        expandable_selectors = [
            "button[aria-expanded='false']",
            ".accordion-header",
            ".dropdown-toggle",
            "[data-toggle='collapse']"
        ]
        
        for selector in expandable_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    if await el.is_visible():
                        el_text = (await el.inner_text()).strip()
                        unique_key = f"{school_domain}_{el_text}"

                        if el_text and unique_key in expanded_elements:
                            continue
                        
                        await el.click(force=True)
                        if el_text:
                            expanded_elements.add(unique_key)
                        await asyncio.sleep(0.3)
            except:
                continue

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)

        # --- 加入黑名單過濾的文字提取邏輯 ---
        content = await page.evaluate(f"""
            () => {{
                const clones = document.body.cloneNode(true);
                const blacklistedTags = {json.dumps(CONTENT_BLACKLIST)};
                
                // 排除 class 或 id 包含黑名單關鍵字的元素 (例如 bjkwfe-nav)
                blacklistedTags.forEach(word => {{
                    const elements = clones.querySelectorAll(`[class*="${{word}}" i], [id*="${{word}}" i]`);
                    elements.forEach(el => el.remove());
                }});

                // 移除基礎雜訊標籤
                const ignoreSelectors = 'script, style, noscript, iframe, svg, canvas';
                clones.querySelectorAll(ignoreSelectors).forEach(el => el.remove());
                
                return clones.innerText;
            }}
        """)

        if content:
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            content = "\n".join(lines)
            
        return content

    except Exception as e:
        print(f"無法抓取 {url}: {e}")
        return None

async def main(start_urls):
    expanded_elements.clear()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context()
        page = await context.new_page()

        for root_url in start_urls:
            parsed_root = urlparse(root_url)
            domain = parsed_root.netloc
            safe_filename = re.sub(r'[^\w\s-]', '_', domain) + ".json"
            base_path = parsed_root.path.rstrip('/')
            
            visited = set()
            to_visit = [root_url]
            school_data = {}

            print(f"\n>>> 開始爬取學校: {domain} <<<")

            while to_visit and len(visited) < 40: # 限制爬取數量
                current_url = to_visit.pop(0)
                if current_url in visited:
                    continue

                # --- 加入 URL 黑名單過濾 ---
                if any(blackword.lower() in current_url.lower() for blackword in URL_BLACKLIST):
                    print(f"跳過黑名單網址: {current_url}")
                    continue

                print(f"正在掃描: {current_url}")
                text = await get_page_content(page, current_url, domain)
                
                if text:
                    visited.add(current_url)
                    school_data[current_url] = text

                    # 提取連結
                    hrefs = await page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
                    for href in hrefs:
                        full_url = href.split('#')[0].rstrip('/')
                        parsed = urlparse(full_url)
                        
                        # 保持原邏輯：同網域、路徑向下
                        if parsed.netloc == domain and parsed.path.startswith(base_path):
                            if full_url not in visited and full_url not in to_visit:
                                # 預先過濾下層連結，減少無效掃描
                                if not any(bw.lower() in full_url.lower() for bw in URL_BLACKLIST):
                                    to_visit.append(full_url)

            with open(safe_filename, "w", encoding="utf-8") as f:
                json.dump(school_data, f, ensure_ascii=False, indent=2)
            print(f"完成！資料已存至: {safe_filename}")

        await browser.close()

if __name__ == "__main__":
    target_schools = [
        "https://cse.mit.edu/programs-admissions/",
        "https://www.cs.cmu.edu/academics/graduate-admissions",
        "https://www.cs.stanford.edu/admissions",
        "https://www.cs.ucla.edu/",
        "https://www.gradoffice.caltech.edu/admissions"
    ]
    asyncio.run(main(target_schools))
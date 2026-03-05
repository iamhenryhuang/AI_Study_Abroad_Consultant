import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse
import json
import re

# --- 設定區：請在此填入不希望爬取的關鍵字 ---
URL_BLACKLIST = [
    "wp-content", "alumni", "staff", "history", "video", "news", "event",
    "announcement", "press-release", "gallery", "wp-admin", "p=", "post=",
    "action=", "mailman", "nondegree", "stories", "award", "deepmind"
]
CONTENT_BLACKLIST = ["nav", "footer", "header", "sidebar", "menu", "social", "breadcrumb", "banner"]

# 紀錄已經點擊過的選單文字
expanded_elements = set()

async def get_page_content(page, url, school_domain):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        })

        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        # --- 自動展開選單 (同文字只點一次) ---
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
                        await asyncio.sleep(0.5)
            except:
                continue

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)

        # --- 黑名單過濾文字提取 ---
        content = await page.evaluate(f"""
            () => {{
                const clones = document.body.cloneNode(true);
                const blacklistedTags = {json.dumps(CONTENT_BLACKLIST)};

                blacklistedTags.forEach(word => {{
                    const elements = clones.querySelectorAll(`[class*="${{word}}" i], [id*="${{word}}" i]`);
                    elements.forEach(el => el.remove());
                }});

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

def is_blacklisted(url: str) -> bool:
    u = url.lower()
    return any(bw.lower() in u for bw in URL_BLACKLIST)

def normalize_url(url: str) -> str:
    # 移除 fragment、尾端 /
    return url.split("#")[0].rstrip("/")

def path_prefixes_for_base_urls(base_urls):
    prefixes = []
    for u in base_urls:
        pu = urlparse(u)
        p = pu.path.rstrip("/")
        prefixes.append(p)  # 可能為 "" 或 "/xxx"
    # 讓較長 prefix 優先（不影響正確性，但比較直覺）
    prefixes.sort(key=len, reverse=True)
    return prefixes

def in_any_prefix(parsed_url, prefixes):
    # 注意：若 prefix == "" 代表全站同網域都算
    for pref in prefixes:
        if pref == "":
            return True
        if parsed_url.path.startswith(pref):
            return True
    return False

async def crawl_one_domain(page, domain, base_urls, max_pages=40):
    """
    同一 domain 可給多條 base url。
    只爬同網域，且 path 落在任一 base url 的 path prefix 之下。
    """
    global expanded_elements
    expanded_elements.clear()

    safe_filename = re.sub(r"[^\w\s-]", "_", domain) + ".json"
    prefixes = path_prefixes_for_base_urls(base_urls)

    visited = set()
    to_visit = [normalize_url(u) for u in base_urls]
    school_data = {}

    print(f"\n>>> 開始爬取學校: {domain} (base urls={len(base_urls)}) <<<")
    print(f"允許的 path prefixes: {prefixes}")

    while to_visit and len(visited) < max_pages:
        current_url = normalize_url(to_visit.pop(0))
        if current_url in visited:
            continue

        if is_blacklisted(current_url):
            print(f"跳過黑名單網址: {current_url}")
            continue

        print(f"正在掃描: {current_url}")
        text = await get_page_content(page, current_url, domain)

        if not text:
            continue

        visited.add(current_url)
        school_data[current_url] = text

        # 提取連結
        try:
            hrefs = await page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
        except:
            hrefs = []

        for href in hrefs:
            full_url = normalize_url(href)
            parsed = urlparse(full_url)

            # 同網域 + 落在任一 prefix + 預先過濾黑名單
            if parsed.netloc == domain and in_any_prefix(parsed, prefixes):
                if full_url not in visited and full_url not in to_visit:
                    if not is_blacklisted(full_url):
                        to_visit.append(full_url)

    with open(safe_filename, "w", encoding="utf-8") as f:
        json.dump(school_data, f, ensure_ascii=False, indent=2)

    print(f"完成！({len(visited)} pages) 資料已存至: {safe_filename}")

async def main(target_schools_by_domain, max_pages_per_school=40):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context()
        page = await context.new_page()

        for domain, base_urls in target_schools_by_domain.items():
            # 防呆：只保留該 domain 的 urls（避免你不小心丟錯）
            filtered = []
            for u in base_urls:
                pu = urlparse(u)
                if pu.netloc == domain:
                    filtered.append(u)
                else:
                    print(f"[WARN] URL 網域不符，已略過: {u} (expected {domain})")

            if not filtered:
                print(f"[WARN] {domain} 沒有可用的 base urls，跳過")
                continue

            await crawl_one_domain(page, domain, filtered, max_pages=max_pages_per_school)

        await browser.close()

if __name__ == "__main__":
    # ✅ 同一間學校（同一 domain）放同一組 list
    target_schools_by_domain = {
        "engineering.yale.edu": [
            "https://engineering.yale.edu/academic-study/departments/computer-science/graduate-study/master-science-program",
            # 你可以在這裡繼續加同 domain 的其他 base url
        ],
        "gsas.yale.edu": [
            "https://gsas.yale.edu/admissions/phdmasters-application-process",
            # 同一個 gsas.yale.edu 的其他 base url 也加在這裡
        ],
    }

    asyncio.run(main(target_schools_by_domain, max_pages_per_school=40))

if __name__ == "__main__":
    target_schools = [
        #"https://cse.mit.edu/programs-admissions/",
        #"https://www.cs.cmu.edu/academics/graduate-admissions",
        #"https://www.cs.stanford.edu/admissions",
        #"https://www.cs.ucla.edu/", #UCLA
        ###"https://www.gradoffice.caltech.edu/admissions" #cal tech不行

        #"https://siebelschool.illinois.edu/admissions/graduate", #伊利諾
        #"https://gradschool.princeton.edu/admission-onboarding", #普林斯頓
        #"https://gradschool.cornell.edu/admissions/",
        #"https://www.cs.utexas.edu/graduate/apply", #德州奧斯丁
        #"https://seas.harvard.edu/computer-science/graduate-program",
        #"https://cse.ucsd.edu/graduate",
        #"https://engineering.yale.edu/academic-study/departments/computer-science/graduate-study/master-science-program", #yale
        "https://gsas.yale.edu/admissions/phdmasters-application-process" #yale

    ]
    asyncio.run(main(target_schools))
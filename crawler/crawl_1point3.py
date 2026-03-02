import os
import re
import time
import json
from urllib.parse import urljoin
from DrissionPage import ChromiumPage, ChromiumOptions
from bs4 import BeautifulSoup

# =========================
# 基本設定
# =========================
BASE_URL = "https://www.1point3acres.com/bbs/"
FID = 82
MAX_PAGES = 10 
OUTPUT_FILE = "1point3_data.json"
CRAWLED_FILE = "crawled_urls.txt"

# =========================
# 開啟瀏覽器
# =========================
co = ChromiumOptions()
co.set_user_data_path("acres_profile")
page = ChromiumPage(co)

# =========================
# 登入與記憶機制
# =========================
def init_crawler():
    # 1. 處理登入
    page.get("https://auth.1point3acres.com/login")
    print("檢查登入狀態中...")
    if "退出" not in page.html and "欢迎您回来" not in page.html:
        print("請手動完成登入與 Cloudflare 驗證")
        input("👉 好了之後按 Enter 繼續...")

    # 2. 載入舊有的 JSON 資料
    all_data = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            try:
                all_data = json.load(f)
            except:
                all_data = {}

    # 3. 載入已爬過的網址清單 (從 TXT 讀取)
    visited = set()
    if os.path.exists(CRAWLED_FILE):
        with open(CRAWLED_FILE, "r", encoding="utf-8") as f:
            visited = set(line.strip() for line in f if line.strip())
            
    print(f"📊 記憶庫載入完成：已跳過 {len(visited)} 個網址。")
    return all_data, visited

# =========================
# 解析表格
# =========================
def extract_table_data(html):
    soup = BeautifulSoup(html, "lxml")
    data_map = {}
    table = soup.find("table", class_="cgtl mbm")
    if table:
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                key = th.get_text(strip=True).replace(":", "").replace("：", "")
                val = td.get_text(strip=True)
                data_map[key] = val
    return data_map

# =========================
# 取得列表頁連結
# =========================
def get_thread_links(page_num):
    url = f"{BASE_URL}forum.php?mod=forumdisplay&fid={FID}&page={page_num}"
    print(f"\n📄 正在掃描列表頁 第 {page_num} 頁...")
    page.get(url)
    time.sleep(2)
    soup = BeautifulSoup(page.html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        if re.search(r"thread-\d+-1-1\.html", a["href"]):
            links.append(urljoin(BASE_URL, a["href"]))
    return list(set(links))

# =========================
# 抓取單篇內容
# =========================
def get_thread_content(url):
    print(f" 📥 抓取並解鎖: {url}")
    page.get(url)
    time.sleep(2)

    # 點擊解鎖隱藏內容
    buttons = page.eles('text:点击查看')
    for btn in buttons:
        try:
            btn.click(by_js=True) 
            page.wait(1.2) 
        except: pass

    raw_table = extract_table_data(page.html)
    soup = BeautifulSoup(page.html, "lxml")
    title = soup.find("title").text.strip() if soup.find("title") else ""
    post_area = soup.find("td", class_="t_f")
    content = post_area.get_text("\n", strip=True) if post_area else ""

    return title, content, raw_table

# =========================
# 主流程
# =========================
def main():
    all_data, visited = init_crawler()
    
    try:
        for page_num in range(11, MAX_PAGES + 41):
            thread_links = get_thread_links(page_num)

            for link in thread_links:
                # 關鍵：先檢查是否爬過，不要直接 add
                if link in visited:
                    continue
                
                title, content, table_data = get_thread_content(link)

                # 判定是否為有效貼文
                if "提示信息" in title or "录取汇报" not in title:
                    print(f"   ⚠️ 跳過無效貼文: {title}")
                    # 即使無效也記錄，避免下次重複點擊
                    with open(CRAWLED_FILE, "a", encoding="utf-8") as f:
                        f.write(link + "\n")
                    visited.add(link)
                    continue

                # 數據封裝
                data = {
                    "url": link,
                    "title": title,
                    "result": table_data.get("申请结果"),
                    "school": table_data.get("学校名称"),
                    "major": table_data.get("专业"),
                    "gpa": table_data.get("本科成绩和算法，排名"),
                    "toefl": table_data.get("T单项和总分"),
                    "gre": table_data.get("G单项和总分"),
                    "undergrad_school": table_data.get("本科学校档次"),
                    "content": content[:1000], 
                    "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                school_name = data.get("school") or "Unknown_School"
                
                # 存入字典結構
                if school_name not in all_data:
                    all_data[school_name] = [data]
                else:
                    all_data[school_name].append(data)

                # --- 存檔更新 ---
                visited.add(link)
                # 1. 記錄網址到 TXT (避免重複爬取)
                with open(CRAWLED_FILE, "a", encoding="utf-8") as f:
                    f.write(link + "\n")
                
                # 2. 儲存數據到 JSON
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)

                print(f"   ✅ 新抓取: {school_name} - {data['result']}")
                time.sleep(2.5) 

    except KeyboardInterrupt:
        print("\n🛑 使用者手動停止。")
    finally:
        print(f"🏁 任務結束。目前累積資料：{sum(len(v) for v in all_data.values())} 筆。")

if __name__ == "__main__":
    main()
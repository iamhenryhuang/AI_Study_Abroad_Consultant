import os
import json
import time
import argparse
import random
import urllib.parse
from datetime import datetime
from playwright.sync_api import sync_playwright

def crawl_reddit(query, limit=10, sort='relevance', timeframe='all', years=None):
    """
    使用 Playwright 模擬瀏覽器抓取 Reddit 資料。
    """
    print(f"[*] 正在準備獲取 Reddit 即時資料: '{query}'...")
    
    # 增加隨機延遲 (1.5s ~ 4s) 模擬人為操作
    delay = random.uniform(2.0, 4.0)
    print(f"[*] 流量控制：等待 {delay:.2f} 秒後再執行...")
    time.sleep(delay)

    # 為了過濾日期，我們抓取比需求更多的資料
    fetch_limit = limit * 3 if years else limit
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.reddit.com/search.json?q={encoded_query}&limit={fetch_limit}&sort={sort}&t={timeframe}"
    
    posts = []
    current_time = time.time()
    seconds_in_year = 365 * 24 * 3600
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.reddit.com/"
            }
        )
        
        # Stealth init script
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()
        
        try:
            print(f"[*] 正在訪問 Reddit 搜尋接口...")
            response = page.goto(search_url, wait_until="networkidle", timeout=30000)
            
            if response.status == 200:
                try:
                    data = response.json()
                    children = data.get('data', {}).get('children', [])
                    print(f"[*] 找到 {len(children)} 篇原始文章。")
                    
                    if not children:
                        print("[!] 查無資料 (children 為空)。")
                        return []
                        
                    for child in children:
                        if len(posts) >= limit:
                            break
                            
                        p_data = child.get('data', {})
                        created_utc = p_data.get('created_utc')
                        
                        # 日期過濾 (例如：兩年內)
                        if years and created_utc:
                            age_years = (current_time - created_utc) / seconds_in_year
                            if age_years > years:
                                # print(f"DEBUG: 跳過文章 (年齡: {age_years:.2f} 年)")
                                continue
                                
                        posts.append({
                            "title": p_data.get('title'),
                            "url": f"https://www.reddit.com{p_data.get('permalink')}",
                            "content": p_data.get('selftext', '')[:5000]
                        })
                    
                except json.JSONDecodeError:
                    print("[!] 解析 JSON 失敗。")
                    return []
            else:
                print(f"[!] 抓取失敗 (HTTP 狀態碼: {response.status})。")
                return []
                
        except Exception as e:
            print(f"[!] 發生異常錯誤: {e}")
            return None
        finally:
            browser.close()
            
    return posts

def main():
    parser = argparse.ArgumentParser(description="Reddit 即時資料爬蟲程式")
    parser.add_argument("--query", type=str, help="手動指定搜尋關鍵字 (多個關鍵字以逗號分隔)")
    parser.add_argument("--limit", type=int, default=10, help="抓取數量")
    parser.add_argument("--years", type=int, default=2, help="限制在幾年內的資料")
    
    args = parser.parse_args()

    # 設定目錄路徑
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_dir)
    data_dir = os.path.join(project_root, "data")
    output_dir = os.path.join(project_root, "reddit_data")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    queries = []
    if args.query:
        # 如果使用者有手動輸入，優先使用
        queries = [q.strip() for q in args.query.split(',')]
    else:
        # 自動從 /data 讀取學校名稱
        if os.path.exists(data_dir):
            files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
            for f in files:
                university_name = f.replace('.json', '')
                queries.append(f"{university_name} cs master admission advice")
        
        # 若 /data 為空，則使用預設
        if not queries:
            queries = ["cmu cs master admission advice", "uiuc cs master admission advice"]

    print(f"[*] 預計爬取 {len(queries)} 個項目...")

    for i, query in enumerate(queries):
        # 檔案安全命名
        file_safe_query = query.split("admission")[0].strip().replace(" ", "_").lower()
        output_file = os.path.join(output_dir, f"{file_safe_query}_reddit.json")
        
        results = crawl_reddit(query, limit=args.limit, years=args.years)
        
        if results:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            print(f"[+] 成功儲存 '{query}' 資料至: {output_file}")
        else:
            print(f"[!] '{query}' 爬取失敗或查無資料。")
            
        # 學校與學校之間增加更長的隨機休息時間，避免被 Reddit 判定為機器人
        if i < len(queries) - 1:
            interval = random.uniform(5.0, 10.0)
            print(f"[*] 項目間休息中：等待 {interval:.2f} 秒後進行下一個項目...")
            time.sleep(interval)

if __name__ == "__main__":
    main()





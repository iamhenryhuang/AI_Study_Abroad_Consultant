import os
import json
import time
import argparse
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

def crawl_reddit(query, limit=5, sort='relevance', timeframe='all'):
    """
    使用 Playwright 模擬瀏覽器抓取 Reddit 資料，並加入隨機延遲以降低被封鎖風險。
    """
    print(f"[*] 正在準備獲取 Reddit 即時資料: '{query}'...")
    
    # 增加隨機延遲 (1.5s ~ 4s) 模擬人為操作
    delay = random.uniform(1.5, 4.0)
    print(f"[*] 流量控制：等待 {delay:.2f} 秒後再執行...")
    time.sleep(delay)

    search_url = f"https://www.reddit.com/search.json?q={query}&limit={limit}&sort={sort}&t={timeframe}"
    
    posts = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 更加擬真的使用者設定
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="en-US"
        )
        page = context.new_page()
        
        try:
            print(f"[*] 正在訪問 Reddit 搜尋接口...")
            # 隨機化導航超時
            response = page.goto(search_url, wait_until="networkidle", timeout=30000)
            
            if response.status == 200:
                content_text = page.evaluate("() => document.body.innerText")
                
                try:
                    data = json.loads(content_text)
                    children = data.get('data', {}).get('children', [])
                    
                    if not children:
                        print("[!] 查無資料。")
                        return None
                        
                    for child in children:
                        p_data = child.get('data', {})
                        posts.append({
                            "title": p_data.get('title'),
                            "url": f"https://www.reddit.com{p_data.get('permalink')}",
                            "author": p_data.get('author'),
                            "subreddit": p_data.get('subreddit_name_prefixed'),
                            "upvotes": p_data.get('score'),
                            "num_comments": p_data.get('num_comments'),
                            "created_at": datetime.fromtimestamp(p_data.get('created_utc')).strftime('%Y-%m-%d %H:%M:%S'),
                            "content": p_data.get('selftext', '')[:5000]
                        })
                    
                except json.JSONDecodeError:
                    print("[!] 解析 JSON 失敗。")
                    return None
            else:
                print(f"[!] 抓取失敗 (HTTP 狀態碼: {response.status})。")
                return None
                
        except Exception as e:
            print(f"[!] 發生異常錯誤: {e}")
            return None
        finally:
            browser.close()
            
    return posts

def main():
    parser = argparse.ArgumentParser(description="Reddit 即時資料爬蟲程式 (流量控制版)")
    parser.add_argument("--query", type=str, default="stanford cs master admission advice", help="搜尋關鍵字")
    parser.add_argument("--limit", type=int, default=5, help="抓取數量")
    parser.add_argument("--sort", type=str, default="relevance", choices=['relevance', 'hot', 'top', 'new', 'comments'], help="排序方式")
    parser.add_argument("--output", type=str, default="stanford_cs_master_reddit.json", help="輸出檔名")
    
    args = parser.parse_args()

    # 設定輸出目錄到專案根目錄下的 reddit_data
    # 這裡假設腳本在 e:\study_abroad_agent\crawler，所以我們往上一層
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_dir)
    output_dir = os.path.join(project_root, "reddit_data")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[*] 建立目錄: {output_dir}")
        
    output_file = os.path.join(output_dir, args.output)

    results = crawl_reddit(args.query, limit=args.limit, sort=args.sort)
    
    if results:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        print(f"\n[+] 任務完成! 成功將 {len(results)} 篇即時文章儲存至: {output_file}")
    else:
        print("\n[!] 爬蟲未能取得任何線上資料。")

if __name__ == "__main__":
    main()




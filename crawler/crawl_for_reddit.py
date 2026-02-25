import os
import json
import time
import argparse
import random
import urllib.parse
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

def crawl_reddit(university_name, limit=10, years=None, seen_urls=None, seen_titles=None):
    """
    抓取特定學校的 Reddit 資料，極度嚴格篩選該校 CS Master 申請。
    使用了更保守的流量控制與重試機制。
    """
    if seen_urls is None:
        seen_urls = set()
    if seen_titles is None:
        seen_titles = set()

    uni_l = university_name.lower()
    
    # 搜尋語句：強制排除 phd 和 undergrad，僅搜尋碩士相關
    base_queries = [
        f'"{university_name}" cs (master OR MS OR MSCS OR MCS) (admission OR advice OR experience) -phd -undergrad',
        f'"{university_name}" MSCS admission advice info',
        f'"{university_name}" computer science graduate application SOP LOR'
    ]
    
    all_posts = []
    current_time = time.time()
    seconds_in_year = 365 * 24 * 3600
    
    def contains_word(text, word):
        return bool(re.search(rf'\b{re.escape(word)}\b', text, re.I))

    FORBIDDEN_KWS = ['phd', 'ph.d', 'doctorate', 'doctoral', 'undergrad', 'bachelor', 'sat', 'high school']
    MASTER_KWS = ['master', 'ms', 'mscs', 'mcs', 'graduate', 'grad school']
    TOPIC_KWS = ['admission', 'advice', 'experience', 'sop', 'lor', 'profile', 'apply', 'applying', 'decision', 'result', 'interview', 'review']

    # 品質、背景與成功案例過濾基準 (最高品質模式)
    MIN_CONTENT_LENGTH = 400  # 提高門檻，確保是完整經驗分享
    ADMISSION_INFO_KWS = ['gpa', 'gre', 'sop', 'lor', 'profile', 'portfolio', 'internship', 'research', 'work experience', 'toefl', 'cv']
    
    # 成功錄取錄取關鍵字
    ADMIT_SUCCESS_KWS = ['accepted', 'admitted', 'got in', 'incoming', 'decision', 'result', 'offer', 'admission', 'enrolled']
    # 純求建議/評估的排除字 (除非同時有錄取結果)
    PURE_ADVICE_KWS = ['chance me', 'chances', 'should i apply', 'evaluating', 'evaluation', 'eval', 'help', 'planning to apply', 'plan to apply']

    # 專門排除「非 CS 本科」或「轉專業」的關鍵字
    NON_CS_EXCLUSION_KWS = [
        'non-cs', 'non cs', 'career changer', 'switching to cs', 'switch to cs', 
        'bridge program', 'conversion', 'pivot', 'non-tech', 'liberal arts',
        'information systems', 'business major', 'mechanical engineer', 'civil engineer'
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            java_script_enabled=True,
            viewport={'width': 1280, 'height': 720}
        )
        
        for base_q in base_queries:
            if len(all_posts) >= limit:
                break
                
            retries = 0
            max_retries = 2
            wait_time = 60 

            while retries <= max_retries:
                print(f"[*] 正在獲取: '{base_q}' (嘗試 {retries+1}/{max_retries+1})...")
                encoded_query = urllib.parse.quote(base_q)
                search_url = f"https://www.reddit.com/search.json?q={encoded_query}&limit=60&sort=relevance&t=all"
                
                page = context.new_page()
                try:
                    time.sleep(random.uniform(5.0, 10.0))
                    response = page.goto(search_url, wait_until="networkidle", timeout=60000)
                    
                    if response.status == 200:
                        data = response.json()
                        children = data.get('data', {}).get('children', [])
                        
                        for child in children:
                            if len(all_posts) >= limit:
                                break
                                
                            p_data = child.get('data', {})
                            url = f"https://www.reddit.com{p_data.get('permalink')}"
                            title = p_data.get('title', '')
                            content = p_data.get('selftext', '')[:5000]
                            num_comments = p_data.get('num_comments', 0)
                            created_utc = p_data.get('created_utc')
                            subreddit = p_data.get('subreddit', '').lower()
                            
                            t_l = title.lower()
                            c_l = content.lower()

                            # --- 核心嚴格品質、背景與「錄取成功感」過濾 ---
                            
                            # 1. 基本去重
                            clean_title = "".join(filter(str.isalnum, t_l))
                            if url in seen_urls or (clean_title and clean_title in seen_titles):
                                continue
                            
                            # 2. 排除情緒廢文或髒話
                            if any(re.search(rf'\b{re.escape(bad)}\b', text) for bad in ['fuck', 'shit', 'suck', 'damn'] for text in [t_l, c_l]):
                                if len(content) < 500: continue

                            # 3. 排除 PhD / 大學部 (SAT, High School)
                            if any(contains_word(t_l, kw) or contains_word(c_l, kw) for kw in FORBIDDEN_KWS):
                                continue

                            # 4. 排除「非 CS 本科 / 轉專業」內容 (NON_CS_EXCLUSION_KWS)
                            if any(contains_word(t_l, kw) or contains_word(c_l, kw) for kw in NON_CS_EXCLUSION_KWS):
                                continue
                            
                            # 5. 重點：錄取成功性過濾 (Admission Success Only)
                            # 檢查是否有錄取關鍵字
                            is_success_story = any(contains_word(t_l, kw) or contains_word(c_l, kw) for kw in ADMIT_SUCCESS_KWS)
                            is_pure_asking = any(contains_word(t_l, kw) or contains_word(c_l, kw) for kw in PURE_ADVICE_KWS)
                            
                            # 如果只是單純在問問題 (Pure Asking) 且 沒提到錄取/結果，則過濾
                            if is_pure_asking and not is_success_story:
                                continue
                            
                            # 特別加強：如果是 Profile Review 但沒說結果，也要過濾
                            if 'profile' in t_l and not is_success_story:
                                continue

                            # 6. 學校關聯度檢查
                            if not contains_word(t_l, uni_l) and subreddit != uni_l:
                                if len(re.findall(rf'\b{re.escape(uni_l)}\b', c_l, re.I)) < 2:
                                    continue
                            
                            # 7. 確保是碩士主題
                            if not any(contains_word(t_l, kw) or contains_word(c_l, kw) for kw in MASTER_KWS):
                                continue
                                
                            # 8. 資訊密度與申請經驗檢查
                            has_admission_data = any(contains_word(c_l, kw) for kw in ADMISSION_INFO_KWS)
                            if len(content) < MIN_CONTENT_LENGTH or not has_admission_data:
                                continue
                            
                            # 最終確認：這篇文章是否真的是「經驗分享」而不僅是「一個問題」
                            if not is_success_story and len(content) < 1000:
                                # 若沒提到錄取，必須非常長且專業才考慮
                                continue

                            # 9. 時間過濾
                            if years and created_utc:
                                if (current_time - created_utc) / seconds_in_year > years:
                                    continue
                                    
                            seen_urls.add(url)
                            if clean_title: seen_titles.add(clean_title)
                            all_posts.append({
                                "title": title,
                                "url": url,
                                "content": content,
                                "num_comments": num_comments
                            })
                        print(f"[*] 本次有效累積: {len(all_posts)}/{limit}")
                        break
                        
                    elif response.status == 403:
                        print(f"[!] 遭遇 403 流量限制，等待 {wait_time} 秒後重試...")
                        time.sleep(wait_time)
                        wait_time *= 2 # 指數退避
                        retries += 1
                    else:
                        print(f"[!] 請求失敗 (HTTP {response.status})")
                        break
                except Exception as e:
                    print(f"[!] 錯誤: {e}")
                    break
                finally:
                    page.close()
            
            if retries > max_retries:
                print(f"[!] 達到最大重試次數，跳過此查詢。")

        browser.close()
            
    return all_posts

def main():
    parser = argparse.ArgumentParser(description="Reddit 高品質資料爬蟲")
    parser.add_argument("--query", type=str, help="指定學校 (多個以逗號分隔)")
    parser.add_argument("--limit", type=int, default=10, help="每校數量")
    parser.add_argument("--years", type=int, default=2, help="資料年份限制")
    
    args = parser.parse_args()

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_dir)
    data_dir = os.path.join(project_root, "data")
    output_dir = os.path.join(project_root, "reddit_data")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    university_names = []
    if args.query:
        university_names = [q.strip() for q in args.query.split(',')]
    else:
        if os.path.exists(data_dir):
            files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
            # 排除已成功抓取且數量足夠的學校 (可選，但為了安全我們先全跑一遍以更新品質)
            for f in files:
                university_names.append(f.replace('.json', ''))
        
        if not university_names:
            university_names = ["cmu", "uiuc", "stanford", "mit"]

    print(f"[*] 任務開始：預計處理 {len(university_names)} 間學校...")
    print("[*] 提示：為避免封鎖，速度目前設定為極慢模式。")

    global_seen_urls = set()
    global_seen_titles = set()

    for i, uni in enumerate(university_names):
        output_file = os.path.join(output_dir, f"{uni.lower()}_cs_master_reddit.json")
        
        # 爬取資料
        results = crawl_reddit(uni, limit=args.limit, years=args.years, 
                             seen_urls=global_seen_urls, seen_titles=global_seen_titles)
        
        if results:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            print(f"[+] '{uni}' 更新完成 ({len(results)} 篇)")
        else:
            print(f"[!] '{uni}' 未能取得新資料。")
            
        if i < len(university_names) - 1:
            interval = random.uniform(20.0, 40.0)
            print(f"[*] 長時間休息中：等待 {interval:.2f} 秒再處理下一間學校...")
            time.sleep(interval)

if __name__ == "__main__":
    main()





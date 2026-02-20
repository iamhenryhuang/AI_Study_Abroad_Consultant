import os
import json
import hashlib 
from groq import Groq
from dotenv import load_dotenv

CACHE_FILE = "universities_list.json"

def get_website():
    load_dotenv()
    
    # 這裡定義你的 Prompt
    current_prompt = (
        "List the top 50 world universities with their official website URLs in JSON format. "
        "Use a root key 'universities' containing a list of objects with fields: 'name' and 'official_website'."
    )
    
    # 1. 計算當前 Prompt 的Hash
    current_hash = hashlib.md5(current_prompt.encode('utf-8')).hexdigest()

    # 2. 檢查快取
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
            
            # 如果檔案裡的 hash 跟現在的一樣，才直接用
            if cache_data.get("prompt_hash") == current_hash:
                print(f"Prompt 未變動，從快取讀取 {len(cache_data['data'])} 所學校...")
                return cache_data["data"]
            else:
                print("Prompt 已變動，準備重新向 Groq 索取資料...")

    # 3. 如果沒快取或內容變了，才問 Groq
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("找不到 API KEY")

    client = Groq(api_key=api_key)
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": current_prompt}],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"}
    )

    raw_content = chat_completion.choices[0].message.content
    llm_data = json.loads(raw_content)
    
    # 確保取得列表
    universities = llm_data.get("universities", llm_data)

    # 4. 儲存包含 Hash 的新快取檔
    save_data = {
        "prompt_hash": current_hash,
        "data": universities
    }
    
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
        print(f"已更新快取檔案與指紋")

    return universities
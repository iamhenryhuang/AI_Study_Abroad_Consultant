import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy 
from crawl4ai import LLMConfig
from crawl4ai.chunking_strategy import RegexChunking
from crawl4ai.content_filter_strategy import PruningContentFilter
#from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerationStrategy
from pydantic import BaseModel, Field
from typing import Optional, List
import litellm
import os
import sys
from get_website import get_website
from dotenv import load_dotenv
from pathlib import Path

CACHE_FILE = "universities_data.json"
load_dotenv()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
root_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(root_dir)
from scripts.db.ops import import_json

class BasicAdmissionSchema(BaseModel):
    school_name: str = Field(..., description="學校的全名，例如：University of Southern California")
    program_name: str = Field(..., description="系所或學位名稱，例如：MS in Computer Science")
    degree_level: str = Field(..., description="學位等級，例如：Master, PhD, Undergraduate")
    toefl_min: Optional[int] = Field(None, description="托福總分最低要求，若無則填 null")
    ielts_min: Optional[float] = Field(None, description="雅思總分最低要求")
    gpa_min: Optional[float] = Field(None, description="最低 GPA 要求 (4.0 標制)")
    deadline: List[str] = Field(..., description="所有申請截止日期，例如：['2025-12-15 (Priority)', '2026-01-15 (Final)']")
    recommendation_letters: Optional[str] = Field(None, description="推薦信的要求描述")
    tuition: Optional[str] = Field(None, description="學費資訊描述")

#litellm._turn_on_debug()

async def main():
    
    os.environ["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY")
    #print(litellm.model_list)

    my_llm_config = LLMConfig(
        provider="groq/llama-3.1-8b-instant",
        #api_token="AIzaSyB-fMfa_NYoJ_locZZIoz6YJexxEAEvXBw"
    )
    # 2. 建立策略：關鍵在於傳入 .model_json_schema()
    strategy = LLMExtractionStrategy(
        llm_config=my_llm_config,
        schema=BasicAdmissionSchema.model_json_schema(), 
        extraction_type="scheme",
        chunking_strategy=RegexChunking(chunk_size=2000, chunk_overlap=200),
        instruction="""
        請從網頁中提取入學門檻資訊。
        1. 學校名稱與系所名稱請使用英文 program_name 只能用 MS in Computer Science。
        2. 截止日期請列出所有批次。
        3. 若分數或 GPA 沒提到，請填 null。
        4. 請確保輸出符合 JSON 格式，並且與提供的 schema 一致。
        5. 請列出所需推薦信格式以及學費
        """
    )

    browser_config = BrowserConfig(headless=True)
    content_filter = PruningContentFilter(threshold=0.48)

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=strategy,
        word_count_threshold=100,
        only_text=True,
        excluded_tags=['nav', 'footer', 'header'], # 排除導航欄和頁尾
    )

    base = {"school_name",
        "program_name",
        "degree_level",
        "toefl_min",
        "ielts_min",
        "gpa_min",
        "deadline",
        "recommendation_letters",
        "tuition",
        "error"
    }

    cache_data = []
    cache_path = Path(CACHE_FILE)
    if cache_path.exists():
        try:
            cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
            print(f"✅ 已載入快取，目前共有 {len(cache_data)} 筆資料。")
        except json.JSONDecodeError:
            print("⚠️ 快取檔案格式錯誤，將重新開始。")

    async with AsyncWebCrawler(config=browser_config) as crawler:
        
        target_list = get_website()

        # 建立一個臨時資料夾來放產出的 JSON
        os.makedirs("temp_json_data", exist_ok=True) 

        for item in target_list:
            school_name = item.get("school_name", "")
            program_name = item.get("program_name", "")
            degree_level = item.get("degree_level", "")
            deadline = item.get("deadline", [])

            hit = False
            for school in cache_data:
                if school.get("school_name") == school_name and school.get("program_name") == program_name and school.get("degree_level") == degree_level and school.get("deadline") == deadline:
                    print(f"學校資料已存在")
                    hit = True
                    break

            if hit == False:
                result = await crawler.arun(
                    url=item["official_website"], 
                    config=crawler_config
                )
                #print(result.extracted_content)
                
                if result.success:
                    data = json.loads(result.extracted_content)

                    final_summary = {} 
                    for item in data:
                        for key, value in item.items():
                            
                            if final_summary.get(key) is None and value is not None:
                                final_summary[key] = value
                
                            elif key == 'deadline' and isinstance(value, list):
                                existing = final_summary.get(key, [])
                                final_summary[key] = list(set(existing + value))

                    #unique_output = [final_summary] 
                    
                    standard_data = {
                        "school_id": final_summary.get("school_name", "unknown").lower().replace(" ", "_"),
                        "university": final_summary.get("school_name"),
                        "program": final_summary.get("program_name"),
                        "official_link": item.get("official_website"), # 從你的 target_list 拿
                        "description_for_vector_db": f"Degree: {final_summary.get('degree_level')}. Tuition: {final_summary.get('tuition')}",
                        "requirements": {
                            "toefl": {
                                "min_total": final_summary.get("toefl_min"),
                                "is_required": True if final_summary.get("toefl_min") else False,
                                "notes": ""
                            },
                            "ielts": {
                                "min_total": final_summary.get("ielts_min"),
                                "is_required": True if final_summary.get("ielts_min") else False
                            },
                            "minimum_gpa": final_summary.get("gpa_min"),
                            "recommendation_letters": final_summary.get("recommendation_letters"),
                            "interview_required": False
                        },
                        "deadlines": {
                            "fall_intake": None, # ops.py 預期 YYYY-MM-DD，若 AI 抓的是字串就先填 None 或處理它
                            "spring_intake": " | ".join(final_summary.get("deadline", []))
                        }
                    }

                    if final_summary.get("school_name"):
                        print("\n--- 最終合併總結 ---")
                        print(json.dumps(final_summary, indent=2, ensure_ascii=False))

                        # 1. 更新快取檔案 (universities_data.json)
                        cache_data.append(final_summary)
                        with open(CACHE_FILE, "w", encoding="utf-8") as f:
                            json.dump(cache_data, f, indent=2, ensure_ascii=False)
                        
                        # 2. 產出給資料庫用的 JSON 檔案 (temp_json_data/xxx.json)
                        file_name = f"temp_json_data/{standard_data['school_id']}.json"
                        with open(file_name, "w", encoding="utf-8") as f:
                            json.dump(standard_data, f, indent=2, ensure_ascii=False)
                        
                        print(f"✅ {final_summary['school_name']} 處理完成：已更新快取並產出 JSON 預備檔。")
                
                    await asyncio.sleep(20)

                else:
                    print(f"Error: {result.error_message}")

        print("\n--- 所有爬取任務完成，開始匯入資料庫 ---")
        try:
            #  import_json，指向你存檔的資料夾
            success = import_json(data_dirname="temp_json_data")
            if success:
                print("🚀 資料已成功同步至 PostgreSQL 資料庫！")
            else:
                print("❌ 資料庫匯入失敗，請檢查 db/ops.py 的報錯訊息。")
        except Exception as e:
            print(f"匯入過程發生非預期錯誤: {e}")
            

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"程式發生錯誤: {e}")
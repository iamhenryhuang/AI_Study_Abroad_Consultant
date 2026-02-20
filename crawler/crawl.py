import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai import LLMConfig
#from crawl4ai.async_configs import LlmConfig
from pydantic import BaseModel, Field
from typing import Optional, List
import litellm
import os
import sys
from get_website import get_website
from dotenv import load_dotenv



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
    load_dotenv()
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
        instruction="""
        請從網頁中提取入學門檻資訊。
        1. 學校名稱與系所名稱請使用英文 program_name 只能用 MS in Computer Science。
        2. 截止日期請列出所有批次。
        3. 若分數或 GPA 沒提到，請填 null。
        4. 請確保輸出符合 JSON 格式，並且與提供的 schema 一致。
        5. 請列出所需推薦信格式以及學費
        """,
    )

    browser_config = BrowserConfig(headless=True)
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=strategy,
        #word_count_threshold=200, # 只處理超過 200 字的區塊
        excluded_tags=['nav', 'footer', 'header'] # 排除導航欄和頁尾
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

    async with AsyncWebCrawler(config=browser_config) as crawler:
        
        target_list = get_website()

        for item in target_list:
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

                unique_output = [final_summary] 
                
                print("\n--- 最終合併總結 ---")
                print(json.dumps(final_summary, indent=2, ensure_ascii=False))
            else:
                print(f"Error: {result.error_message}")

            await asyncio.sleep(25)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"程式發生錯誤: {e}")
import asyncio
import os
from typing import Dict, Optional, List
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig, BrowserConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy

# --- 1. 定義更精確的 Schema ---

class Deadline(BaseModel):
    round_name: str = Field(..., description="The name of the application round (e.g., Priority, Regular, Fall)")
    date: str = Field(..., description="The deadline date, preferably in YYYY-MM-DD format")

class BasicAdmissionSchema(BaseModel):
    school_name: str = Field(..., description="Full English name of the university.")
    program_name: str = Field("MS in Computer Science", description="Name of the department or degree (Must be 'MS in Computer Science').")
    degree_level: str = Field("Master", description="Degree level (e.g., Master, PhD).")
    
    # 分數要求
    toefl_min: Optional[int] = Field(None, description="Minimum total TOEFL score. Use null if not mentioned.")
    ielts_min: Optional[float] = Field(None, description="Minimum total IELTS score. Use null if not mentioned.")
    gpa_min: Optional[float] = Field(None, description="Minimum GPA requirement (4.0 scale). Use null if not mentioned.")
    
    # 截止日期與細節
    deadlines: List[Deadline] = Field(..., description="List of all application deadline rounds found on the page.")
    recommendation_letters: Optional[str] = Field(None, description="Quantity and submission format of Letters of Recommendation.")
    tuition: Optional[str] = Field(None, description="Tuition fees information (e.g., per credit, per year, or total).")

# --- 2. 結構化資料提取函數 ---

async def extract_structured_data_using_llm(provider: str, api_token: str = None, extra_headers: Dict[str, str] = None):
    print(f"\n--- Extracting Structured Data with {provider} ---")

    if api_token is None and "ollama" not in provider:
        print(f"API token is required for {provider}. Skipping.")
        return

    browser_config = BrowserConfig(headless=True)

    # 設定指令 (Instruction)
    extraction_instruction = """
    Identify and extract admission requirements for the 'MS in Computer Science' program.
    
    Rules:
    1. Language: University and program names MUST be in English.
    2. Deadlines: Capture EVERY application round (Early, Round 1, Final, etc.) into the 'deadlines' list.
    3. Missing Data: If GPA, TOEFL, or IELTS scores are not explicitly stated as a minimum requirement, fill with null.
    4. LOR: Specifically look for how many letters are required and the method of submission.
    5. Tuition: Extract any mention of costs, specifying if it's per unit or per academic year.
    6. Precision: Do not hallucinate. Only extract what is present on the page.
    """

    extra_args = {"temperature": 0, "top_p": 0.9, "max_tokens": 2000}
    if extra_headers:
        extra_args["extra_headers"] = extra_headers

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=1,
        page_timeout=80000,
        extraction_strategy=LLMExtractionStrategy(
            llm_config=LLMConfig(provider=provider, api_token=api_token),
            schema=BasicAdmissionSchema.model_json_schema(),
            extraction_type="schema",
            instruction=extraction_instruction,
            extra_args=extra_args,
        ),
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # 以 Stanford CS 招生頁面為例
        result = await crawler.arun(
            url="https://www.cs.stanford.edu/admissions", 
            config=crawler_config
        )
        
        if result.success:
            print("\nExtracted Content:")
            print(result.extracted_content)
        else:
            print(f"Extraction failed: {result.error_message}")


if __name__ == "__main__":
    # 若使用 OpenAI，請取消註解並填入 Key
    # provider = "openai/gpt-4o"
    # api_key = os.getenv("OPENAI_API_KEY")
    
    # 預設使用你提供的 Ollama 設定
    asyncio.run(
        extract_structured_data_using_llm(
            provider="ollama/llama3", 
            api_token=None
        )
    )
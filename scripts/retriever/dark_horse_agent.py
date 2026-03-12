"""
黑馬科系導航 Agent
推薦 CS 相關但競爭較低的科系
"""

def search_dark_horse_programs(profile=None):

    mock_programs = [
        {
            "university": "Carnegie Mellon University",
            "program": "Information Systems",
            "overlap_with_cs": 0.75,
            "difficulty": "Medium",
            "reason": "課程包含 Database / Distributed Systems / ML"
        },
        {
            "university": "Georgia Tech",
            "program": "Analytics",
            "overlap_with_cs": 0.65,
            "difficulty": "Medium-Low",
            "reason": "Data science + machine learning"
        },
        {
            "university": "Indiana University",
            "program": "Data Science",
            "overlap_with_cs": 0.7,
            "difficulty": "Low",
            "reason": "AI / statistics / ML"
        },
        {
            "university": "UT Austin",
            "program": "Information Studies",
            "overlap_with_cs": 0.6,
            "difficulty": "Low",
            "reason": "資料工程 + 系統設計"
        }
    ]

    return mock_programs
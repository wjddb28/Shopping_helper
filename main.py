# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from crawlers.levdance import get_levdance_stock
from crawlers.eballet import get_eballet_stock

class OptionItem(BaseModel):
    color: str
    size: str
    is_soldout: bool

# 최종 응답 데이터 규칙
class StockResponse(BaseModel):
    status: str
    message: Optional[str] = None
    
    class ConfigData(BaseModel):
        target_url: str
        mall_type: str
        options: List[OptionItem]
        
    data: Optional[ConfigData] = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/stock")
def get_stock(url: str):
    
    # 다른 쇼핑몰 추가시 코드도 추가하기
    if "levdance.com" in url:
        return get_levdance_stock(url)

    elif "eballetshop.com" in url:
        return get_eballet_stock(url)

    
    else:
        return {"status": "error", "message": "아직 지원하지 않는 쇼핑몰 주소입니다."}
# main.py
from fastapi import FastAPI
import requests
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

from database import init_db, insert_track, fetch_all_tracks, update_track_status, delete_track
from crawlers.levdance import get_levdance_stock
from crawlers.eballet import get_eballet_stock
from crawlers.cafe24 import get_cafe24_stock
from crawlers.makeshop import get_makeshop_stock
from crawlers.sixshop import get_sixshop_stock

app = FastAPI()
init_db()

class OptionItem(BaseModel):
    color: str
    size: str
    is_soldout: bool

class StockResponse(BaseModel):
    status: str
    message: Optional[str] = None
    
    class ConfigData(BaseModel):
        target_url: str
        mall_type: str
        options: List[OptionItem]
        
    data: Optional[ConfigData] = None

class TrackRequest(BaseModel):
    url: str
    target_color: str
    target_size: str
    category: str = "미분류"

# 1=알람켬, 0=알람끔
class StatusRequest(BaseModel):
    is_active: int

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def detect_platform(url):
    if "branduid=" in url or "shopdetail.html" in url:
        return "makeshop"
    elif "yooraballet.com" in url:
        return "sixshop"
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        html_text = response.text.lower()
        
        if "sixshop.com" in html_text or "sixshop.io" in html_text or "cdn.sixshop" in html_text:
            return "sixshop"
            
        if "option_stock_data" in html_text or "cafe24.com" in html_text or "ec-core" in html_text:
            return "cafe24"
            
    except Exception as e:
        print(f"플랫폼 탐지 중 에러 발생: {e}")

    return "cafe24"

# 실시간 재고확인 API
@app.get("/api/stock")
def get_stock(url: str):
    if "eballetshop.com" in url:
        return get_eballet_stock(url)
    
    elif "levdance.com" in url:
        return get_levdance_stock(url)
        
    platform = detect_platform(url)    
    if platform == "makeshop":
        return get_makeshop_stock(url)
    elif platform == "sixshop":
        return get_sixshop_stock(url)
    else:
        return get_cafe24_stock(url)
    

# 새로운 URL을 추가하는 API
@app.post("/api/track")
def add_to_track_list(req: TrackRequest):
    crawled_data = get_stock(req.url)

    if crawled_data["status"] == "error":
        return {"status": "error", "message": "크롤링에 실패"}
    
    mall_type = crawled_data["data"]["mall_type"]
    product_name =crawled_data["data"]["product_name"]

    is_success = insert_track(req.url, mall_type, product_name, req.target_color, req.target_size, req.category)

    if is_success:
        return {"status": "success", "message": f"[{mall_type}] {product_name} ({req.target_color}/{req.target_size}) 추적 시작!"}
    else:
        return {"status": "error", "message": "DB 저장 중 문제가 발생했습니다."}
    

# 추가한 상품을 삭제하는 API
@app.delete("/api/track/{item_id}")
def remove_track(item_id: int):
    is_success = delete_track(item_id)

    if is_success:
        return {"status": "success", "message" : "상품을 장바구니에서 삭제했습니다."}
    else:
        return {"status": "error", "message": "삭제 실패: 해당 상품을 찾을 수 없거나 에러가 발생했습니다."}


# 저장한 목록을 불러오는 API
@app.get("/api/tracks")
def get_all_tracks(mall: Optional[str] = None, category: Optional[str] = None):
    rows = fetch_all_tracks()
    filtered_rows = rows

    # 쇼핑몰 이름별로 필터링
    if mall:
        filtered_rows = [row for row in filtered_rows if row['mall_type'] == mall]
        
    # 카테고리별로 필터링
    if category:
        filtered_rows = [row for row in filtered_rows if row['category'] == category]
        
    return {"status": "success", "data": filtered_rows}


# 알람 상태 변경 API
@app.put("/api/track/{item_id}")
def change_track_status(item_id: int, req: StatusRequest):
    is_success = update_track_status(item_id, req.is_active)
    
    if is_success:
        status_text = "켜짐 🔔" if req.is_active == 1 else "꺼짐 🔕"
        return {"status": "success", "message": f"{item_id}번 상품 알림이 [{status_text}] 상태로 변경되었습니다."}
    else:
        return {"status": "error", "message": "상태 변경 실패"}


# 일정 시간마다 자동으로 재고 확인
def check_stock_periodically():
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n🔍 [{now}] 재고 확인중....")
    
    rows = fetch_all_tracks()
    
    if not rows:
        print(" 아직 추적 중인 상품이 없습니다 ")
        return

    for row in rows:
        if row['is_active'] == 0:
            continue;

        url = row['target_url']
        mall_type = row['mall_type']
        product_name = row['product_name']
        target_color = row['target_color']
        target_size = row['target_size']
        
        result = get_stock(url)
        
        if result['status'] == 'error':
            print(f"❌ [{mall_type}] {product_name} : 크롤링 에러")
            continue
            
        options = result['data']['options']
        available_options = [
            opt for opt in options 
            if opt['is_soldout'] == False 
            and opt['color'] == target_color 
            and opt['size'] == target_size
        ]
        
        if available_options:
            print(f"🎉 [{mall_type}] {product_name} ({target_color}/{target_size}) 재고가 들어왔습니다!!")
        else:
            print(f"😥 [{mall_type}] {product_name} ({target_color}/{target_size}) : 아직 품절입니다.")


# 스케줄러 실행
@app.on_event("startup")
def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    # 나중에 minutes=30 으로 바꾸기
    scheduler.add_job(check_stock_periodically, 'interval', minutes=10)
    
    scheduler.start()
    print("⏰ 자동 스케줄러 실행중..")
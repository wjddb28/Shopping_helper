# crawlers/cafe24.py
import requests
import re
import json
from bs4 import BeautifulSoup

def get_cafe24_stock(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        site_name_meta = soup.find('meta', property='og:site_name')
        mall_type = site_name_meta['content'] if site_name_meta else "카페24 쇼핑몰"
        
        title_meta = soup.find('meta', property='og:title')
        product_name = title_meta['content'] if title_meta else "상품명 확인 불가"
        
        selects = soup.find_all('select', attrs={'product_type': 'product_option'})
        option_titles = []
        for s in selects:
            title = s.get('option_title', '').upper()
            if title:
                option_titles.append(title)
            
        stock_data_match = re.search(r"var option_stock_data\s*=\s*'(\{.*?\})';", response.text)
        mapper_match = re.search(r"var option_name_mapper\s*=\s*'([^']+)';", response.text)
        
        mapper_names = []
        if mapper_match:
            mapper_names = [p.strip().upper() for p in mapper_match.group(1).split('#$%')]

        options = []
        
        if stock_data_match:
            raw_json = stock_data_match.group(1)
            clean_json = raw_json.replace('\\"', '"').replace('\\\\', '\\')
            
            try:
                stock_dict = json.loads(clean_json)
                
                for key, info in stock_dict.items():
                    opt_val = info.get('option_value', '')
                    is_soldout = (info.get('use_soldout', 'F') == 'T')
                    
                    current_names = mapper_names
                    if not current_names:
                        json_name = info.get('option_name', '')
                        if json_name:
                            current_names = [p.strip().upper() for p in json_name.split('#$%')]
                    if not current_names:
                        current_names = option_titles

                    val_parts = [p.strip() for p in opt_val.split('#$%')]
                    
                    final_color = "단일/통합색상"
                    final_size = "단일/통합사이즈"
                    
                    if current_names:
                        for idx, name in enumerate(current_names):
                            if idx < len(val_parts):
                                if "COLOR" in name or "색상" in name or "컬러" in name:
                                    final_color = val_parts[idx]
                                elif "SIZE" in name or "사이즈" in name or "크기" in name:
                                    final_size = val_parts[idx]
                    else:
                        if len(val_parts) >= 2:
                            final_color = val_parts[0]
                            final_size = val_parts[1]
                        elif len(val_parts) == 1:
                            final_color = val_parts[0]

                    if final_size == "단일/통합사이즈" and "-" in final_color:
                        split_parts = final_color.split("-", 1)
                        final_color = split_parts[0].strip()
                        final_size = split_parts[1].strip()
                        
                    elif final_color == "단일/통합색상" and "-" in final_size:
                        split_parts = final_size.split("-", 1)
                        final_color = split_parts[0].strip()
                        final_size = split_parts[1].strip()

                    options.append({
                        "color": final_color,
                        "size": final_size,
                        "is_soldout": is_soldout
                    })
                    
                return {
                    "status": "success",
                    "data": {
                        "target_url": url,
                        "mall_type": mall_type,
                        "product_name": product_name,
                        "options": options
                    }
                }
            except json.JSONDecodeError:
                pass

        return {"status": "error", "message": "데이터를 찾을 수 없습니다."}
        
    except Exception as e:
        return {"status": "error", "message": f"카페24 크롤링 실패: {str(e)}"}
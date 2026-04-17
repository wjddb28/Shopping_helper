# crawlers/makeshop.py
import requests
import re
import json
from bs4 import BeautifulSoup

def get_makeshop_stock(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        mall_type = "메이크샵 쇼핑몰"
        product_name = "상품명 확인 불가"
        
        site_name_meta = soup.find('meta', property='og:site_name')
        if site_name_meta and site_name_meta.get('content'):
            mall_type = site_name_meta['content'].strip()

        title_meta = soup.find('meta', property='og:title')
        if title_meta:
            full_title = title_meta['content']
            if " - " in full_title:
                parts = full_title.split(" - ", 1)
                if mall_type == "메이크샵 쇼핑몰": 
                    mall_type = parts[0].strip()
                product_name = parts[1].strip()
            else:
                product_name = full_title

        json_ld_tags = soup.find_all('script', type='application/ld+json')
        for tag in json_ld_tags:
            if tag and tag.string:
                try:
                    ld_data = json.loads(tag.string)
                    
                    if ld_data.get('name'):
                        product_name = ld_data.get('name')

                    seller_name = ld_data.get('seller', {}).get('name')
                    
                    if not seller_name and isinstance(ld_data.get('offers'), dict):
                        seller_name = ld_data.get('offers', {}).get('seller', {}).get('name')

                    if seller_name:
                        mall_type = seller_name
                        
                except json.JSONDecodeError:
                    seller_match = re.search(r'"seller"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', tag.string)
                    if seller_match:
                        mall_type = seller_match.group(1)
                        
        options = []
        
        json_data_match = re.search(r"var optionJsonData\s*=\s*(\{.*?\});", response.text, re.DOTALL)
        
        if json_data_match:
            json_text = json_data_match.group(1)
            
            pattern = r"opt_name:'([^']+)'.*?opt_values:'([^']+)'.*?sto_real_stock:'([^']*)'.*?sto_state:'([^']+)'"
            matches = re.finditer(pattern, json_text)
            
            for m in matches:
                opt_name = m.group(1).upper() 
                opt_val = m.group(2)         
                stock = m.group(3)
                state = m.group(4)
                
                is_soldout = (state == 'SOLDOUT' or stock == '0')
                
                final_color = "단일/통합색상"
                final_size = "단일/통합사이즈"
                
                has_color = ("COLOR" in opt_name or "색상" in opt_name or "컬러" in opt_name)
                has_size = ("SIZE" in opt_name or "사이즈" in opt_name)
                
                if has_size and not has_color:
                    final_size = opt_val
                elif has_color and not has_size:
                    final_color = opt_val
                else:
                    if "-" in opt_val:
                        parts = opt_val.rsplit("-", 1) 
                        final_color = parts[0].strip()
                        final_size = parts[1].strip()
                    else:
                        final_color = opt_val 
                
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
        
    except Exception as e:
        return {"status": "error", "message": f"메이크샵 크롤링 실패: {str(e)}"}
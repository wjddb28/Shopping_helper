import requests
import re
import json
from bs4 import BeautifulSoup

def get_levdance_stock(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'}
    response = requests.get(url, headers=headers)
    
    result = {
        "status": "success",
        "data": {
            "target_url": url,
            "mall_type": "레브당스",
            "product_name": "",
            "product_image": "",
            "options": [] 
        }
    }

    html_text = response.text
    match = re.search(r"var option_stock_data = '(.*?)';", html_text)
    
    if match:
        stock_data_str = match.group(1)
        
        clean_str = stock_data_str.replace('\\"', '"')

        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('meta', property='og:title')
        product_name = title_tag.get('content', '상품명 없음') if title_tag else '상품명 없음'

        image_tag = soup.find('meta', property='og:image')
        product_image = image_tag.get('content', '') if image_tag else ''

        result['data']['product_name'] = product_name
        result['data']['product_image'] = product_image
        
        try:
            stock_data = json.loads(clean_str)
            
            for item_code, info in stock_data.items():
                option_raw = info.get('option_value', '')
                option_label = info.get('option_name', '')
                is_soldout = True if info.get('use_soldout', 'F') == 'F' else False

                # 다중 옵션 (색상 + 사이즈)
                if '-' in option_raw:
                    option_parts = option_raw.split('-',1)
                    color = option_parts[0].strip()
                    size = option_parts[1].strip()

                else:
                    if 'size' in option_label.lower() or '사이즈' in option_label:
                        color = "-"
                        size = option_raw.strip()

                    elif 'color' in option_label.lower() or '색상' in option_label:
                        color = option_raw.strip()
                        size = "-"

                    else:
                        color = option_raw.strip()
                        size = "-"

                result['data']['options'].append({
                    "color": color,
                    "size": size,
                    "is_soldout": is_soldout
                })
                
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 에러: {e}")


    return result


import requests
import re
import json
from bs4 import BeautifulSoup

def get_eballet_stock(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'}
    response = requests.get(url, headers=headers)
    
    result = {
        "status": "success",
        "data": {
            "target_url": url,
            "mall_type": "이발레샵",
            "product_name": "",
            "product_image": "",
            "options": []       
        }
    }

    try:
        match = re.search(r"var goodsNo = '(\d+)';", response.text)
        
        if match:
            goods_no = match.group(1)
        else:
            return {"status": "error", "message": "상품 번호를 찾을 수 없습니다."}

        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('meta', property='og:title')
        product_name = title_tag.get('content', '상품명 없음') if title_tag else '상품명 없음'

        image_tag = soup.find('meta', property='og:image')
        product_image = image_tag.get('content', '') if image_tag else ''

        result['data']['product_name'] = product_name
        result['data']['product_image'] = product_image

        color_select = soup.find('select', {'name': 'optionNo_0'})

        # 다중 옵션 (색상 + 사이즈)
        if color_select:
            color_tags = color_select.find_all('option')
            colors = [opt.get('value') for opt in color_tags if opt.get('value')]

            api_url = "https://www.eballetshop.com/goods/goods_ps.php"
        
            for color in colors:
                payload = {
                    "mode": "option_select",
                    "optionVal[]": color,
                    "optionKey": "0",
                    "goodsNo": goods_no,
                    "mileageFl": "g"
                }
            
                api_res = requests.post(api_url, data=payload, headers=headers)
                api_data = api_res.json()
                
                sizes = api_data.get("nextOption", [])
                stocks = api_data.get("stockCnt", [])
            
                for size, stock_str in zip(sizes, stocks):
                    stock_count = int(stock_str)
                    # 재고 수량이 0이면 True(품절), 아니면 False(구매가능)
                    is_soldout = True if stock_count == 0 else False
                    
                    result['data']['options'].append({
                        "color": color,
                        "size": size,
                        "is_soldout": is_soldout
                    })

            # 단일 옵션 (색상 or 사이즈)
        else:
            single_select = soup.find('select', {'name': 'optionSnoInput'})

            if single_select:
                option_label = ""
                dl_tag = single_select.find_parent('dl')

                if dl_tag and dl_tag.find('dt'):
                    option_label = dl_tag.find('dt').get_text(strip=True)

                for opt in single_select.find_all('option'):
                    value = opt.get('value')
                    if not value:
                        continue

                    raw_text = opt.get_text(strip=True)
                    option_name = raw_text.replace('[품절]', '').strip()
                    is_soldout = True if opt.get('disabled') else False

                    if '/' in option_name:
                        parts = option_name.split('/', 1)
                        color = parts[0].strip()
                        size = parts[1].strip()

                    else:
                        if '색상' in option_label or '컬러' in option_label or 'Color' in option_label:
                            color = option_name
                            size = "-"

                        elif '사이즈'in option_label or 'SIZE' in option_label:
                            color = "-"
                            size = option_name
                        
                        else:
                            color = option_name
                            size = "-"

                    result['data']['options'].append({
                        "color": color,
                        "size": size,
                        "is_soldout": is_soldout
                    })
            else:
                return {"status": "error", "message": "옵션 선택 영역을 찾을 수 없습니다."}

    except Exception as e:
        result["status"] = "error"
        result["message"] = f"크롤링 중 에러 발생: {e}"

    return result


# crawlers/sixshop.py
import requests
import json
from bs4 import BeautifulSoup
import re

def get_sixshop_stock(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        mall_type = "식스샵 쇼핑몰"
        product_name = "상품명 확인 불가"
        
        site_name_meta = soup.find('meta', property='og:site_name')
        if site_name_meta and site_name_meta.get('content'):
            mall_type = site_name_meta['content'].strip()

        title_meta = soup.find('meta', property='og:title')
        if title_meta and title_meta.get('content'):
            product_name = title_meta['content'].strip()
        else:
            title_tag = soup.find('title')
            if title_tag:
                product_name = title_tag.text.strip()
                
        json_ld_tag = soup.find('script', type='application/ld+json')
        if json_ld_tag and json_ld_tag.string:
            try:
                ld_data = json.loads(json_ld_tag.string)
                if ld_data.get('name'):
                    product_name = ld_data.get('name')
                seller_info = ld_data.get('offers', {}).get('seller', {})
                if seller_info and seller_info.get('name'):
                    mall_type = seller_info.get('name')
            except json.JSONDecodeError:
                pass

        if mall_type == "식스샵 쇼핑몰":            
            sangho_label = soup.find(string=re.compile('상호'))
            if sangho_label:
                sangho_dd = sangho_label.find_next('dd')
                if sangho_dd and sangho_dd.text:
                    mall_type = sangho_dd.text.strip()

        options = []
        
        variants_match = re.search(r'"variants"\s*:\s*\[(.*?)\]\s*,\s*"isOutOfStock"', response.text)
        if not variants_match:
            variants_match = re.search(r'"variants"\s*:\s*\[(.*?)\]', response.text)
            
        if variants_match:
            variants_text = variants_match.group(1)
            is_soldout = True if '"isOutOfStock":true' in variants_text else False
            
            val_match = re.search(r'"value"\s*:\s*"([^"]+)"', variants_text)
            final_size = val_match.group(1) if val_match else "단일/통합사이즈"
            
            options.append({
                "color": "단일/통합색상", 
                "size": final_size,
                "is_soldout": is_soldout
            })
            
        if not options:
            option_list_div = soup.find('div', class_='shopProductOptionListDiv')
            if option_list_div and option_list_div.get('data-not-selling') == 'true':
                 return {
                    "status": "success",
                    "data": {
                        "target_url": url,
                        "mall_type": mall_type,
                        "product_name": product_name,
                        "options": [{"color": "전체", "size": "판매중지", "is_soldout": True}]
                    }
                }

            color_options = {} 
            size_options = []
            wrappers = soup.find_all('div', class_='custom-select-wrapper')
            
            for wrapper in wrappers:
                name_span = wrapper.find('span', class_='custom-select-option-name')
                if not name_span:
                    continue
                    
                label = name_span.text.strip().lower()
                opt_divs = wrapper.find_all('div', class_='custom-select-option')

                if 'color' in label or '색상' in label or '컬러' in label:
                    for div in opt_divs:
                        val_no = div.get('data-combined-option-value-no')
                        val = div.get('data-option-value')
                        soldout = (div.get('data-soldout') == 'true')
                        if val_no and val:
                            color_options[val_no] = {'name': val, 'soldout': soldout}
                            
                elif 'size' in label or '사이즈' in label:
                    for div in opt_divs:
                        combo_nos = div.get('data-combined-option-value-no')
                        val = div.get('data-option-value')
                        soldout = (div.get('data-soldout') == 'true')
                        if combo_nos and val:
                            size_options.append({'combo': combo_nos, 'name': val, 'soldout': soldout})

            if color_options and size_options:
                for size_opt in size_options:
                    parts = [p.strip() for p in size_opt['combo'].split(',')]
                    if len(parts) >= 1:
                        color_id = parts[0] 
                        color_info = color_options.get(color_id, {'name': '기본색상'})
                        options.append({
                            "color": color_info['name'],
                            "size": size_opt['name'],
                            "is_soldout": size_opt['soldout']
                        })
            elif size_options and not color_options:
                for size_opt in size_options:
                    options.append({
                        "color": "단일/통합색상", 
                        "size": size_opt['name'],
                        "is_soldout": size_opt['soldout']
                    })
            elif color_options and not size_options:
                for c_id, c_info in color_options.items():
                    options.append({
                        "color": c_info['name'],
                        "size": "단일/통합사이즈",
                        "is_soldout": c_info['soldout']
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
        return {"status": "error", "message": f"식스샵 크롤링 실패: {str(e)}"}
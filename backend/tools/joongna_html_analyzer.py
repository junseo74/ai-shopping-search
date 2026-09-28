"""Analyze a manually saved Joongna search-result HTML file. No network requests."""
import argparse
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup


def extract(path):
    soup = BeautifulSoup(Path(path).read_text(encoding='utf-8'), 'html.parser')
    products = []
    seen = set()
    for a in soup.select('a[href^="/product/"]'):
        href = a.get('href', '')
        match = re.fullmatch(r'/product/(\d+)', href)
        if not match:
            continue
        pid = match.group(1)
        if pid in seen:
            continue
        title_el = a.select_one('span.line-clamp-2')
        price_el = a.select_one('span.text-18.font-bold')
        img_el = a.select_one('img[src]')
        if not title_el or not price_el:
            continue
        price_raw = price_el.get_text(' ', strip=True).replace(',', '')
        if not price_raw.isdigit():
            continue
        seen.add(pid)
        texts = [x.get_text(' ', strip=True) for x in a.select('span')]
        status = next((v for v in texts if v in ('판매완료', '예약중', '판매중')), None)
        products.append({
            'product_id': pid,
            'product_name': title_el.get_text(' ', strip=True),
            'price': int(price_raw),
            'currency': 'KRW',
            'platform': '중고나라',
            'condition': 'used',
            'product_url': 'https://web.joongna.com' + href,
            'image_url': img_el.get('src') if img_el else None,
            'region': None,
            'sale_status': status,
            'data_source': 'manually_saved_html',
        })
    summary = {
        'source_file': str(path),
        'product_count': len(products),
        'missing_name': sum(not p['product_name'] for p in products),
        'missing_price': sum(p['price'] is None for p in products),
        'missing_image': sum(not p['image_url'] for p in products),
        'missing_region': sum(not p['region'] for p in products),
        'missing_sale_status': sum(not p['sale_status'] for p in products),
        'note': 'Only fields visible in saved search-result HTML are extracted. Region/status are null when absent.'
    }
    return {'summary': summary, 'products': products}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html_file')
    ap.add_argument('--output-json', default='joongna_products.json')
    args = ap.parse_args()
    result = extract(args.html_file)
    Path(args.output_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

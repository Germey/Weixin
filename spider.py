import re
import requests
from requests.exceptions import ConnectionError
from urllib.parse import urlencode, urljoin
from pyquery import PyQuery as pq

import pymongo

MONGO_URL = 'localhost'
MONGO_DB = 'Weixin'
MONGO_TABLE = 'Weixin'

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

headers = {
    'Host': 'weixin.sogou.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
}


def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('Successfully Saved to Mongo', result)
        return True
    return False


def get_proxy():
    proxy_pool_url = 'http://127.0.0.1:5000/get'
    try:
        r = requests.get(proxy_pool_url)
        return r.text
    except ConnectionError:
        return None


proxy = None
max_count = 5
base_url = 'http://weixin.sogou.com/weixin?'


def get_page(url, count=1):
    global proxy, max_count
    print('Now proxy', proxy)
    if count == max_count:
        print('Tried too many times')
        return None
    try:
        if proxy:
            proxies = {'http': 'http://' + proxy}
            print(proxies, url)
            response = requests.get(url, headers=headers, proxies=proxies, allow_redirects=False)
        else:
            response = requests.get(url, headers=headers, allow_redirects=False)
        if response.status_code == 200:
            return response.text
        if response.status_code == 302:
            proxy = get_proxy()
            if proxy:
                print('Using proxy', proxy)
                return get_page(url)
            else:
                print('Get proxy failed')
                return None
    except ConnectionError:
        print('Error Occurred')
        count += 1
        proxy = get_proxy()
        return get_page(url, count)


def get_index_page(url):
    html = get_page(url)
    if html:
        for result in parse_index_page(html):
            if isinstance(result, dict):
                save_to_mongo(result)
            elif isinstance(result, str) and re.match(r'^https?:/{2}\w.+$', result):
                get_index_page(result)


def parse_index_page(html):
    doc = pq(html)
    items = doc('.news-box li').items()
    for item in items:
        image = item.find('.img-box img').attr('src')
        title = item.find('.tit').text()
        account = item.find('label[name="em_weixinhao"]').text()
        qrcode = item.find('.ew-pop img[height="104"]').attr('src')
        introduction = item.find('dl:nth-child(2) > dd').text()
        authentication = item.find('dl:nth-child(3) > dd').text()
        yield {'image': image, 'title': title, 'account': account, 'qrcode': qrcode, 'introduction': introduction,
               'authentication': authentication}
    next = doc('.p-fy #sogou_next').attr('href')
    yield urljoin(base_url, next) if next else None


def main(keyword):
    page = 1
    data = {
        '_sug_type_': '',
        's_from': 'input',
        '_sug_': 'n',
        'type': 1,
        'ie': 'utf-8',
        'query': keyword,
        'page': page
    }
    params = urlencode(data)
    url = base_url + params
    print('Crawling', url)
    get_index_page(url)


main('搞笑')

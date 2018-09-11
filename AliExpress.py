from bs4 import BeautifulSoup
import requests
import re
from selenium import webdriver
from time import sleep
import json

#search_url = 'https://www.aliexpress.com/wholesale?catId=0'

def login_ali():
    driver = webdriver.Chrome('C:\\temp\\chromedriver.exe')
    driver.get('https://login.aliexpress.com')
    #sleep(10)
    driver.switch_to.frame(0)
    username = driver.find_element_by_name("loginId")
    username.send_keys('se7en.msk@gmail.com')
    #sleep(5)
    password = driver.find_element_by_name("password")
    password.send_keys('password_here')
    #sleep(5)
    submit = driver.find_element_by_name('submit-btn')
    submit.click()
    sleep(5)
    cookies_list = driver.get_cookies()
    print(cookies_list)
    s = requests.Session()
    for cookie in cookies_list:
        s.cookies.set(cookie['name'], cookie['value'])
    return s

def login_ali2():
    payload = {
        "loginId": "se7en.msk@gmail.com",
        "password2": "9348777b06f448e15da5edb8a01b9c614ade0d09a1e9e6f10cf016d4c3635c8bbf3afb94a330cf60411082eafd1ed9521fcccc25e0776f44f3e7a8638a7726f5092baf7e9b65624ec0a9f102aea94f4a3c50fe729c531df83c0905e390decd8981f22d5948331384f61187fa595299b4474623e84111deb69d95afa59fea0d9f",
    }
    LOGIN_URL = 'https://passport.aliexpress.com/newlogin/login.do?fromSite=13&appName=aebuyer'
    LOGIN_URL_2 = 'https://login.aliexpress.com/validateSTGroup.htm?language=ru_ru&st='
    session_requests = requests.session()
    source_code = session_requests.post(LOGIN_URL, data=payload)
    plain_text = source_code.json()
    if not 'st' in  plain_text['content']['data']:
        return session_requests
    st = plain_text['content']['data']['st']
    source_code = session_requests.get(LOGIN_URL_2 + st)
    plain_text = source_code.text
    plain_text = plain_text.replace('var xman_success=', '')
    plain_text = json.loads(plain_text)
    url = plain_text["xlogin_urls"][0]
    token_list = url.split("&")
    token = ''
    for elem in token_list:
        if 'token' in elem:
            token = elem.split("=")[1]
    LOGIN_URL = "https://passport.alibaba.com/mini_apply_st.js?callback=jQuery18303464445807479921_1536179244420&site=13&token=" + token + "&_=1536179253078"
    source_code = session_requests.get(LOGIN_URL)
    plain_text = source_code.text
    LOGIN_URL2 = "https://login.alibaba.com/xman/tvs.htm"
    payload = {
        "token": token,
        "moduleKey": "common.xman.SetCookie",
        "pid": '141115758',
        "rnd": "1400743609262"
    }
    source_code = session_requests.post(LOGIN_URL2, data=payload)
    plain_text = source_code.text
    print(plain_text)
    source_code = session_requests.get("https://login.aliexpress.com/xloginCallBackForRisk.do")
    plain_text = source_code.text
    print(plain_text)
    source_code = session_requests.get("http://trade.aliexpress.com/orderList.htm")
    plain_text = source_code.text
    print(plain_text)
    return session_requests


def find_refund(user_data, link_list, cond_result, cond_user):
    SEARCH_URL = 'https://www.aliexpress.com/wholesale?SortType=create_desc'
    #min_price = '10'
    #max_price = ''
    if user_data['min_price']:
        SEARCH_URL += '&minPrice=' + user_data['min_price']
    if user_data['max_price']:
        SEARCH_URL += '&maxPrice=' + user_data['max_price']
    SEARCH_URL += '&SearchText='
    #SEARCH_PRODUCT = 'mi band 3'
    #BRAND = 'xiaomi'
    search_url = SEARCH_URL + user_data['product']
    s = login_ali2()
    for page in range(1, 99):
        request_url = search_url + '&page=' + str(page)
        print(request_url)
        r = s.get(request_url)
        page = r.text
        soup = BeautifulSoup(page, 'html.parser')
        test_page = soup.find(text=re.compile('did not match any products'))
        if test_page:
            link_list.clear()
            link_list.append(None)
            with cond_result:
                cond_result.notifyAll()
            break
            #return None
        products = soup.findAll('a',  attrs={'class': 'history-item product '})
        prodlist=[]
        for p in products:
            tmp = p['href']
            prodlist.append('http://' + tmp[2:])
        print("Products found: " + str(len(prodlist)))
        for p in prodlist:
            found = True
            '''for word in search_product.split():
                name = p.split('/')[4]
                if word in name:
                    continue
                else:
                    found = False
            if not found:
                continue'''
            prod_page = requests.get(p).text
            soup_prod = BeautifulSoup(prod_page, 'html.parser')
            title = soup_prod.find('h1', attrs={'class': 'product-name'})
            if title:
                for filtered_word in user_data['filter_words']:
                    if filtered_word.lower() in title.text.lower():
                        print('filtered word found, so this is not our item!')
                        continue
            brand_li = soup_prod.find('li', attrs={'id': 'product-prop-2'})
            if not brand_li:
                print('No brand!')
                continue
            child = brand_li.findChild("span", attrs={'class': 'propery-des'})
            if child.text.lower() != user_data['brand'].lower():
                #return p
                print(p)
                link_list.clear()
                link_list.append(p)
                with cond_result:
                    cond_result.notifyAll()
                with cond_user:
                    if not cond_user.wait(60):
                        exit()
            else:
                print('brand fine!')


if __name__ == '__main__':
    try:
        find_refund(SEARCH_PRODUCT, BRAND)
    except KeyboardInterrupt:
        exit()

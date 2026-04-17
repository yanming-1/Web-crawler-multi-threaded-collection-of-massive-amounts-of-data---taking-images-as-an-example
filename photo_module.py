import requests
from bs4 import BeautifulSoup
import os
import threading
from selenium import webdriver  # selenium 的用法可參見 5-7 節
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time



def download_pic(url, path):
    pic = requests.get(url)  # 使用 GET 對圖片連結發出請求
    path += url[url.rfind('.'):]  # 將路徑加上圖片的副檔名
    f = open(path, 'wb')  # 以指定的路徑建立一個檔案
    f.write(pic.content)  # 將 HTTP Response 物件的 content寫入檔案中
    f.close()  # 關閉檔案


def get_photolist(photo_name, download_num):
    page = 1  
    photo_list = []  

    url = 'https://pixabay.com/zh/'   # Pixabay 網址
    option = webdriver.ChromeOptions()  # ←↓加入選項來指定不要有自動控制的訊息
    option.add_experimental_option('excludeSwitches', ['enable-automation'])
    browser = webdriver.Chrome(options=option)  # 以指定的選項啟動 Chrome
    # 連線到pixabay網頁, ●●注意, Chrome出現訊息窗時不可按【停用】鈕, 請按 x 將之關閉, 或不理它也可。
    browser.get(url)
    time.sleep(2) 
    search_box = browser.find_element(By.NAME, 'search') 
    search_box.send_keys(photo_name)
    search_box.send_keys(Keys.RETURN)
    time.sleep(5)  # 等待搜索结果加载
    html = browser.page_source

    while True:
        html = browser.page_source
#        print(html)
        bs = BeautifulSoup(html, 'lxml')  # 解析網頁
        # 尋找所有圖片元素
        photo_items = bs.find_all('img', {'src': True})
        if len(photo_items) == 0:
            print('Error, no photo link in page', page)
            return None
        for img in photo_items:
            photo = img['src']
            if photo == '/static/img/blank.gif':
                if 'data-lazy' in img.attrs:
                    photo = img['data-lazy']
                else:
                    continue  # 跳過無效圖片
            if photo in photo_list or not photo.startswith('https://cdn.pixabay.com/photo'):
                continue  # 跳過重複或非Pixabay圖片
            # 若要下載較高解析度的圖, 可將下行取消註解
#            photo = photo.replace('_340', '1280')  # 更換為1280解析度
            photo_list.append(photo)  # 將找到的連結新增進 list 之中
            if len(photo_list) >= download_num:
                print('end by get photo list size', len(photo_list))
                browser.close()
                return photo_list
        page += 1  # 頁數加1
        # 找出下一頁的連結網址
        try:
            next_link = browser.find_element(By.PARTIAL_LINK_TEXT, '›').get_attribute('href')
            browser.get(next_link)
        except:  # 沒下一頁了
            browser.close()
            return photo_list


def create_folder(photo_name):
    folder_name = input("請輸入要儲存的資料夾名稱: ")

    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
        print("資料夾不存在, 建立資料夾: " + folder_name)
    else:
        print("找到資料夾: " + folder_name)

    if not os.path.exists(folder_name + os.sep + photo_name):
        os.mkdir(folder_name + os.sep + photo_name)
        print("建立資料夾: " + photo_name)
    else:
        print(photo_name + " 資料夾已存在")
    return folder_name


def get_photobythread(folder_name, photo_name, photo_list):
    download_num = len(photo_list)  # 設定下載數量為圖片連結串列的長度
    Q = int(download_num / 100)  # 取商數
    R = download_num % 100  # 取餘數

    for i in range(Q):
        threads = []
        for j in range(100):
            threads.append(threading.Thread(target=download_pic, args=(
                photo_list[i*100+j], folder_name + os.sep + photo_name + os.sep + str(i*100+j+1))))
            threads[j].start()
        for j in threads:
            j.join()
        print(int((i+1)*100/download_num*100), '%')  # 顯示當前進度

    threads = []
    for i in range(R):
        threads.append(threading.Thread(target=download_pic, args=(
            photo_list[Q*100+i], folder_name + os.sep + photo_name + os.sep + str(Q*100+i+1))))
        threads[i].start()
    for i in threads:
        i.join()
    print("100%")  # 顯示當前進度

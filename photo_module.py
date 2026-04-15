import os
import threading
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def download_pic(url, path):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        ext = os.path.splitext(url.split("?")[0])[1]
        if not ext or len(ext) > 5:
            ext = ".jpg"

        full_path = path + ext
        with open(full_path, "wb") as f:
            f.write(response.content)

        print("下載成功:", full_path)
    except Exception as e:
        print("下載失敗:", url, e)


def get_photolist(photo_name, download_num):
    photo_list = []
    url = "https://pixabay.com/zh/"

    option = webdriver.ChromeOptions()
    option.add_experimental_option("excludeSwitches", ["enable-automation"])

    browser = webdriver.Chrome(options=option)

    try:
        browser.get(url)
        time.sleep(2)

        search_box = browser.find_element(By.NAME, "search")
        search_box.send_keys(photo_name)
        search_box.send_keys(Keys.RETURN)
        time.sleep(5)

        while True:
            html = browser.page_source
            bs = BeautifulSoup(html, "lxml")
            img_tags = bs.find_all("img")

            found_new = False

            for img in img_tags:
                photo = img.get("src", "")

                if not photo:
                    continue
                if not photo.startswith("https://"):
                    continue
                if "cdn.pixabay.com" not in photo:
                    continue
                if photo in photo_list:
                    continue

                photo_list.append(photo)
                found_new = True
                print("抓到圖片:", photo)

                if len(photo_list) >= download_num:
                    print("已取得足夠圖片:", len(photo_list))
                    return photo_list

            if not found_new:
                print("這一頁沒有新圖片了")
                break

            try:
                next_link = browser.find_element(By.PARTIAL_LINK_TEXT, "›").get_attribute("href")
                if not next_link:
                    break

                browser.get(next_link)
                time.sleep(3)
            except Exception:
                print("沒有下一頁了")
                break

        return photo_list

    finally:
        browser.quit()


def create_folder(photo_name):
    folder_name = input("請輸入要儲存的資料夾名稱: ").strip()

    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
        print("資料夾不存在，建立資料夾:", folder_name)
    else:
        print("找到資料夾:", folder_name)

    target_folder = folder_name + os.sep + photo_name
    if not os.path.exists(target_folder):
        os.mkdir(target_folder)
        print("建立資料夾:", photo_name)
    else:
        print(photo_name + " 資料夾已存在")

    return folder_name


def get_photobythread(folder_name, photo_name, photo_list):
    download_num = len(photo_list)

    if download_num == 0:
        print("沒有可下載的圖片")
        return

    q = download_num // 100
    r = download_num % 100

    for i in range(q):
        threads = []

        for j in range(100):
            index = i * 100 + j
            t = threading.Thread(
                target=download_pic,
                args=(
                    photo_list[index],
                    folder_name + os.sep + photo_name + os.sep + str(index + 1),
                ),
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        print(int((i + 1) * 100 / download_num * 100), "%")

    threads = []
    for i in range(r):
        index = q * 100 + i
        t = threading.Thread(
            target=download_pic,
            args=(
                photo_list[index],
                folder_name + os.sep + photo_name + os.sep + str(index + 1),
            ),
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("100%")


if __name__ == "__main__":
    photo_name = input("請輸入要搜尋的圖片名稱: ").strip()
    download_num = int(input("請輸入要下載的圖片數量: "))

    photo_list = get_photolist(photo_name, download_num)
    print("抓到的圖片數量：", len(photo_list))

    if len(photo_list) > 0:
        folder_name = create_folder(photo_name)
        get_photobythread(folder_name, photo_name, photo_list)
    else:
        print("沒有抓到任何圖片")
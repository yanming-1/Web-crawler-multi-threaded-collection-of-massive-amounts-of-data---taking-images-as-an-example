import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver  # selenium 的用法可參見 5-7 節
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


BASE_URL = "https://pixabay.com/zh/"
PIXABAY_PHOTO_PREFIX = "https://cdn.pixabay.com/photo"


def create_webdriver(): # 建立並回傳可供 Selenium 使用的 Chrome WebDriver。
    option = webdriver.ChromeOptions()
    option.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(options=option)


def clean_extension(url):  # 從圖片 URL 解析並回傳檔案副檔名。
    url = url.split("?")[0]
    _, extension = os.path.splitext(url)
    if extension and len(extension) <= 5:
        return extension
    return ".jpg"


def download_pic(url, path):  # 下載單張圖片並儲存到指定路徑。
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    extension = clean_extension(url)
    file_path = f"{path}{extension}"

    with open(file_path, "wb") as f:
        f.write(response.content)


def parse_photo_urls(html, photo_list):  # 解析 HTML 取得圖片連結並新增到清單中。
    soup = BeautifulSoup(html, "lxml")
    for img in soup.find_all("img", {"src": True}):
        photo = img["src"]
        if photo == "/static/img/blank.gif":
            photo = img.attrs.get("data-lazy")
            if not photo:
                continue

        if not photo.startswith(PIXABAY_PHOTO_PREFIX):
            continue
        if photo in photo_list:
            continue

        photo_list.append(photo)


def collect_photo_urls(browser, download_num):  # 從瀏覽器頁面逐頁蒐集圖片連結直到達到所需數量。
    photo_list = []
    page = 1

    while True:
        html = browser.page_source
        parse_photo_urls(html, photo_list)
        if len(photo_list) >= download_num:
            print("end by get photo list size", len(photo_list))
            return photo_list

        page += 1
        try:
            next_link = browser.find_element(By.PARTIAL_LINK_TEXT, "›").get_attribute("href")
            browser.get(next_link)
            time.sleep(2)
        except Exception:
            return photo_list


def get_photolist(photo_name, download_num):  # 使用 Selenium 搜尋關鍵字並取得圖片連結清單。
    browser = create_webdriver()
    browser.get(BASE_URL)
    time.sleep(2)

    search_box = browser.find_element(By.NAME, "search")
    search_box.send_keys(photo_name)
    search_box.send_keys(Keys.RETURN)
    time.sleep(5)

    photo_list = collect_photo_urls(browser, download_num)
    browser.close()
    return photo_list


def create_folder(photo_name, parent_folder=None):  # 建立下載用資料夾並回傳根目錄路徑。
    if parent_folder is None:
        parent_folder = input("請輸入要儲存的資料夾名稱: ").strip()
    if not parent_folder:
        parent_folder = "."

    os.makedirs(os.path.join(parent_folder, photo_name), exist_ok=True)
    print(f"儲存目錄已建立或已存在: {os.path.join(parent_folder, photo_name)}")
    return parent_folder


def download_photos(photo_list, root_folder, photo_name):  # 迭代下載整批圖片到指定資料夾。
    target_folder = os.path.join(root_folder, photo_name)
    for index, photo_url in enumerate(photo_list, 1):
        target_path = os.path.join(target_folder, str(index))
        download_pic(photo_url, target_path)


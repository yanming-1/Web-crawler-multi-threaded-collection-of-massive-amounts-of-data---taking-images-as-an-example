import os
import time
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from requests.exceptions import RequestException, Timeout, ConnectionError
from tqdm import tqdm

BASE_URL = "https://pixabay.com/zh/"
PIXABAY_PHOTO_PREFIX = "https://cdn.pixabay.com/photo"


def create_webdriver():
    option = webdriver.ChromeOptions()
    option.add_experimental_option("excludeSwitches", ["enable-automation"])
    option.add_argument("--no-sandbox")
    option.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=option)
    logging.info("WebDriver 創建成功")
    return driver


def clean_extension(url):
    try:
        url = url.split("?")[0]
        _, extension = os.path.splitext(url)
        if extension and len(extension) <= 5:
            return extension
        return ".jpg"
    except Exception as e:
        logging.warning(f"解析副檔名失敗，使用預設 .jpg: {e}")
        return ".jpg"


def download_pic(url, path, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=15, stream=True)
            response.raise_for_status()
            extension = clean_extension(url)
            file_path = f"{path}{extension}"

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"成功下載圖片: {file_path}")
            return True
        except (RequestException, Timeout, ConnectionError) as e:
            logging.warning(f"下載圖片失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logging.error(f"下載圖片最終失敗: {url}")
                return False
        except OSError as e:
            logging.error(f"寫入文件失敗: {e}")
            return False
        except Exception as e:
            logging.error(f"未知錯誤: {e}")
            return False


def parse_photo_urls(html, photo_set):
    try:
        soup = BeautifulSoup(html, "lxml")
        for img in soup.find_all("img", {"src": True}):
            photo = img["src"]
            if photo == "/static/img/blank.gif":
                photo = img.attrs.get("data-lazy")
                if not photo:
                    continue

            if not photo.startswith(PIXABAY_PHOTO_PREFIX):
                continue

            photo_set.add(photo)
    except Exception as e:
        logging.error(f"解析 HTML 失敗: {e}")


def collect_photo_urls(browser, download_num, max_pages=50):
    photo_set = set()
    page = 1
    wait = WebDriverWait(browser, 10)

    while page <= max_pages:
        try:
            html = browser.page_source
            parse_photo_urls(html, photo_set)
            if len(photo_set) >= download_num:
                logging.info(f"已收集足夠圖片: {len(photo_set)}")
                return list(photo_set)[:download_num]

            page += 1
            next_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "›")))
            browser.get(next_link.get_attribute("href"))
            time.sleep(2)
        except (NoSuchElementException, TimeoutException):
            logging.info("未找到下一頁連結，停止收集")
            break
        except WebDriverException as e:
            logging.error(f"瀏覽器操作失敗: {e}")
            break
        except Exception as e:
            logging.error(f"收集圖片連結時發生未知錯誤: {e}")
            break

    return list(photo_set)[:download_num]


def get_photolist(photo_name, download_num):
    browser = None
    try:
        browser = create_webdriver()
        browser.get(BASE_URL)
        time.sleep(3)

        wait = WebDriverWait(browser, 10)
        search_box = wait.until(EC.presence_of_element_located((By.NAME, "search")))

        search_box.send_keys(photo_name)
        search_box.send_keys(Keys.RETURN)
        time.sleep(5)

        return collect_photo_urls(browser, download_num)
    except NoSuchElementException as e:
        logging.error(f"找不到搜尋框: {e}")
        return []
    except TimeoutException as e:
        logging.error(f"等待元素超時: {e}")
        return []
    except WebDriverException as e:
        logging.error(f"Selenium 操作失敗: {e}")
        return []
    except Exception as e:
        logging.error(f"取得圖片清單時發生未知錯誤: {e}")
        return []
    finally:
        if browser:
            try:
                browser.quit()
                logging.info("瀏覽器已關閉")
            except Exception as e:
                logging.warning(f"關閉瀏覽器時發生錯誤: {e}")


def create_folder(photo_name, parent_folder):
    try:
        if not parent_folder:
            parent_folder = "."
        folder_path = os.path.join(parent_folder, photo_name)
        os.makedirs(folder_path, exist_ok=True)
        logging.info(f"儲存目錄已建立或已存在: {folder_path}")
        return parent_folder
    except OSError as e:
        logging.error(f"建立資料夾失敗: {e}")
        raise
    except Exception as e:
        logging.error(f"建立資料夾時發生未知錯誤: {e}")
        raise


def download_photos(photo_list, root_folder, photo_name, max_workers=5):
    target_folder = os.path.join(root_folder, photo_name)
    success_count = 0
    fail_count = 0

    def _download(args):
        index, url = args
        target_path = os.path.join(target_folder, str(index))
        return download_pic(url, target_path)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_download, (i, url)): i for i, url in enumerate(photo_list, 1)}
        with tqdm(total=len(photo_list), desc="下載進度", unit="張") as pbar:
            for future in as_completed(futures):
                if future.result():
                    success_count += 1
                else:
                    fail_count += 1
                pbar.update(1)

    logging.info(f"下載統計: 成功 {success_count} 張，失敗 {fail_count} 張")

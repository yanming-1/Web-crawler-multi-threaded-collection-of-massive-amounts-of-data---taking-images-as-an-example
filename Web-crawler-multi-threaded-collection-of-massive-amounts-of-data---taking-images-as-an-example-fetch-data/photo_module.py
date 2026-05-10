import os
import time
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import RequestException, Timeout, ConnectionError
from tqdm import tqdm

PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "55770865-37d56e6b7c3009a4b1f996c31")
PIXABAY_API_URL = "https://pixabay.com/api/"


def set_api_key(api_key):
    global PIXABAY_API_KEY
    if api_key:
        PIXABAY_API_KEY = api_key


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


def fetch_photolist_api(photo_name, download_num):
    if not PIXABAY_API_KEY:
        logging.error("Pixabay API Key 未設定，請輸入有效的 API Key 或設定 PIXABAY_API_KEY 環境變數。")
        return []

    urls = []
    page = 1
    per_page = min(download_num, 200)

    while len(urls) < download_num:
        params = {
            "key": PIXABAY_API_KEY,
            "q": photo_name,
            "image_type": "photo",
            "per_page": per_page,
            "page": page,
            "safesearch": "true",
        }

        try:
            response = requests.get(PIXABAY_API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            hits = data.get("hits", [])

            if not hits:
                logging.info("API 查詢未找到任何圖片。")
                break

            for hit in hits:
                url = hit.get("largeImageURL") or hit.get("webformatURL") or hit.get("previewURL")
                if url:
                    urls.append(url)
                    if len(urls) >= download_num:
                        break

            if len(hits) < per_page:
                break

            page += 1
        except RequestException as e:
            logging.error(f"Pixabay API 請求失敗: {e}")
            break
        except ValueError as e:
            logging.error(f"解析 Pixabay API 回傳失敗: {e}")
            break
        except Exception as e:
            logging.error(f"取得 Pixabay API 圖片清單時發生未知錯誤: {e}")
            break

    return urls[:download_num]


def get_photolist(photo_name, download_num):
    try:
        return fetch_photolist_api(photo_name, download_num)
    except Exception as e:
        logging.error(f"取得圖片清單時發生錯誤: {e}")
        return []


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

import os
import time
import logging
import re
import requests
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from bs4 import BeautifulSoup
from PIL import Image, ImageFile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from requests.exceptions import RequestException, Timeout, ConnectionError
from tqdm import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

PIXABAY_SEARCH_URL = "https://pixabay.com/zh/images/search/"
UNSPLASH_SEARCH_URL = "https://unsplash.com/s/photos/"
PEXELS_SEARCH_URL = "https://www.pexels.com/search/"

PIXABAY_PHOTO_PREFIX = "https://cdn.pixabay.com/photo"
UNSPLASH_PHOTO_PREFIX = "https://images.unsplash.com"
PEXELS_PHOTO_PREFIX = "https://images.pexels.com/photos/"


def create_webdriver():
    option = webdriver.ChromeOptions()
    option.add_experimental_option("excludeSwitches", ["enable-automation"])
    option.add_argument("--no-sandbox")
    option.add_argument("--disable-dev-shm-usage")
    option.add_argument("--disable-blink-features=AutomationControlled")
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


def verify_image_dimensions(url, target_width, target_height, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=20, headers=HEADERS, stream=True)
            response.raise_for_status()

            parser = ImageFile.Parser()
            for chunk in response.iter_content(chunk_size=1024):
                parser.feed(chunk)
                if parser.image:
                    width, height = parser.image.size
                    return width == target_width and height == target_height
            return False
        except (requests.exceptions.RequestException, OSError) as e:
            logging.warning(f"驗證尺寸失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return False
        except Exception as e:
            logging.error(f"驗證圖片尺寸發生未知錯誤: {e}")
            return False


def verify_image_min_dimensions(url, min_width, min_height, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=20, headers=HEADERS, stream=True)
            response.raise_for_status()

            parser = ImageFile.Parser()
            for chunk in response.iter_content(chunk_size=1024):
                parser.feed(chunk)
                if parser.image:
                    width, height = parser.image.size
                    return width >= min_width and height >= min_height
            return False
        except (requests.exceptions.RequestException, OSError) as e:
            logging.warning(f"驗證最小尺寸失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return False
        except Exception as e:
            logging.error(f"驗證圖片尺寸發生未知錯誤: {e}")
            return False


def download_pic(url, path, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=15, stream=True, headers=HEADERS)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').lower()
            if 'image/jpeg' in content_type:
                extension = '.jpg'
            elif 'image/png' in content_type:
                extension = '.png'
            elif 'image/webp' in content_type:
                extension = '.webp'
            elif 'image/gif' in content_type:
                extension = '.gif'
            elif 'image/avif' in content_type:
                extension = '.avif'
            else:
                extension = clean_extension(url)

            file_path = f"{path}{extension}"

            if attempt == 0 and os.path.exists(file_path):
                logging.info(f"圖片已存在，跳過下載: {file_path}")
                return True

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


def parse_srcset(srcset):
    try:
        raw_parts = srcset.split(',')
        candidates = []
        current_part = ""
        for part in raw_parts:
            if current_part:
                stripped = part.strip()
                if stripped.startswith("http") or stripped.startswith("//") or stripped.startswith("data:"):
                    candidates.append(current_part.strip())
                    current_part = part
                else:
                    current_part += "," + part
            else:
                current_part = part
        if current_part:
            candidates.append(current_part.strip())

        parsed = []
        for item in candidates:
            parts = item.split()
            if not parts:
                continue
            url = parts[0]
            w = None
            if len(parts) > 1 and parts[1].endswith("w"):
                try:
                    w = int(float(parts[1][:-1]))
                except Exception:
                    w = None
            if url.startswith("//"):
                url = "https:" + url
            parsed.append((url, w))

        widths = [p for p in parsed if p[1]]
        if widths:
            return max(widths, key=lambda x: x[1])

        for url, w in parsed:
            if not url.startswith(("data:", "blob:")):
                return (url, None)

        if parsed:
            return parsed[0]
        return None
    except Exception:
        return None


def extract_image_info(img):
    """Return dict with url, width, height, alt/title info when available."""
    best_url = None
    best_width = -1
    height = None
    alt = img.get("alt") or img.get("title") or ""

    try:
        w = img.get("width") or img.get("data-width") or img.get("data-size")
        h = img.get("height") or img.get("data-height")
        if w:
            try:
                best_width = int(w)
            except Exception:
                pass
        if h:
            try:
                height = int(h)
            except Exception:
                pass
    except Exception:
        pass

    for attr in ("srcset", "data-srcset", "data-lazy-srcset"):
        value = img.get(attr)
        if value:
            info = parse_srcset(value)
            if info:
                u, w = info
                if u and not u.startswith(("data:", "blob:")):
                    if w and w > best_width:
                        best_url = u
                        best_width = w
                    elif not best_url:
                        best_url = u

    for attr in ("data-fullsrc", "data-original", "data-src", "data-lazy", "src"):
        u = img.get(attr)
        if u and isinstance(u, str) and not u.startswith(("data:", "blob:")):
            if u.startswith("//"):
                u = "https:" + u
            if not best_url or attr in ("data-fullsrc", "data-original"):
                best_url = u
                if attr in ("data-fullsrc", "data-original"):
                    break

    if not best_url:
        return {"url": None, "width": None, "height": None, "alt": alt}

    if (best_width <= 0 or height is None) and best_url:
        try:
            match = re.search(r"(\d{3,5})[xX](\d{3,5})", best_url)
            if match:
                if best_width <= 0:
                    best_width = int(match.group(1))
                if height is None:
                    height = int(match.group(2))
            else:
                qs = {k: v for k, v in [part.split("=", 1) for part in best_url.split("?")[-1].split("&") if "=" in part]}
                if best_width <= 0 and "w" in qs:
                    try:
                        best_width = int(qs["w"])
                    except Exception:
                        pass
                if height is None and "h" in qs:
                    try:
                        height = int(qs["h"])
                    except Exception:
                        pass
        except Exception:
            pass

    return {
        "url": best_url,
        "width": best_width if best_width > 0 else None,
        "height": height,
        "alt": alt
    }


def parse_photo_urls(html, photo_dict, valid_prefixes):
    try:
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all("img"):
            info = extract_image_info(img)
            if not info or not info.get("url"):
                continue

            full_url = info["url"]
            base_url = full_url.split("?")[0]
            if not any(base_url.startswith(prefix) for prefix in valid_prefixes):
                continue

            if base_url not in photo_dict:
                photo_dict[base_url] = (full_url, info.get("width"), info.get("height"))
    except Exception as e:
        logging.error(f"解析 HTML 失敗: {e}")


def _is_challenge_page(browser):
    try:
        title = browser.title.lower()
        if any(k in title for k in ("just a moment", "attention required", "access denied", "robot")):
            return True
        source = browser.page_source.lower()
        return any(k in source for k in ("cf-browser-verification", "challenge-running", "cf_chl_opt"))
    except Exception:
        return False


def collect_photo_urls(browser, download_num, valid_prefixes, max_scrolls=20):
    photo_dict = {}
    wait = WebDriverWait(browser, 10)

    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
    except TimeoutException:
        logging.warning("等待圖片元素超時，無法收集圖片")
        return []

    last_height = browser.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    while len(photo_dict) < download_num and scroll_count < max_scrolls:
        html = browser.page_source
        parse_photo_urls(html, photo_dict, valid_prefixes)
        if len(photo_dict) >= download_num:
            logging.info(f"已收集足夠圖片: {len(photo_dict)}")
            break

        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_count += 1

    return list(photo_dict.values())[:download_num]


def get_photolist(photo_name, download_num, selected_sources=None, min_size=None):
    browser = None
    try:
        browser = create_webdriver()
        sources = [
            ("Pixabay", PIXABAY_SEARCH_URL, [PIXABAY_PHOTO_PREFIX, "https://pixabay.com/get/"]),
            ("Unsplash", UNSPLASH_SEARCH_URL, [UNSPLASH_PHOTO_PREFIX]),
            ("Pexels", PEXELS_SEARCH_URL, [PEXELS_PHOTO_PREFIX]),
        ]
        # If user specified selected_sources (list of names), filter sources
        if selected_sources:
            selected = set([s.lower() for s in selected_sources])
            sources = [s for s in sources if s[0].lower() in selected]

        photo_list = []
        collected_urls = set()
        candidate_goal = download_num if min_size is None else max(download_num * 5, download_num + 20)

        for source_name, base_url, prefixes in sources:
            if len(photo_list) >= download_num:
                break

            search_url = f"{base_url}{quote(photo_name)}"
            logging.info(f"從 {source_name} 搜尋: {search_url}")
            browser.get(search_url)
            time.sleep(5)

            if _is_challenge_page(browser):
                logging.warning(f"{source_name} 被反爬蟲攔截（Cloudflare challenge），跳過")
                continue

            photo_request_count = candidate_goal - len(collected_urls)
            if photo_request_count < 1:
                photo_request_count = candidate_goal
            source_photos = collect_photo_urls(browser, photo_request_count, prefixes)
            matched = 0
            for photo, known_w, known_h in source_photos:
                if photo in collected_urls:
                    continue
                collected_urls.add(photo)
                if min_size:
                    min_w, min_h = min_size
                    if known_w is not None and known_h is not None:
                        if known_w >= min_w and known_h >= min_h:
                            photo_list.append(photo)
                            matched += 1
                    elif verify_image_min_dimensions(photo, min_w, min_h):
                        photo_list.append(photo)
                        matched += 1
                else:
                    photo_list.append(photo)
                    matched += 1
                if len(photo_list) >= download_num:
                    break

            logging.info(f"從 {source_name} 收集到 {len(source_photos)} 張圖片，新增 {matched} 張，累計 {len(photo_list)} 張")

        return photo_list[:download_num]
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
        return folder_path
    except OSError as e:
        logging.error(f"建立資料夾失敗: {e}")
        raise
    except Exception as e:
        logging.error(f"建立資料夾時發生未知錯誤: {e}")
        raise


def download_photos(photo_list, target_folder, max_workers=5):
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

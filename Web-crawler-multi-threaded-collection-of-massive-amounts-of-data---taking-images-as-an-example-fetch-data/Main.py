import logging
import photo_module as m

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def prompt_for_input():
    while True:
        try:
            photo_name = input("請輸入要下載的圖片名稱: ").strip()
            if not photo_name:
                print("關鍵字不可為空，請重新輸入。")
                continue

            download_num = int(input("請輸入要下載的數量: "))
            if download_num <= 0:
                raise ValueError("下載數量必須為正整數")
            if download_num > 1000:
                print("下載數量過大，請輸入小於等於 1000 的數量。")
                continue

            parent_folder = input("請輸入要儲存的資料夾名稱: ").strip()
            return photo_name, download_num, parent_folder
        except ValueError as e:
            print(f"輸入無效: {e}。請重新輸入。")
        except KeyboardInterrupt:
            print("\n使用者中斷輸入")
            raise
        except Exception as e:
            logging.error(f"輸入時發生未知錯誤: {e}")
            print("發生未知錯誤，請重新輸入。")


def main():
    try:
        photo_name, download_num, parent_folder = prompt_for_input()
        logging.info(f"開始處理關鍵字: {photo_name}, 下載數量: {download_num}")

        photo_list = m.get_photolist(photo_name, download_num)

        if not photo_list:
            print("找不到圖片, 請換關鍵字再試試看")
            return

        if len(photo_list) < download_num:
            print(f"找到的相關圖片僅有 {len(photo_list)} 張")
        else:
            print("取得所有圖片連結")

        root_folder = m.create_folder(photo_name, parent_folder)
        print("開始下載...")
        m.download_photos(photo_list, root_folder, photo_name)
        print("\n下載完畢")
    except KeyboardInterrupt:
        print("\n程式被使用者中斷")
    except Exception as e:
        logging.error(f"主程式執行時發生錯誤: {e}")
        print(f"發生錯誤: {e}")


if __name__ == "__main__":
    main()

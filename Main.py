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

            # 選擇網站來源
            print("可選擇來源網站: 0:不限定網站, 1:Pixabay, 2:Unsplash, 3:Pexels")
            src_input = input("請輸入來源編號 (可逗號分隔多選，或留空為不限定網站): ").strip()
            mapping = {"1": "Pixabay", "2": "Unsplash", "3": "Pexels", "0": "All"}
            selected_sources = None
            if src_input:
                parts = [p.strip() for p in src_input.split(",") if p.strip()]
                names = []
                for p in parts:
                    if p in mapping and mapping[p] != "All":
                        names.append(mapping[p])
                if names:
                    selected_sources = names

            min_size = None
            print("\n請選擇圖片最小尺寸篩選條件:")
            print("0: 不設條件 (預設)")
            print("1: 小 (大於 640x480)")
            print("2: 中 (大於 1280x720)")
            print("3: 大 (大於 1920x1080)")
            print("4: 自訂尺寸")
            size_input = input("請輸入尺寸選項 (0-4，直接按 Enter 視為 0): ").strip()

            if size_input in ["", "0"]:
                min_size = None
            elif size_input == "1":
                min_size = (640, 480)
            elif size_input == "2":
                min_size = (1280, 720)
            elif size_input == "3":
                min_size = (1920, 1080)
            elif size_input == "4":
                min_width = input("請輸入最小寬度 (px): ").strip()
                min_height = input("請輸入最小高度 (px): ").strip()
                try:
                    min_w = int(min_width)
                    min_h = int(min_height)
                    if min_w > 0 and min_h > 0:
                        min_size = (min_w, min_h)
                    else:
                        print("寬度與高度必須為正整數；請重新輸入。")
                        continue
                except ValueError:
                    print("尺寸格式錯誤，請重新輸入。")
                    continue
            else:
                print("選項輸入錯誤，請輸入 0 到 4 之間的數字。")
                continue

            return photo_name, download_num, parent_folder, selected_sources, min_size
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
        photo_name, download_num, parent_folder, selected_sources, min_size = prompt_for_input()
        logging.info(f"開始處理關鍵字: {photo_name}, 下載數量: {download_num}")

        photo_list = m.get_photolist(photo_name, download_num, selected_sources=selected_sources, min_size=min_size)

        if not photo_list:
            print("找不到符合條件的圖片，請換關鍵字或放寬篩選條件再試試看")
            return

        if len(photo_list) < download_num:
            print(f"找到的相關圖片僅有 {len(photo_list)} 張")
        else:
            print("取得所有圖片連結")

        target_folder = m.create_folder(photo_name, parent_folder)
        print("開始下載...")
        m.download_photos(photo_list, target_folder)
        print("\n下載完畢")
    except KeyboardInterrupt:
        print("\n程式被使用者中斷")
    except Exception as e:
        logging.error(f"主程式執行時發生錯誤: {e}")
        print(f"發生錯誤: {e}")


if __name__ == "__main__":
    main()

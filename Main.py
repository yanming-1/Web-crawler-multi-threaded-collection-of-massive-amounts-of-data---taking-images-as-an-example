import os
import photo_module as m


def prompt_for_input():  # 提示使用者輸入搜尋關鍵字與下載數量。
    while True:
        photo_name = input("請輸入要下載的圖片名稱: ").strip()
        if not photo_name:
            print("關鍵字不可為空，請重新輸入。")
            continue

        try:
            download_num = int(input("請輸入要下載的數量: "))
            if download_num <= 0:
                raise ValueError
        except ValueError:
            print("請輸入正整數的下載數量。")
            continue

        return photo_name, download_num


def main():  # 執行主要流程：搜尋圖片、建立資料夾、下載圖片。
    photo_name, download_num = prompt_for_input()
    photo_list = m.get_photolist(photo_name, download_num)

    if not photo_list:
        print("找不到圖片, 請換關鍵字再試試看")
        return

    if len(photo_list) < download_num:
        print("找到的相關圖片僅有", len(photo_list), "張")
    else:
        print("取得所有圖片連結")

    root_folder = m.create_folder(photo_name)
    print("開始下載...")
    m.download_photos(photo_list, root_folder, photo_name)
    print("\n下載完畢")


if __name__ == "__main__":
    main()
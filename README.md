# Web Crawler 圖片下載器

簡單的圖片搜尋與下載工具，支援 Pixabay / Unsplash / Pexels / Bing / Flickr 搜尋並下載結果。

**需求**
- Python 3.8+
- Chrome 與對應的 ChromeDriver（放在 PATH 或系統可存取位置）
- 套件: `selenium`, `beautifulsoup4`, `requests`, `tqdm`, `lxml`, `Pillow`

安裝套件範例：

```bash
pip install selenium beautifulsoup4 requests tqdm lxml Pillow
```

**檔案**
- `Main.py`：主程式，互動式輸入搜尋字串、數量、儲存資料夾、來源與篩選條件。
- `photo_module.py`：搜尋、解析與下載相關邏輯。

**使用方式**

1. 執行：

```bash
python Main.py
```

2. 依序輸入提示：
- 搜尋關鍵字（例如 `dog`）
- 下載數量（正整數，最大建議 <=1000）
- 儲存資料夾（相對或絕對路徑，例如 `downloads`）
- 來源網站（輸入編號，多選可逗號分隔，或留空為不限定網站）：
  - `0` 不限定網站
  - `1` Pixabay
  - `2` Unsplash
  - `3` Pexels
  - `4` Bing
  - `5` Flickr
- 篩選條件（可留空）：
  - 精準尺寸選項（例如 `1920x1080`、`800x600`，或自訂寬度/高度）

範例互動輸入：
```
關鍵字: dog
數量: 10
資料夾: downloads
來源: 1,3
尺寸: 4
```

下載結果會儲存在 `parent_folder/photo_name/` 底下，檔名以索引編號命名（會自動加上副檔名）。

**注意事項與限制**
- 篩選的寬高來自頁面 `srcset` 或 `width/height` 屬性：若網站未提供，寬高條件可能無效。
- 若要在無頭（headless）或無瀏覽器環境運行，需自行調整 `photo_module.create_webdriver()` 或使用遠端 WebDriver。 
- 請遵守各網站的使用條款與版權規範，僅下載有權使用的資源。

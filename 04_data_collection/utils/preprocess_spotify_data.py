from pathlib import Path

import numpy as np
import pandas as pd

# ---------- 路徑設定 ----------
# 假設此檔案放在專案的 utils 或 scripts 資料夾中，BASE_DIR 指向專案根目錄
if "__file__" in locals():
    BASE_DIR = Path(__file__).resolve().parent.parent
else:
    BASE_DIR = Path(".")

DATASET_DIR = BASE_DIR / "dataset"
INPUT_CSV = DATASET_DIR / "spotify_track_dataset.csv"
OUTPUT_CURRENT = DATASET_DIR / "spotify_track_dataset_current.csv"
OUTPUT_NEW = DATASET_DIR / "spotify_track_dataset_new.csv"


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"找不到輸入檔案: {INPUT_CSV}，請確認已下載並放入正確位置。")

    print(f"開始讀取資料: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)

    # 1. 讀取並初步清理
    if "Unnamed: 0" in df.columns:
        df.drop(columns=["Unnamed: 0"], inplace=True)

    print(f"原始資料形狀: {df.shape}")

    # 2. 清理資料 (移除重複與缺失值)
    duplicated_rows = df.duplicated().sum()
    if duplicated_rows > 0:
        df = df.drop_duplicates()
        print(f"已刪除 {duplicated_rows} 筆重複資料")

    initial_rows = len(df)
    df = df.dropna()
    print(f"已刪除 {initial_rows - len(df)} 筆含缺失值的資料")

    # 3. 檢查異常值範圍
    df = df.loc[df['time_signature'] >= 3]
    df = df[df['duration_ms'] != 0]
    print(f"刪除異常值後資料形狀: {df.shape}")

    # 4. 轉換特定欄位為類別型態 (提升可讀性)
    df['time_signature'] = df['time_signature'].replace({
        3: '3/4', 4: '4/4', 5: '5/4', 6: '6/4', 7: '7/4'
    })

    df['key'] = df['key'].replace({
        0: 'C', 1: 'C-sharp_D-flat', 2: 'D', 3: 'D-sharp_E-flat',
        4: 'E', 5: 'F', 6: 'F-sharp_G-flat', 7: 'G',
        8: 'G-sharp_A-flat', 9: 'A', 10: 'A-sharp_B-flat', 11: 'B'
    })

    df['mode'] = df['mode'].replace({0: 'minor', 1: 'major'})
    df['explicit'] = np.where(df['explicit'] == False, 'no', 'yes')

    # 【效能修正】使用 np.select 取代原書極慢的 for i in df.speechiness 迴圈
    conditions = [
        df['speechiness'] < 0.33,
        (df['speechiness'] >= 0.33) & (df['speechiness'] <= 0.66)
    ]
    choices = ['Low', 'Medium']
    df['speechiness_type'] = np.select(conditions, choices, default='High')

    print("語音特徵分類統計:")
    print(df['speechiness_type'].value_counts())

    # 5. 分割資料 (模擬 DVC 版本控制使用)
    cutoff = 100_000
    if len(df) > cutoff:
        subset1_df = df.iloc[:cutoff, :]
        subset2_df = df.iloc[cutoff:, :]
    else:
        print("警告：資料總筆數不足 100,000 筆，將不進行分割。")
        subset1_df = df
        subset2_df = pd.DataFrame(columns=df.columns)

    # 6. 儲存處理後的資料
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    subset1_df.to_csv(OUTPUT_CURRENT, index=False)
    subset2_df.to_csv(OUTPUT_NEW, index=False)

    print(f"\n資料處理完成！")
    print(f"初始訓練集 (subset1) 形狀: {subset1_df.shape} -> 儲存至 {OUTPUT_CURRENT.name}")
    print(f"新增模擬集 (subset2) 形狀: {subset2_df.shape} -> 儲存至 {OUTPUT_NEW.name}")

if __name__ == "__main__":
    main()
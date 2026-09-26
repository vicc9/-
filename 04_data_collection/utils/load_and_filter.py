"""步驟 1：邊讀邊篩選 train_triplets.txt，只保留資料庫中歌曲的聆聽紀錄，並存成 CSV。"""
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.exc import OperationalError
from sqlmodel import create_engine, select

from model import Song, create_session

try:
    import pyarrow as pa
    import pyarrow.csv as pacsv
    import pyarrow.compute as pc
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False

# ---------- 路徑（以本檔案位置為基準，與執行時的工作目錄無關） ----------
BASE_DIR = Path(__file__).resolve().parent.parent  # 04_data_collection
DATASET_DIR = BASE_DIR / "dataset"
TRIPLETS_PATH = DATASET_DIR / "train_triplets.txt"
SUBSET_CSV_PATH = DATASET_DIR / "listening_history_subset.csv"
COLUMNS = ["user_id", "song_id", "play_count"]

# 改成你的 PostgreSQL 設定
ENGINE_URL = "postgresql://username:password@localhost:5432/music_database"


def get_unique_song_ids():
    """從資料庫查出所有不重複的 song_id。"""
    engine = create_engine(ENGINE_URL, echo=False)  # echo=True 會印出大量 SQL
    with create_session(engine) as session:
        stmt = select(Song.song_id).distinct()
        return list(session.exec(stmt))


def filter_with_pyarrow(song_ids):
    """pyarrow 串流讀取：多執行緒解析，速度快，且不會一次載入全部資料。"""
    reader = pacsv.open_csv(
        TRIPLETS_PATH,
        read_options=pacsv.ReadOptions(column_names=COLUMNS, block_size=64 << 20),
        parse_options=pacsv.ParseOptions(delimiter="\t", quote_char=False),
        convert_options=pacsv.ConvertOptions(
            column_types={
                "user_id": pa.string(),
                "song_id": pa.string(),
                "play_count": pa.int32(),
            }
        ),
    )
    value_set = pa.array(song_ids)
    kept, total = [], 0
    for batch in reader:
        total += batch.num_rows
        mask = pc.is_in(batch["song_id"], value_set=value_set)
        kept.append(batch.filter(mask))
        print(f"  已處理 {total:,} 筆...", end="\r")
    print()
    return pa.Table.from_batches(kept, schema=reader.schema).to_pandas(), total


def filter_with_pandas(song_ids, chunk_size=1_000_000):
    """沒有安裝 pyarrow 時的備案：pandas 分批讀取（省記憶體，但速度較慢）。"""
    song_set = set(song_ids)  # set 查詢比 list 快很多
    kept, total = [], 0
    reader = pd.read_csv(
        TRIPLETS_PATH,
        sep="\t",
        names=COLUMNS,
        dtype={"user_id": str, "song_id": str, "play_count": "int32"},
        chunksize=chunk_size,
    )
    for chunk in reader:
        total += len(chunk)
        kept.append(chunk[chunk["song_id"].isin(song_set)])
        print(f"  已處理 {total:,} 筆...", end="\r")
    print()
    return pd.concat(kept, ignore_index=True), total


def main():
    """主流程：查詢 song_id -> 分批篩選 -> 儲存 CSV。"""
    print("檔案是否存在:", TRIPLETS_PATH, TRIPLETS_PATH.exists())
    if not TRIPLETS_PATH.exists():
        sys.exit("找不到 train_triplets.txt，請確認已解壓縮並放在 dataset/ 資料夾。")

    # 1. 先查資料庫（連不上就立刻停止，不必白等讀檔）
    try:
        unique_song_ids = get_unique_song_ids()
    except OperationalError as e:
        sys.exit(f"無法連線到 PostgreSQL，請確認服務已啟動且帳號密碼正確。\n原始錯誤：{e.orig}")

    print(f"Number of unique songs in the database: {len(unique_song_ids)}")
    print(unique_song_ids[:10])
    if not unique_song_ids:
        sys.exit("songs 表是空的，請先執行 app.py 匯入 Million Song Dataset subset。")

    # 2. 邊讀邊篩選
    if HAS_PYARROW:
        subset, total_rows = filter_with_pyarrow(unique_song_ids)
    else:
        print("未安裝 pyarrow，改用 pandas 分批讀取（`uv add pyarrow` 可加速）")
        subset, total_rows = filter_with_pandas(unique_song_ids)

    print(f"原始聆聽紀錄筆數: {total_rows:,}")
    print(f"Number of listening history entries after filtering: {subset.shape[0]}")

    # 3. 儲存到 dataset 資料夾（絕對路徑，不受工作目錄影響）
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    subset.to_csv(SUBSET_CSV_PATH, index=False)
    print(f"已儲存至 {SUBSET_CSV_PATH}（{SUBSET_CSV_PATH.stat().st_size / 1e6:.1f} MB）")


if __name__ == "__main__":
    main()
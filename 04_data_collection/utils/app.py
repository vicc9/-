"""將 Million Song Dataset subset (.h5) 批量寫入 PostgreSQL（artists / songs / audio_features）。"""
import glob
import math
import os
import traceback
from pathlib import Path

import numpy as np
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, create_engine, func, select

import hdf5_getters
from model import Artist, AudioFeatures, Song, create_session, create_table, drop_table
from utils import extract_h5_info

# ====== 請依你的 PostgreSQL 設定修改 ======
ENGINE_URL = "postgresql://username:password@localhost:5432/music_database"
# ==========================================


def find_dataset_root() -> Path:
    """在腳本所在資料夾、上一層、目前工作目錄下尋找 dataset/MillionSongSubset。"""
    here = Path(__file__).resolve().parent
    tried = []
    for base in (here, here.parent, Path.cwd()):
        candidate = base / "dataset" / "MillionSongSubset"
        tried.append(str(candidate))
        if candidate.exists():
            return candidate
    raise FileNotFoundError("找不到 MillionSongSubset 資料夾，已嘗試：\n  " + "\n  ".join(tried))


def sanitize_value(value):
    """轉成 psycopg2 能寫入的 Python 原生型別。

    hdf5_getters 回傳的是 numpy 型別 / bytes（例如 np.float64、np.int32、np.bytes_）。
    psycopg2 無法直接處理，NumPy 2.x 下常見錯誤：schema "np" does not exist。
    """
    if isinstance(value, np.generic):
        value = value.item()  # numpy 純量 -> Python 原生型別
    if isinstance(value, (bytes, bytearray)):
        value = bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        value = value.replace("\x00", "")  # PostgreSQL 不接受 NUL 字元
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


def insert_song_data_bulk_mappings(session: Session, h5_data_list: list):
    artist_mappings = [
        {
            "artist_id": sanitize_value(info["artist_id"]),
            "artist_name": sanitize_value(info["artist_name"]),
            "artist_hotness": sanitize_value(info["artist_hotness"]),
        }
        for info in h5_data_list
    ]
    song_mappings = [
        {
            "song_id": sanitize_value(info["song_id"]),
            "artist_id": sanitize_value(info["artist_id"]),
            "song_title": sanitize_value(info["song_title"]),
            "song_hotness": sanitize_value(info["song_hotness"]),
            "year": sanitize_value(info["year"]),
        }
        for info in h5_data_list
    ]
    audio_features_mappings = [
        {
            "song_id": sanitize_value(info["song_id"]),
            "danceability": sanitize_value(info["audio_features"]["danceability"]),
            "energy": sanitize_value(info["audio_features"]["energy"]),
            "key": sanitize_value(info["audio_features"]["key"]),
            "loudness": sanitize_value(info["audio_features"]["loudness"]),
            "tempo": sanitize_value(info["audio_features"]["tempo"]),
        }
        for info in h5_data_list
    ]

    try:
        # 順序不可換：artists -> songs -> audio_features（外鍵相依）
        # 用 ON CONFLICT DO NOTHING，重複資料會被略過而不是讓整批失敗
        for model, mappings in (
            (Artist, artist_mappings),
            (Song, song_mappings),
            (AudioFeatures, audio_features_mappings),
        ):
            session.exec(insert(model).values(mappings).on_conflict_do_nothing())
        session.commit()
        print(f"Successfully inserted {len(h5_data_list)} records in this batch.")
    except Exception:
        session.rollback()
        print("Bulk insert error（下方為完整錯誤）：")
        traceback.print_exc()
        raise  # 不再吞掉錯誤，避免出現「顯示完成但資料庫是空的」


def process_h5_files_in_batches(h5_files: list, engine, batch_size: int = 1000):
    batch, failed_files, total = [], 0, 0

    def flush():
        nonlocal batch, total
        if batch:
            with create_session(engine) as session:
                insert_song_data_bulk_mappings(session, batch)
            total += len(batch)
            batch = []

    for file_path in h5_files:
        h5 = None
        try:
            h5 = hdf5_getters.open_h5_file_read(file_path)
            for i in range(hdf5_getters.get_num_songs(h5)):
                batch.append(extract_h5_info(h5, i))
        except Exception as e:
            failed_files += 1
            if failed_files <= 5:  # 只印前 5 筆，避免洗版
                print(f"Error processing {file_path}: {type(e).__name__}: {e}")
        finally:
            if h5 is not None:
                h5.close()
        if len(batch) >= batch_size:
            flush()
    flush()  # 寫入最後不滿一批的資料
    return total, failed_files


def print_table_counts(engine):
    with create_session(engine) as session:
        for model in (Artist, Song, AudioFeatures):
            count = session.exec(select(func.count()).select_from(model)).one()
            print(f"  {model.__tablename__}: {count:,} 筆")


if __name__ == "__main__":
    root_dir = find_dataset_root()
    h5_files = glob.glob(os.path.join(str(root_dir), "**", "*.h5"), recursive=True)
    print(f"資料夾: {root_dir}")
    print(f"找到 {len(h5_files):,} 個 .h5 檔案")
    if not h5_files:
        raise SystemExit("沒有找到任何 .h5 檔案，請確認 MillionSongSubset 已解壓縮。")

    engine = create_engine(ENGINE_URL, echo=False)  # echo=True 會洗版並蓋掉錯誤訊息

    print("Dropping existing tables...")
    drop_table(engine)
    print("Creating new tables...")
    create_table(engine)

    print("Starting data processing and insertion...")
    total, failed = process_h5_files_in_batches(h5_files, engine, batch_size=1000)
    print(f"Data insertion complete. 寫入 {total:,} 筆，讀取失敗 {failed} 個檔案。")
    print("資料庫現況：")
    print_table_counts(engine)
from pathlib import Path
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    PayloadSchemaType,
)

from app.core.config import settings

# -----------------------------------------------------------------------------
# 0. 讀取先前步驟篩選好的 CSV 資料
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent if "__file__" in locals() else Path(".")
TRIPLETS_CSV = BASE_DIR / "dataset" / "listening_history_subset.csv"

if not TRIPLETS_CSV.exists():
    TRIPLETS_CSV = Path("listening_history_subset.csv")  # 備用相對路徑

listening_history_subset = pd.read_csv(TRIPLETS_CSV)


# -----------------------------------------------------------------------------
# 0.5【新增】過濾掉播放紀錄過少的用戶
# -----------------------------------------------------------------------------
# 因為 songs 表只涵蓋 MillionSongSubset（約 1 萬首歌），對全量 train_triplets.txt
# 篩選後，大多數使用者只會留下 1 筆紀錄，導致 SVD 後這些「單曲用戶」的向量方向
# 完全由那首歌決定，造成大量使用者相似度 = 1.0、推薦系統失去意義。
# 這裡先把播放紀錄數過少的用戶整批排除，只保留紀錄較豐富、向量較能代表
# 個人聽歌偏好的用戶，避免污染後續的相似度計算。
MIN_PLAYS_PER_USER = 5  # 可依實際資料量調整這個門檻

before_rows = len(listening_history_subset)
before_users = listening_history_subset["user_id"].nunique()

user_play_counts = listening_history_subset.groupby("user_id").size()
valid_users = user_play_counts[user_play_counts >= MIN_PLAYS_PER_USER].index

listening_history_subset = listening_history_subset[
    listening_history_subset["user_id"].isin(valid_users)
].reset_index(drop=True)

after_rows = len(listening_history_subset)
after_users = listening_history_subset["user_id"].nunique()

print(f"[過濾] 門檻: 每位使用者至少 {MIN_PLAYS_PER_USER} 筆播放紀錄")
print(f"[過濾] 使用者數: {before_users:,} -> {after_users:,}")
print(f"[過濾] 紀錄筆數: {before_rows:,} -> {after_rows:,}")

if after_users == 0:
    raise SystemExit(
        f"過濾後沒有任何使用者符合門檻（>= {MIN_PLAYS_PER_USER} 筆），"
        "請降低 MIN_PLAYS_PER_USER 或改用完整版 Million Song Dataset。"
    )


# -----------------------------------------------------------------------------
# 1. 建立 User-Song 稀疏矩陣 Function
# -----------------------------------------------------------------------------
def create_sparse_user_song_matrix(listening_history):
    users = listening_history["user_id"].unique()
    songs = listening_history["song_id"].unique()

    user_to_idx = {user: idx for idx, user in enumerate(users)}
    song_to_idx = {song: idx for idx, song in enumerate(songs)}

    # 【修正】改用 .map() 替代 iterrows()，將處理速度從幾十分鐘大幅縮短至數秒
    row_indices = listening_history["user_id"].map(user_to_idx).values
    col_indices = listening_history["song_id"].map(song_to_idx).values
    play_counts = listening_history["play_count"].values

    user_song_matrix = csr_matrix(
        (play_counts, (row_indices, col_indices)),
        shape=(len(users), len(songs))
    )

    return user_song_matrix, user_to_idx, song_to_idx


# -----------------------------------------------------------------------------
# 2. 轉換矩陣並輸出統計資訊
# -----------------------------------------------------------------------------
user_song_matrix, user_to_idx, song_to_idx = create_sparse_user_song_matrix(listening_history_subset)

# 建立反向對照字典
idx_to_song = {v: k for k, v in song_to_idx.items()}
idx_to_user = {v: k for k, v in user_to_idx.items()}  # 【新增】供後續高效率反查 user_id

print(f"The number of songs = {len(song_to_idx.keys())}")
print(f"The number of users = {len(user_to_idx.keys())}")


# -----------------------------------------------------------------------------
# 3. 降維處理 (Truncated SVD)
# -----------------------------------------------------------------------------
# 【修正】n_components 不能大於等於 min(矩陣的列數, 欄數)，過濾後使用者/歌曲數
# 可能變少，這裡動態夾住上限，避免 TruncatedSVD 直接報錯。
n_components = min(256, min(user_song_matrix.shape) - 1)
if n_components < 1:
    raise SystemExit("使用者或歌曲數過少，無法進行 SVD 降維，請降低 MIN_PLAYS_PER_USER。")

svd = TruncatedSVD(n_components=n_components, random_state=42)
reduced_vectors = svd.fit_transform(user_song_matrix)

print(f"降維後矩陣形狀: {reduced_vectors.shape}")


# -----------------------------------------------------------------------------
# 4. 連線至 Qdrant 並建立 Collection
# -----------------------------------------------------------------------------
client = QdrantClient(
    url=settings.VECTOR_DATABASE_URL,
    api_key=settings.QDRANT_API_KEY,
)

collection_name = settings.COLLECTION_NAME_USER_HISTORY

print(f"連線 Qdrant: {settings.VECTOR_DATABASE_URL}")
print(f"Collection: {collection_name}")


# 如果 Collection 已存在，刪除後重新建立
if client.collection_exists(collection_name):
    print(
        f"⚠️ Collection 已存在，將重新建立: "
        f"{collection_name}"
    )

    client.delete_collection(collection_name)


# 建立 Collection
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(
        size=n_components,
        distance=Distance.COSINE,
    ),
)

print(
    f"✅ Collection 建立完成: {collection_name}"
)


# 建立 original_id Payload Index
client.create_payload_index(
    collection_name=collection_name,
    field_name="original_id",
    field_schema=PayloadSchemaType.KEYWORD,
)

print(
    "✅ Payload Index 建立完成: "
    f"{collection_name}.original_id"
)

# -----------------------------------------------------------------------------
# 5. 批量插入向量數據至 Qdrant
# -----------------------------------------------------------------------------
batch_size = 1000  # 【修正】補上原書遺漏的 batch_size 宣告

for batch_start in range(0, len(reduced_vectors), batch_size):
    batch_end = min(batch_start + batch_size, len(reduced_vectors))
    batch_vectors = reduced_vectors[batch_start:batch_end]

    points = []
    for local_idx, vector in enumerate(batch_vectors):
        global_idx = batch_start + local_idx

        payload = {
            "original_index": global_idx,
            "type": "user_vector"
        }

        # 【修正】改用字典反查 idx_to_user，取代原書超慢的 list.index() 操作
        if global_idx in idx_to_user:
            payload["original_id"] = idx_to_user[global_idx]

        point = PointStruct(
            id=global_idx,
            vector=vector.tolist(),
            payload=payload
        )
        points.append(point)

    client.upsert(
        collection_name=collection_name,
        points=points
    )

    if batch_start % 5000 == 0:
        print(f"Uploaded batch {batch_start // batch_size + 1}")


# -----------------------------------------------------------------------------
# 6. 驗證寫入數據
# -----------------------------------------------------------------------------
info = client.get_collection(collection_name=collection_name)
print("總數據點:", info.points_count)

points = client.retrieve(
    collection_name=collection_name,
    ids=[0],
    with_vectors=False
)
print(points)
"""將本機 Qdrant 的 user_song_vectors collection 遷移到 Qdrant Cloud。"""
import time
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, PointStruct
import os
from dotenv import load_dotenv

load_dotenv()
COLLECTION_NAME = "user_song_vectors"

# 本機來源
local_client = QdrantClient("localhost", port=6333)

# 雲端目的地（換成你自己的 Cluster URL 和 API Key）
cloud_client = QdrantClient(
    url=os.getenv("QDRANT_CLOUD_URL"),
    api_key=os.getenv("QDRANT_CLOUD_API_KEY"),
    timeout=60,
)

# 1. 讀取本機 collection 的設定，在雲端建立同樣規格的 collection
info = local_client.get_collection(COLLECTION_NAME)
vector_size = info.config.params.vectors.size
distance = info.config.params.vectors.distance

if not cloud_client.collection_exists(COLLECTION_NAME):
    cloud_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=distance),
    )

# 2. 分批把本機的點讀出來，寫進雲端
offset = None
batch_size = 100
total_migrated = 0

while True:
    points, offset = local_client.scroll(
        collection_name=COLLECTION_NAME,
        limit=batch_size,
        offset=offset,
        with_vectors=True,
        with_payload=True,
    )
    if not points:
        break

    point_structs = [
        PointStruct(id=record.id, vector=record.vector, payload=record.payload)
        for record in points
    ]

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            cloud_client.upsert(collection_name=COLLECTION_NAME, points=point_structs)
            break
        except Exception as e:
            print(f"第 {attempt} 次嘗試失敗：{e}")
            if attempt == max_retries:
                raise
            print("2 秒後重試...")
            time.sleep(2)

    total_migrated += len(points)
    print(f"已遷移 {total_migrated} 筆")

    if offset is None:
        break

print(f"完成！總共遷移 {total_migrated} 筆向量到 Qdrant Cloud。")
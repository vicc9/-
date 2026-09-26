"""列出目前 Qdrant collection 裡實際存在的 user_id（供測試用）。"""
from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)
collection_name = "user_song_vectors"

info = client.get_collection(collection_name=collection_name)
print(f"Qdrant collection '{collection_name}' 目前總數據點: {info.points_count}")

# 撈前 20 筆，看看有哪些 original_id 可以拿來測試
records, _ = client.scroll(
    collection_name=collection_name,
    limit=20,
    with_payload=True,
    with_vectors=False,
)

print("\n可用來測試的 user_id（前 20 筆）：")
for r in records:
    original_id = r.payload.get("original_id") if r.payload else None
    print(f"  point_id={r.id}, original_id={original_id}")

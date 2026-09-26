"""診斷：確認連到哪個資料庫、有哪些資料表、各表有幾筆資料。"""
from sqlalchemy import inspect, text
from sqlmodel import create_engine

engine_url = "postgresql://username:password@localhost:5432/music_database"  # 改成你的設定
engine = create_engine(engine_url)

with engine.connect() as conn:
    # 1. 目前連到的資料庫，以及伺服器上所有資料庫
    try:
        print("目前資料庫:", conn.execute(text("select current_database()")).scalar())
        rows = conn.execute(text("select datname from pg_database where not datistemplate"))
        print("伺服器上的資料庫:", [r[0] for r in rows])
    except Exception as e:
        conn.rollback()
        print("（略過 PostgreSQL 專用查詢）", e)

    # 2. 所有資料表與筆數
    insp = inspect(conn)
    schemas = [s for s in insp.get_schema_names() if s not in ("information_schema", "pg_catalog", "pg_toast")]
    for schema in schemas:
        for table in insp.get_table_names(schema=schema):
            count = conn.execute(text(f'select count(*) from "{schema}"."{table}"')).scalar()
            print(f"  {schema}.{table}: {count:,} 筆")

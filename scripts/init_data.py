"""
从 data/documents.json 导入或更新文档，并写入 SQLite + 向量库。
用法（在项目根目录）:
  python scripts/init_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db
from app.services.content_service import seed_from_json_file


def main() -> None:
    init_db()
    path = ROOT / "data" / "documents.json"
    db = SessionLocal()
    try:
        n = seed_from_json_file(db, path)
        print(f"已处理 {n} 条记录（来自 {path}）")
    finally:
        db.close()


if __name__ == "__main__":
    main()

"""SQLite 계정·문의를 PostgreSQL로 복사. 기존 자료와 세션은 삭제하지 않는다."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import Database
from app.auth import Auth


def migrate(source, url):
    # URI read-only: 경로 오타로 새 SQLite DB를 만들지 않는다.
    with sqlite3.connect(Path(source).resolve().as_uri() + '?mode=ro', uri=True) as src:
        users = src.execute('SELECT id,username,password_hash,role FROM users').fetchall()
        records = src.execute('SELECT id,body,receipt_no,student_id FROM inquiries').fetchall()
    db = Database(source, url)
    Auth(db.connect).initialize(seed=False)
    db.initialize_inquiries()
    added_users = added_records = 0
    with db.connect() as dest:
        dest.execute('ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS receipt_no TEXT')
        dest.execute('ALTER TABLE inquiries ADD COLUMN IF NOT EXISTS student_id TEXT REFERENCES users(id)')
        dest.execute('CREATE UNIQUE INDEX IF NOT EXISTS inquiries_receipt_no ON inquiries(receipt_no)')
        dest.execute('CREATE INDEX IF NOT EXISTS inquiries_student_id ON inquiries(student_id)')
        for row in users:
            found = dest.execute('SELECT id,username,password_hash,role FROM users WHERE id=? OR username=?', row[:2]).fetchall()
            if found:
                if found != [row]:
                    raise ValueError('대상 DB 계정과 충돌합니다. 기존 자료를 덮어쓰지 않습니다.')
                continue
            dest.execute('INSERT INTO users VALUES (?,?,?,?)', row)
            added_users += 1
        for row in records:
            json.loads(row[1])
            found = dest.execute('SELECT id,body,receipt_no,student_id FROM inquiries WHERE id=? OR receipt_no=?', (row[0],row[2])).fetchall()
            if found:
                if found != [row]:
                    raise ValueError('대상 DB 문의와 충돌합니다. 기존 자료를 덮어쓰지 않습니다.')
                continue
            dest.execute('INSERT INTO inquiries(id,body,receipt_no,student_id) VALUES (?,?,?,?)', row)
            added_records += 1
    return {'users_copied':added_users, 'inquiries_copied':added_records, 'sessions_copied':0}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root/'backend/.env'); load_dotenv(root/'.env')
    parser = argparse.ArgumentParser(description='SQLite 계정·문의 → PostgreSQL 복사')
    parser.add_argument('--source', type=Path, default=root/'backend/data/inquiries.sqlite3')
    args = parser.parse_args()
    url = os.getenv('DATABASE_URL')
    if not url:
        parser.error('.env에 DATABASE_URL을 먼저 설정해 주세요.')
    try:
        print(json.dumps(migrate(args.source,url), ensure_ascii=False))
    except Exception:
        # DB 예외에는 연결 정보가 포함될 수 있어 그대로 출력하지 않는다.
        sys.exit('이전 실패: 연결·스키마·기존 데이터 충돌을 확인해 주세요. 기존 자료는 덮어쓰지 않았습니다.')

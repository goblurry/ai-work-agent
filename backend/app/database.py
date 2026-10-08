"""문의·계정 DB 연결. DATABASE_URL 설정 시 PostgreSQL, 로컬 테스트는 SQLite."""
import os
import sqlite3
from pathlib import Path


class Connection:
    def __init__(self, raw, postgres=False):
        self.raw = raw
        self.postgres = postgres

    def execute(self, sql, params=()):
        if self.postgres:
            sql = sql.replace("json_extract(body, '$.channel')", "(body::jsonb ->> 'channel')")
            sql = sql.replace('ORDER BY rowid DESC', "ORDER BY (body::jsonb ->> 'created_at') DESC, id DESC")
            sql = sql.replace('?', '%s')
        return self.raw.execute(sql, params)

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        try:
            if kind is None:
                self.raw.commit()
            else:
                self.raw.rollback()
        finally:
            self.raw.close()

    def columns(self, table):
        if self.postgres:
            return {row[0] for row in self.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=?", (table,)).fetchall()}
        return {row[1] for row in self.execute(f'PRAGMA table_info({table})').fetchall()}


class Database:
    def __init__(self, path, url=None):
        self.path = Path(path)
        self.url = url
        if url and not url.startswith(('postgresql://', 'postgres://')):
            raise ValueError('DATABASE_URL에는 PostgreSQL 연결 문자열을 설정해 주세요.')

    def connect(self):
        if self.url:
            import psycopg
            # 원격 연결은 TLS를 사용. 로컬 통합 테스트만 sslmode=disable을 명시한다.
            raw = psycopg.connect(self.url, connect_timeout=10,
                                   **({} if 'sslmode=' in self.url else {'sslmode': 'require'}))
            return Connection(raw, postgres=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(self.path, timeout=10)
        raw.execute('PRAGMA foreign_keys=ON')
        return Connection(raw)

    def initialize_inquiries(self):
        with self.connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS inquiries (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
            if conn.postgres:
                conn.execute('ALTER TABLE inquiries ENABLE ROW LEVEL SECURITY')

"""외부 DB와 검색 인덱스를 준비한 뒤 API 서버 실행."""
import os
import subprocess
import sys
from pathlib import Path

if not os.getenv('DATABASE_URL'):
    sys.exit('DATABASE_URL 설정이 필요합니다. 배포 환경에서는 SQLite를 사용하지 않습니다.')
for key in ('QDRANT_URL', 'QDRANT_API_KEY', 'QDRANT_COLLECTION', 'OPENAI_API_KEY'):
    if not os.getenv(key):
        sys.exit(f'{key} 설정이 필요합니다.')
if not Path('backend/data/course_index.sqlite3').exists():
    subprocess.run([sys.executable, 'backend/scripts/build_course_index.py'], check=True)
os.execvp(sys.executable, [sys.executable, '-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend',
                          '--host', '0.0.0.0', '--port', '7860', '--proxy-headers'])

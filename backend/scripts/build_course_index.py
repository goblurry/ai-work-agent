"""벡터를 받지 않고 Qdrant 공개 학사 본문으로 학수번호 인덱스 생성."""
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import httpx
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[2]
load_dotenv(ROOT/'backend/.env');load_dotenv(ROOT/'.env')
sys.path.insert(0,str(ROOT/'backend'))
from app.courses import INDEX_PATH

INDEX_PATH.parent.mkdir(parents=True,exist_ok=True)
staging=INDEX_PATH.with_suffix('.building.sqlite3')
if staging.exists():
    staging.unlink()
keys=('chunk_id','doc_id','title','text','source_url','source_type','section','applicability','dates',
      'course_rows','major_track','source_file','page','related_chunk_ids','quality_flags','metadata_review_required')
with sqlite3.connect(staging) as db, httpx.Client(timeout=60,headers={'api-key':os.environ['QDRANT_API_KEY']}) as client:
    db.execute('CREATE TABLE chunks(chunk_id TEXT PRIMARY KEY,body TEXT NOT NULL)')
    db.execute('CREATE TABLE codes(code TEXT NOT NULL,chunk_id TEXT NOT NULL,PRIMARY KEY(code,chunk_id))')
    offset=None;scanned=0;indexed=0
    while True:
        body={'limit':512,'with_vector':False,'with_payload':list(keys)}
        if offset is not None:body['offset']=offset
        r=client.post(os.environ['QDRANT_URL'].rstrip('/')+'/collections/'+os.environ['QDRANT_COLLECTION']+'/points/scroll',json=body)
        r.raise_for_status();result=r.json()['result']
        for point in result['points']:
            p=point.get('payload',{});text=p.get('text') or ''
            numbers=set(re.findall(r'(?<!\d)\d{5}(?!\d)',text))
            if numbers and p.get('chunk_id'):
                db.execute('INSERT OR REPLACE INTO chunks VALUES (?,?)',(p['chunk_id'],json.dumps(p,ensure_ascii=False)))
                db.executemany('INSERT OR IGNORE INTO codes VALUES (?,?)',[(code,p['chunk_id']) for code in numbers])
                indexed+=1
        scanned+=len(result['points']);offset=result.get('next_page_offset')
        if scanned % 2048==0:print('scanned',scanned,'indexed',indexed,flush=True)
        if offset is None:break
    db.execute('CREATE TABLE metadata(collection TEXT,scanned INTEGER,indexed INTEGER)')
    db.execute('INSERT INTO metadata VALUES (?,?,?)',(os.environ['QDRANT_COLLECTION'],scanned,indexed))
staging.replace(INDEX_PATH)
print('index_ready',scanned,indexed,round(INDEX_PATH.stat().st_size/1024**2,1),'MB',flush=True)

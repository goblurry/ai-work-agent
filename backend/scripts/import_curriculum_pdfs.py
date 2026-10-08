"""유레카 출력 PDF를 검증·JSONL 변환 후 기존 Qdrant에 추가한다."""
import argparse,hashlib,json,os,re,sqlite3,sys,unicodedata
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL,uuid5
from zoneinfo import ZoneInfo
import httpx,pdfplumber
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.search import local_model
from app.courses import INDEX_PATH
URL='https://eureka.ewha.ac.kr/eureka/my/public.do?pgId=P531005523'
LABELS=['구분','영역명/학수번호','교과목명','이수권장학년','설정학기','시간','학점','필수여부','학사편입생제외여부','개설학과','출력당시개설여부','비고']

def clean(v):return (v or '').replace('\n','').strip()

def extract(path):
    filename=unicodedata.normalize('NFC',path.name)
    match=re.fullmatch(r'(20\d{2})_컴공_(주전공|복수전공)\.pdf',filename)
    if not match:raise ValueError('지원하지 않는 파일명: '+filename)
    year=int(match[1]);track=match[2];digest=hashlib.sha256(path.read_bytes()).hexdigest();doc_id=digest[:24]
    title=f'{year}학년도 컴퓨터공학 교과과정표 ({track})'
    chunks=[];texts=[];category='';group='';group_rule=''
    with pdfplumber.open(path) as pdf:
        first=pdf.pages[0].extract_text() or ''
        if not re.search(str(year)+r'\s*학년도\s*교과과정안내',first) or '컴퓨터공학' not in first or not re.search(r'출력구분\s*:\s*'+track,first):
            raise ValueError('파일명과 PDF 적용 조건 불일치: '+filename)
        chunks.append({'page':1,'rows':[],'text':first.split('영역명')[0],'section':'적용 조건·졸업 총요건'})
        for page_no,page in enumerate(pdf.pages,1):
            text=page.extract_text() or '';texts.append(f'[page {page_no}]\n{text}')
            rows=[]
            for table in page.extract_tables():
                if not any(len(row)==12 and clean(row[2])=='교과목명' for row in table):continue
                for raw in table:
                    if len(raw)!=12:raise ValueError('열 수 확인 필요')
                    row=[clean(v) for v in raw]
                    if row[2]=='교과목명' or not row[1] or '학수번호' in row[1]:continue
                    if row[0]:category=row[0]
                    if not re.fullmatch(r'\*?\d{5}',row[1]):
                        group=row[1];group_rule=row[2]
                    entry=dict(zip(LABELS,row));entry.update(category=category,group=group,group_rule=group_rule)
                    rows.append(entry)
            # 표 외의 본문도 보존. 행의 의미는 열 이름과 상위 이수 조건으로 명시한다.
            if not rows:
                chunks.append({'page':page_no,'rows':[],'text':text,'section':'본문·주석'})
            for start in range(0,len(rows),6):
                block=rows[start:start+6]
                lines=[]
                for row in block:
                    lines.append(' | '.join(f'{key}: {value}' for key,value in row.items() if value))
                chunks.append({'page':page_no,'rows':block,'text':'\n'.join(lines),'section':block[0]['category']+' / '+block[0]['group']})
    # 유레카의 Date는 출력일이다. 시행일·입학연도로 대신 사용하지 않는다.
    now=datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    document={'doc_id':doc_id,'title':title,'text':'\n\n'.join(texts),'source_url':URL,'source_type':'교육과정',
              'source_file':filename,'raw_path':str(path),'sha256':digest,'collected_at':now,
              'admission_year':year,'major_track':track,'printed_at':'2026-10-08' if '2026/10/08' in first else None}
    payloads=[]
    for i,chunk in enumerate(chunks):
        content=f'입학연도: {year}\n적용학과: 컴퓨터공학\n이수구분: {track}\n페이지: {chunk["page"]}\n'+chunk['text']
        payloads.append({'chunk_id':f'{doc_id}_curriculum_{i:04d}','doc_id':doc_id,'title':title,'source_url':URL,
            'source_file':filename,'source_type':'교육과정','text':content,'section':chunk['section'],'page':chunk['page'],
            'course_rows':chunk['rows'],'major_track':track,'applicability':{
                'department':{'status':'specified','values':['컴퓨터공학','컴퓨터공학과','컴퓨터공학전공']},
                'admission_year':{'status':'specified','from':year,'to':year},
                'major_track':{'status':'specified','values':[track]},
                'student_status':{'status':'unknown','values':[]},
                'basis':first.split('영역명')[0]},
            'dates':{'posted_at':None,'effective_from':None,'effective_until':None,'target_term':None},
            'printed_at':document['printed_at'],'collected_at':now,'raw_path':str(path),'related_chunk_ids':[],
            'quality_flags':[],'metadata_review_required':False,'ingestion_status':'ready',
            'extraction_method':'pdfplumber_12_column_table_with_group_context','embedding_input':title+'\n'+content})
    return document,payloads

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--upload',action='store_true');args=ap.parse_args()
    load_dotenv(ROOT/'.env')
    out=ROOT/'backend/data/curriculum_import';out.mkdir(parents=True,exist_ok=True)
    documents=[];chunks=[]
    for path in sorted(Path('/Users/hyun/Downloads').iterdir()):
        if re.fullmatch(r'202[1-6]_컴공_(주전공|복수전공)\.pdf',unicodedata.normalize('NFC',path.name)):
            doc,payloads=extract(path);documents.append(doc);chunks+=payloads
            print(doc['source_file'],len(payloads),'chunks',flush=True)
    if len(documents)!=7:raise ValueError('원본 PDF 7개가 필요합니다.')
    for name,items in [('documents.jsonl',documents),('chunks.jsonl',chunks)]:
        (out/name).write_text(''.join(json.dumps(h,ensure_ascii=False)+'\n' for h in items))
    rows=[r for h in chunks for r in h['course_rows']]
    print('documents',len(documents),'chunks',len(chunks),'course_rows',sum(bool(re.fullmatch(r'\*?\d{5}',r['영역명/학수번호'])) for r in rows),flush=True)
    if not args.upload:return
    model=local_model();point_ids=[]
    with httpx.Client(timeout=60,headers={'api-key':os.environ['QDRANT_API_KEY']}) as client:
        endpoint=os.environ['QDRANT_URL'].rstrip('/')+'/collections/'+os.environ['QDRANT_COLLECTION']
        for start in range(0,len(chunks),8):
            batch=chunks[start:start+8]
            emb=model.encode([h['embedding_input'] for h in batch],max_length=1024,return_dense=True,return_sparse=True,return_colbert_vecs=False)
            points=[]
            for i,h in enumerate(batch):
                pid=str(uuid5(NAMESPACE_URL,'ewha-curriculum:'+h['chunk_id']));point_ids.append(pid)
                weights=emb['lexical_weights'][i]
                points.append({'id':pid,'payload':h,'vector':{'bge_m3_dense':emb['dense_vecs'][i].tolist(),
                    'bge_m3_sparse':{'indices':[int(k) for k in weights],'values':[float(v) for v in weights.values()]}}})
            response=client.put(endpoint+'/points',params={'wait':'true'},json={'points':points});response.raise_for_status()
            print('uploaded',min(start+8,len(chunks)),'/',len(chunks),flush=True)
        # 업로드한 ID만 직접 읽어 payload와 벡터 존재를 검증한다.
        verified=0
        for start in range(0,len(point_ids),64):
            response=client.post(endpoint+'/points',json={'ids':point_ids[start:start+64],'with_payload':True,'with_vector':True});response.raise_for_status()
            points=response.json()['result']
            for p in points:
                assert len(p['vector']['bge_m3_dense'])==1024 and p['payload']['course_rows'] is not None
            verified+=len(points)
        assert verified==len(chunks)
    INDEX_PATH.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(INDEX_PATH) as db:
        for h in chunks:
            db.execute('INSERT OR REPLACE INTO chunks VALUES (?,?)',(h['chunk_id'],json.dumps(h,ensure_ascii=False)))
            numbers=set(re.findall(r'(?<!\d)\d{5}(?!\d)',h['text']))
            db.executemany('INSERT OR IGNORE INTO codes VALUES (?,?)',[(code,h['chunk_id']) for code in numbers])
    (out/'upload_result.json').write_text(json.dumps({'documents':len(documents),'chunks':len(chunks),'verified_points':verified,
        'collection':os.environ['QDRANT_COLLECTION'],'point_ids':point_ids},ensure_ascii=False,indent=2))
    print('verified_and_indexed',verified,flush=True)
if __name__=='__main__':main()

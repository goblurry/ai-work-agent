import json
import sqlite3
from fastapi.testclient import TestClient
from app.main import create_app


def test_web_lifecycle_no_internal_exposure(tmp_path):
    calls=[]
    def process(r):
        calls.append(r['inquiry_id'])
        r.update(status='need_info',missing_fields=['admission_year'],draft='비공개 내부 초안',
                 evidence=[{'text':'내부 검색 결과'}],warnings=['내부 경고'])
        return r
    with TestClient(create_app(tmp_path/'db',processor=process)) as c:
        r=c.post('/students/inquiries',json={'question':'졸업 요건 문의'}).json()
        receipt=r['receipt_no'];public='/students/inquiries/'+receipt
        assert calls==[] and r['status']=='접수 완료'
        staff=c.get('/inquiries').json()[0];url='/inquiries/'+staff['inquiry_id']
        assert staff['channel']=='web'
        assert c.post(public+'/supplement',json={'profile':{'admission_year':2022}}).status_code==409
        c.post(url+'/run')
        p=c.get(public).json()
        assert p['final_answer'] is None
        assert not {'draft','evidence','trace','missing_fields','warnings','unresolved_reason','inquiry_id'} & p.keys()
        c.post(url+'/request-info',json={'message':'입학연도를 알려 주세요.','fields':['admission_year']})
        assert c.get(public).json()['information_request']['fields']==['admission_year']
        assert c.post(url+'/run').status_code==409
        r=c.post(public+'/supplement',json={'profile':{'admission_year':2022}}).json()
        assert r['status']=='접수 완료' and len(calls)==1
        c.post(url+'/run');assert len(calls)==2
        c.post(url+'/review',json={'action':'edit','text':'확정 전 답변'})
        assert c.get(public).json()['final_answer'] is None
        c.post(url+'/review',json={'action':'complete','text':'확정된 안내'})
        assert c.get(public).json()['final_answer']=='확정된 안내'
        assert c.get(public).json()['information_request'] is None
        assert c.post(url+'/run').status_code==409
        assert c.post(public+'/supplement',json={'profile':{}}).status_code==409


def test_phone_and_old_database_migration(tmp_path):
    db=tmp_path/'db'
    old={'inquiry_id':'old','question':'기존 문의','profile':{},'status':'completed','draft':'기존 완료 답변',
         'trace':[],'updated_at':'2026-10-01'}
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE inquiries(id TEXT PRIMARY KEY,body TEXT NOT NULL)')
        conn.execute('INSERT INTO inquiries VALUES (?,?)',('old',json.dumps(old)))
    with TestClient(create_app(db,processor=lambda r:r)) as c:
        saved=c.get('/inquiries/old').json()
        assert saved['final_answer']=='기존 완료 답변' and saved['receipt_no']
        r=c.post('/inquiries',json={'question':'전화 문의'}).json()
        assert r['channel']=='phone' and r['status']=='received'
        assert c.get('/students/inquiries/'+r['receipt_no']).status_code==404
        url='/inquiries/'+r['inquiry_id']
        c.post(url+'/request-info',json={'message':'학과 확인','fields':['department']})
        assert c.get(url).json()['status']=='need_info'
        assert c.post(url+'/continue',json={'profile':{'department':'컴퓨터공학과'}}).json()['status']=='received'
    with TestClient(create_app(db,processor=lambda r:r)) as c:
        assert c.get('/inquiries/old').json()['receipt_no']==saved['receipt_no']

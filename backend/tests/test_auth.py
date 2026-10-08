import json
import sqlite3
import time
from fastapi.testclient import TestClient
from app.main import create_app
from app.auth import COOKIE, token_hash, verify_password


def login(c, role):
    response=c.post('/auth/login',json={'username':role,'password':role+'-test-password'})
    assert response.status_code==200
    assert response.json()['role']==role
    return response


def test_login_session_hash_logout_and_expiry(tmp_path):
    db=tmp_path/'db'
    with TestClient(create_app(db)) as c:
        assert c.get('/auth/me').status_code==401
        assert c.post('/auth/login',json={'username':'student','password':'wrong'}).status_code==401
        assert c.post('/auth/login',json={'username':'unknown','password':'wrong'}).status_code==401
        response=login(c,'student')
        assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=lax' in response.headers['set-cookie']
        token=c.cookies.get(COOKIE)
        assert set(c.get('/auth/me').json())=={'id','username','role'}
        with sqlite3.connect(db) as conn:
            encoded=conn.execute("SELECT password_hash FROM users WHERE username='student'").fetchone()[0]
            assert encoded!='student-test-password' and verify_password('student-test-password',encoded)
            assert conn.execute('SELECT token_hash FROM sessions').fetchone()[0]==token_hash(token)
        assert c.post('/auth/logout').status_code==200
        assert c.get('/auth/me').status_code==401
        c.cookies.set(COOKIE,token)
        assert c.get('/auth/me').status_code==401
        c.cookies.clear();login(c,'student')
        with sqlite3.connect(db) as conn:conn.execute('UPDATE sessions SET expires_at=?',(time.time()-1,))
        assert c.get('/auth/me').status_code==401


def test_roles_ownership_and_final_reply_flow(tmp_path):
    def process(r):
        r.update(status='needs_review',draft='직원용 비공개 초안',evidence=[{'chunk_id':'c1','text':'근거'}])
        return r
    app=create_app(tmp_path/'db',processor=process,reply_writer=lambda r,d:'검토할 안내문')
    with TestClient(app) as c:
        for path in ['/inquiries','/students/inquiries','/inquiries/x','/materials/courses/20481']:
            assert c.get(path).status_code==401
        assert c.post('/students/inquiries',json={'question':'문의'}).status_code==401
        login(c,'student')
        me=c.get('/auth/me').json()
        public=c.post('/students/inquiries',json={'question':'졸업 문의'}).json()
        receipt=public['receipt_no'];public_url='/students/inquiries/'+receipt
        assert len(c.get('/students/inquiries').json())==1
        assert c.post('/students/inquiries',json={'question':'위조','student_id':'other'}).status_code==422
        assert c.get('/inquiries').status_code==403
        assert c.post('/inquiries/x/run').status_code==403
        other_id=app.state.auth.create_user('student2','second-test-password','student')
        c.post('/auth/login',json={'username':'student2','password':'second-test-password'})
        assert c.get('/students/inquiries').json()==[]
        assert c.get(public_url).status_code==404
        assert c.post(public_url+'/supplement',json={'profile':{'admission_year':2022}}).status_code==404
        login(c,'staff')
        assert c.get('/students/inquiries').status_code==403
        assert c.post('/students/inquiries',json={'question':'직원 학생접수 시도'}).status_code==403
        item=c.get('/inquiries').json()[0]
        assert item['student_id']==me['id'] and item['student_id']!=other_id
        url='/inquiries/'+item['inquiry_id']
        c.post(url+'/run')
        c.post(url+'/review',json={'action':'edit','text':'수정한 내부 초안'})
        login(c,'student')
        assert c.get(public_url).json()['final_answer'] is None
        assert not {'student_id','draft','evidence','trace','inquiry_id'} & c.get(public_url).json().keys()
        login(c,'staff')
        assert c.post(url+'/compose',json={'text':'안내 방향'}).status_code==200
        assert c.post(url+'/review',json={'action':'complete','text':'확정된 학생 답변'}).status_code==200
        phone=c.post('/inquiries',json={'question':'전화 문의'}).json()
        assert phone['student_id'] is None
        login(c,'student')
        assert c.get(public_url).json()['final_answer']=='확정된 학생 답변'
        assert len(c.get('/students/inquiries').json())==1
        assert c.get('/students/inquiries/'+phone['receipt_no']).status_code==404
        for suffix in ['run','compose','review','continue','request-info']:
            assert c.post(url+'/'+suffix,json={}).status_code==403


def test_restart_preserves_accounts_sessions_and_legacy_inquiries(tmp_path):
    db=tmp_path/'db'
    old={'inquiry_id':'old','question':'기존 문의','profile':{},'channel':'web','receipt_no':'old-receipt','status':'completed','draft':'예전 답변','trace':[],'updated_at':'2026-10-01'}
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE inquiries(id TEXT PRIMARY KEY,body TEXT NOT NULL)')
        conn.execute('INSERT INTO inquiries VALUES (?,?)',('old',json.dumps(old)))
    with TestClient(create_app(db)) as c:
        login(c,'staff');session=c.cookies.get(COOKIE);uid=c.get('/auth/me').json()['id']
        assert c.get('/inquiries/old').json()['student_id'] is None
    with TestClient(create_app(db)) as c:
        c.cookies.set(COOKIE,session)
        assert c.get('/auth/me').json()['id']==uid
        assert len(c.get('/inquiries').json())==1
        login(c,'student')
        assert c.get('/students/inquiries').json()==[]
        assert c.get('/students/inquiries/old-receipt').status_code==404
        with sqlite3.connect(db) as conn:assert conn.execute('SELECT count(*) FROM users').fetchone()[0]==2


def test_csrf_origin_and_credentialed_cors(tmp_path):
    with TestClient(create_app(tmp_path/'db')) as c:
        body={'username':'student','password':'student-test-password'}
        assert c.post('/auth/login',json=body,headers={'origin':'https://untrusted.example'}).status_code==403
        response=c.post('/auth/login',json=body,headers={'origin':'http://127.0.0.1:5173'})
        assert response.status_code==200
        assert response.headers['access-control-allow-credentials']=='true'
        assert c.post('/auth/logout',headers={'origin':'https://untrusted.example'}).status_code==403
        assert c.get('/auth/me').status_code==200

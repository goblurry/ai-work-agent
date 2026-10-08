"""TEST_DATABASE_URL의 별도 PostgreSQL DB에서 실제 API 저장·권한·재시작 검증."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import create_app


def test_postgres_inquiry_and_session_persistence(monkeypatch):
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('별도 PostgreSQL 테스트 DB가 설정되지 않음')
    monkeypatch.setenv('DATABASE_URL', url)
    def process(r):
        r.update(status='needs_review',draft='내부 초안',evidence=[{'chunk_id':'c1','text':'근거'}])
        return r
    def login(c, role):
        assert c.post('/auth/login',json={'username':role,'password':role+'-test-password'}).status_code==200
    with TestClient(create_app(processor=process, reply_writer=lambda r,d:'초안')) as c:
        login(c,'student')
        res=c.post('/students/inquiries',json={'question':'PostgreSQL 테스트'})
        assert res.status_code==201
        receipt=res.json()['receipt_no']
        assert any(x['receipt_no']==receipt for x in c.get('/students/inquiries').json())
        assert c.get('/inquiries').status_code==403
        login(c,'staff')
        record=next(x for x in c.get('/inquiries').json() if x['receipt_no']==receipt)
        path='/inquiries/'+record['inquiry_id']
        assert c.post(path+'/run').status_code==200
        assert c.post(path+'/compose',json={'text':'담당자 판단'}).json()['draft']=='초안'
        assert c.post(path+'/review',json={'action':'complete','text':'확정 답변'}).status_code==200
        login(c,'student')
        token=c.cookies.get('academic_session')
    with TestClient(create_app()) as c:
        c.cookies.set('academic_session',token)
        assert c.get('/auth/me').status_code==200
        response=c.get('/students/inquiries/'+receipt).json()
        assert response['final_answer']=='확정 답변'
        assert 'draft' not in response and 'evidence' not in response
        assert c.post('/auth/logout').status_code==200
        assert c.get('/auth/me').status_code==401

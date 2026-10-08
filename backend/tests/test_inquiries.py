from fastapi.testclient import TestClient
from app.main import create_app


def test_save_resume_complete_and_persist(tmp_path):
    db = tmp_path / 'inquiries.sqlite3'
    with TestClient(create_app(db, processor=lambda record: record)) as client:
        response = client.post('/inquiries', json={'question':'복수전공 신청 문의', 'profile':{'department':'컴퓨터공학'}})
        assert response.status_code == 201
        record = response.json()
        assert record['draft'] is None and record['evidence'] == []
        url = '/inquiries/' + record['inquiry_id']
        updated = client.post(url+'/continue',json={'profile':{'admission_year':2021}}).json()
        assert updated['profile']['department'] == '컴퓨터공학'
        assert updated['profile']['admission_year'] == 2021
        assert client.post(url+'/review',json={'action':'complete','text':'담당자 확인 안내'}).json()['status'] == 'completed'
        assert client.post(url+'/continue',json={'profile':{}}).status_code == 409
    with TestClient(create_app(db, processor=lambda record: record)) as client:
        assert client.get(url).json()['draft'] == '담당자 확인 안내'


def test_invalid_requests_and_missing_record(tmp_path):
    with TestClient(create_app(tmp_path/'test.sqlite3', processor=lambda record: record)) as client:
        assert client.post('/inquiries',json={'question':'   '}).status_code == 422
        assert client.get('/inquiries/not-found').status_code == 404
        assert client.post('/inquiries',json={'question':'문의','profile':{'admission_year':5}}).status_code == 422

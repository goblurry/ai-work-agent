import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi.testclient import TestClient
from app.main import create_app


def login(client, name='student'):
    password = 'second-test-password' if name == 'student2' else name+'-test-password'
    assert client.post('/auth/login', json={'username':name,'password':password}).status_code == 200


def paths(client):
    login(client)
    public = client.post('/students/inquiries', json={'question':'원래 문의','profile':{'department':'컴퓨터공학과'}}).json()
    login(client, 'staff')
    item = client.get('/inquiries').json()[0]
    return '/students/inquiries/'+public['receipt_no'], '/inquiries/'+item['inquiry_id'], item


def test_owner_edit_resets_evidence_and_preserves_identity(tmp_path):
    def process(record):
        record.update(status='needs_review',draft='오래된 초안',draft_kind='student_reply',staff_decision='이전 판단',
                      course_lookup={'codes':['20481']},evidence=[{'text':'이전 근거'}],support_summary={'old':True})
        return record
    with TestClient(create_app(tmp_path/'db',processor=process)) as client:
        public, staff, original = paths(client)
        assert client.post(staff+'/run').status_code == 200
        login(client)
        response = client.put(public, json={'question':'수정된 문의','inquiry_type':'course_recognition',
                              'details':{'required_course_code':'20481'},'profile':{'admission_year':2022}})
        assert response.status_code == 200 and response.json()['can_manage']
        assert response.json()['final_answer'] is None and 'evidence' not in response.json()
        login(client,'staff')
        saved = client.get(staff).json()
        assert saved['status'] == 'received' and saved['question'] == '수정된 문의'
        for key in ['inquiry_id','receipt_no','student_id','channel','created_at']:
            assert saved[key] == original[key]
        assert saved['evidence'] == []
        for key in ['draft','support_summary','staff_decision','course_lookup']:
            assert saved[key] is None
        assert saved['trace'][-1]['step'] == '문의수정'
        assert client.post(staff+'/compose',json={'text':'판단'}).status_code == 409


def test_ownership_roles_and_validation(tmp_path):
    with TestClient(create_app(tmp_path/'db')) as client:
        public, staff, _ = paths(client)
        client.app.state.auth.create_user('student2','second-test-password','student')
        login(client,'student2')
        assert client.put(public,json={'question':'다른 학생 변경'}).status_code == 404
        assert client.delete(public).status_code == 404
        assert client.delete(staff).status_code == 403
        login(client)
        for invalid in [{'question':' '},{'question':'문의','student_id':'위조'},
                        {'question':'문의','inquiry_type':'other','details':{'required_course_code':'20481'}}]:
            assert client.put(public,json=invalid).status_code == 422
        client.post('/auth/logout')
        assert client.delete(public).status_code == 401


def test_soft_delete_hides_both_lists_and_cannot_be_reopened(tmp_path):
    db = tmp_path/'db'
    with TestClient(create_app(db)) as client:
        public, staff, original = paths(client)
        login(client)
        assert client.delete(public).json() == {'deleted':True}
        assert client.get('/students/inquiries').json() == []
        assert client.get(public).status_code == 404
        assert client.put(public,json={'question':'복원 시도'}).status_code == 404
        login(client,'staff')
        assert client.get('/inquiries').json() == []
        assert client.get(staff).status_code == 404
        assert client.post(staff+'/run').status_code == 404
        with sqlite3.connect(db) as conn:
            body = json.loads(conn.execute('SELECT body FROM inquiries WHERE id=?',(original['inquiry_id'],)).fetchone()[0])
            assert body['status'] == 'deleted' and body['deleted_at']


def test_staff_management_and_completed_lock(tmp_path):
    with TestClient(create_app(tmp_path/'db')) as client:
        _, staff, _ = paths(client)
        assert client.put(staff,json={'question':'담당자 수정'}).status_code == 200
        assert client.post(staff+'/review',json={'action':'complete','text':'완료 답변'}).status_code == 200
        assert client.put(staff,json={'question':'완료 후 변경'}).status_code == 409
        assert client.delete(staff).status_code == 409
        login(client)
        item = client.get('/students/inquiries').json()[0]
        assert not item['can_manage']
        assert client.delete('/students/inquiries/'+item['receipt_no']).status_code == 409
        login(client,'staff')
        phone = client.post('/inquiries',json={'question':'전화 문의'}).json()
        assert client.delete('/inquiries/'+phone['inquiry_id']).status_code == 200
        assert len(client.get('/inquiries').json()) == 1


def test_running_agent_blocks_student_and_staff_changes(tmp_path):
    entered, release = Event(), Event()
    def process(record):
        entered.set()
        assert release.wait(10)
        record.update(status='needs_review')
        return record
    app = create_app(tmp_path/'db',processor=process)
    with TestClient(app) as runner, TestClient(app) as editor:
        public, staff, _ = paths(runner)
        with ThreadPoolExecutor() as pool:
            future = pool.submit(runner.post,staff+'/run')
            assert entered.wait(5)
            try:
                login(editor)
                assert not editor.get(public).json()['can_manage']
                assert editor.put(public,json={'question':'실행 중 수정'}).status_code == 409
                assert editor.delete(public).status_code == 409
                login(editor,'staff')
                assert editor.put(staff,json={'question':'실행 중 수정'}).status_code == 409
                assert editor.delete(staff).status_code == 409
            finally:
                release.set()
            assert future.result().status_code == 200


def test_cors_allows_new_methods(tmp_path):
    with TestClient(create_app(tmp_path/'db')) as client:
        for method in ['PUT','DELETE']:
            response = client.options('/students/inquiries/id',headers={
                'Origin':'http://localhost:5173','Access-Control-Request-Method':method,
                'Access-Control-Request-Headers':'content-type'})
            assert response.status_code == 200


def test_edit_during_reply_generation_does_not_restore_old_question(tmp_path):
    entered, release = Event(), Event()
    def process(record):
        record.update(status='needs_review',evidence=[{'text':'확인 근거'}])
        return record
    def writer(record, decision):
        entered.set()
        assert release.wait(10)
        return '수정 전 문의의 초안'
    app = create_app(tmp_path/'db',processor=process,reply_writer=writer)
    with TestClient(app) as runner, TestClient(app) as editor:
        public, staff, _ = paths(runner)
        assert runner.post(staff+'/run').status_code == 200
        with ThreadPoolExecutor() as pool:
            future = pool.submit(runner.post,staff+'/compose',json={'text':'담당자 판단'})
            assert entered.wait(5)
            try:
                login(editor)
                assert editor.put(public,json={'question':'변경된 질문'}).status_code == 200
            finally:
                release.set()
            assert future.result().status_code == 409
        saved = runner.get(staff).json()
        assert saved['question'] == '변경된 질문' and saved['draft'] is None

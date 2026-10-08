from fastapi.testclient import TestClient
from app.main import create_app
from app.intake import processing_record
from app import agent


def test_conditional_intake_and_run_update(tmp_path):
    seen=[]
    def process(record):
        seen.append(record.copy())
        record.update(status='needs_review')
        return record
    with TestClient(create_app(tmp_path/'db',processor=process)) as c:
        body={'question':'이 과목으로 인정되나요?', 'inquiry_type':'course_recognition',
              'profile':{'department':'통계학과','target_department':'컴퓨터공학과','admission_year':2022,'major_track':'복수전공'},
              'details':{'required_course_code':'20481','completed_course_code':'39144'}}
        r=c.post('/students/inquiries',json=body)
        assert r.status_code==201
        assert r.json()['details']['required_course_code']=='20481'
        staff=c.get('/inquiries').json()[0];url='/inquiries/'+staff['inquiry_id']
        response=c.post(url+'/run',json={'profile':{'major_track':'주전공'},'details':{'completed_course_code':None}})
        assert response.status_code==200
        result=response.json()
        assert result['details']['required_course_code']=='20481' and result['details']['completed_course_code'] is None
        assert result['profile']['department']=='통계학과' and result['profile']['target_department']=='컴퓨터공학과'
        assert seen[-1]['profile']['major_track']=='주전공'
        assert c.post(url+'/run').status_code==200
        assert c.post('/students/inquiries',json={**body,'inquiry_type':'leave_return'}).status_code==422
        assert c.post('/students/inquiries',json={**body,'details':{'required_course_code':'123'}}).status_code==422
        change=c.post(url+'/run',json={'inquiry_type':'leave_return','details':{'procedure':'leave','application_status':'saved','application_date':'2026-09-30'}})
        assert change.status_code==200
        assert '20481' not in str(change.json()['details'])
        assert change.json()['details']['application_date']=='2026-09-30'


def test_form_conditions_drive_lookup_without_changing_student_input(monkeypatch):
    seen=[]
    hit={'chunk_id':'c1','doc_id':'d1','source_type':'교육과정','title':'2022 컴퓨터공학 교과과정',
         'major_track':'복수전공','text':'20481 자료구조','course_rows':[{'영역명/학수번호':'20481','교과목명':'자료구조','학점':'3','group':'전공필수'}],
         'applicability':{'department':{'status':'specified','values':['컴퓨터공학과']},'admission_year':{'status':'specified','from':2022,'to':2022}}}
    def lookup(codes,dept,year,**kwargs):
        seen.append((codes,dept,year,kwargs))
        return {'available':True,'evidence':[hit],'matches':{}}
    monkeypatch.setattr(agent,'lookup_courses',lookup)
    r={'question':'인정되나요?', 'inquiry_type':'course_recognition', 'profile':{'department':'통계학과','target_department':'컴퓨터공학과','admission_year':2022,'major_track':'복수전공'},
       'details':{'required_course_code':'20481','completed_course_code':'39144'},'trace':[]}
    result=agent.run_agent(r)
    assert seen[0][:3]==(['20481','39144'],'컴퓨터공학과',2022)
    assert result['question']=='인정되나요?' and result['profile']['department']=='통계학과'
    assert result['support_summary']['confirmed_courses'][0]['course_code']=='20481'
    assert not result['missing_fields']


def test_leave_context_preserves_application_and_receipt_distinction():
    r={'question':'반환 기준 문의','inquiry_type':'leave_return','profile':{},
       'details':{'procedure':'leave','application_status':'submitted','application_date':'2026-09-30','receipt_date':None}}
    prepared=processing_record(r)
    assert '신청일(학생 입력): 2026-09-30' in prepared['question']
    assert '접수완료 여부 미확인' in prepared['question'] and '실제 접수일(학생 입력)' not in prepared['question']
    assert r['question']=='반환 기준 문의'


def test_staff_schema_has_six_main_operations(tmp_path):
    with TestClient(create_app(tmp_path/'db')) as c:
        spec=c.get('/openapi.json').json()
        count=sum('담당자' in operation.get('tags',[]) for path in spec['paths'].values() for operation in path.values())
        assert count==6
        assert '/inquiries/{inquiry_id}/continue' not in spec['paths']

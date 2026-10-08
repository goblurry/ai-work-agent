from fastapi.testclient import TestClient
from app.main import create_app
from app.llm import LLMServiceError


def process(r):
    r.update(status='needs_review',draft='담당자용 근거 요약',
             support_summary={'staff_question':{'text':'이수요건을 충족할 수 있나요?'},'confirmed_courses':[{'course_code':'20481','course_name':'자료구조','credits':'3'}]},
             evidence=[{'chunk_id':'c1','text':'20481 자료구조 3학점 전공필수'}])
    return r


def test_compose_is_internal_draft_until_staff_confirms(tmp_path):
    calls=[]
    def local_writer(record,decision):
        calls.append((record['evidence'],decision))
        return '문의하신 과목으로는 지정 필수과목의 이수를 인정하기 어렵습니다.'
    with TestClient(create_app(tmp_path/'db',processor=process,reply_writer=local_writer)) as c:
        r=c.post('/students/inquiries',json={'question':'가상 시연 문의'}).json()
        staff=c.get('/inquiries').json()[0];url='/inquiries/'+staff['inquiry_id']
        assert c.post(url+'/compose',json={'text':'안됩니다'}).status_code==409
        c.post(url+'/run')
        response=c.post(url+'/compose',json={'text':'안됩니다'});assert response.status_code==200
        draft=response.json()
        assert draft['staff_decision']=='안됩니다' and draft['draft']!='안됩니다'
        assert draft['draft_kind']=='student_reply' and draft['final_answer'] is None
        assert calls[0][0][0]['chunk_id']=='c1'
        public='/students/inquiries/'+r['receipt_no']
        assert c.get(public).json()['final_answer'] is None
        c.post(url+'/review',json={'action':'complete','text':draft['draft']})
        assert c.get(public).json()['final_answer']==draft['draft']
        assert c.post(url+'/compose',json={'text':'수정'}).status_code==409


def test_unconnected_or_failed_writer_keeps_existing_draft(tmp_path):
    for name,writer in [('unconnected',None),('failure',lambda *args: (_ for _ in ()).throw(LLMServiceError('테스트 실패')))]:
        with TestClient(create_app(tmp_path/name,processor=process,reply_writer=writer)) as c:
            r=c.post('/inquiries',json={'question':'가상 시연 문의'}).json();url='/inquiries/'+r['inquiry_id']
            c.post(url+'/run')
            assert c.post(url+'/compose',json={'text':'안됩니다'}).status_code==503
            saved=c.get(url).json()
            assert saved['draft']=='담당자용 근거 요약' and saved['final_answer'] is None


def test_choices_and_optional_memo(tmp_path):
    calls=[]
    def writer(record, decision):
        calls.append(decision)
        return '검토할 학생 안내문'
    with TestClient(create_app(tmp_path/'choices',processor=process,reply_writer=writer)) as c:
        r=c.post('/inquiries',json={'question':'가상 문의'}).json();url='/inquiries/'+r['inquiry_id']
        c.post(url+'/run')
        for choice,label in [('yes','예'),('no','아니요'),('check','추가 확인 필요')]:
            result=c.post(url+'/compose',json={'choice':choice,'memo':'담당자 확인 기준'}).json()
            assert result['staff_choice']==choice and result['staff_memo']=='담당자 확인 기준'
            assert label in calls[-1] and result['final_answer'] is None
        assert c.post(url+'/compose',json={}).status_code==422
        assert c.post(url+'/compose',json={'choice':'no','text':'예'}).status_code==422

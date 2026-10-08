from copy import deepcopy
from app import agent
from app.main import create_app
from fastapi.testclient import TestClient


def record():
    return {'question':'복학 신청 절차 문의','profile':{},'trace':[], 'target_term':None,'as_of':None}


def evidence():
    return {'chunk_id':'c1','text':'복학은 신청 기간에 온라인 신청합니다.','source_type':'안내',
            'applicability':{f:{'status':'all'} for f in ('department','admission_year','student_status')},
            'dates':{},'source_url':'https://example.edu/rules'}


def decision(action, **kwargs):
    return {'action':action,'reason':'다음 처리','query':'','missing_fields':[],'evidence_ids':[],**kwargs}


def test_retry_observe_then_draft(monkeypatch):
    decisions=iter([decision('search',query='복학'),decision('search',query='복학 온라인 신청 절차'),
                    decision('draft',evidence_ids=['c1'])])
    calls=[]
    monkeypatch.setattr(agent,'decide_action',lambda *args: next(decisions))
    def search(q, **kwargs):
        calls.append(q)
        return [] if len(calls)==1 else [evidence()]
    monkeypatch.setattr(agent,'search',search)
    monkeypatch.setattr(agent,'generate_draft',lambda *args: '온라인 신청합니다. [c1]')
    result=agent.run_agent(record())
    assert len(calls)==2 and result['status']=='draft_ready'
    assert len([t for t in result['trace'] if t['step']=='자료검색'])==2


def test_unknown_scope_never_ready(monkeypatch):
    hit=evidence();hit['applicability']['admission_year']={'status':'unknown'}
    decisions=iter([decision('search',query='복학'),decision('draft',evidence_ids=['c1'])])
    monkeypatch.setattr(agent,'decide_action',lambda *args:next(decisions))
    monkeypatch.setattr(agent,'search',lambda *args, **kwargs:[hit])
    monkeypatch.setattr(agent,'generate_draft',lambda *args:'기간 내 신청합니다. [c1]')
    result=agent.run_agent(record())
    assert result['status']=='needs_review' and result['warnings']
    assert result['draft'] is not None


def test_scope_mismatch_excluded_and_missing_requested():
    hit=evidence();hit['applicability']['admission_year']={'status':'specified','from':2020,'to':2022}
    r=record()
    assert agent.assess(hit,r)['missing_fields']==['admission_year']
    r['profile']['admission_year']=2025
    assert agent.assess(hit,r)['excluded']


def test_stop_repeated_search_and_bad_citation(monkeypatch):
    monkeypatch.setattr(agent,'decide_action',lambda *args:decision('search',query='복학'))
    monkeypatch.setattr(agent,'search',lambda *args, **kwargs:[])
    assert agent.run_agent(record())['status']=='needs_review'
    choices=iter([decision('search',query='복학'),decision('draft',evidence_ids=['c1'])])
    monkeypatch.setattr(agent,'decide_action',lambda *args:next(choices))
    monkeypatch.setattr(agent,'search',lambda *args, **kwargs:[evidence()])
    monkeypatch.setattr(agent,'generate_draft',lambda *args:'근거가 틀린 초안 [invented]')
    result=agent.run_agent(record())
    assert result['draft'] is None and '인용' in result['unresolved_reason']


def test_api_resume_retains_id_history_and_term(tmp_path):
    seen=[]
    def process(r):
        seen.append(deepcopy(r))
        r['status']='need_info' if not r['profile'].get('admission_year') else 'draft_ready'
        r['trace'].append({'step':'테스트실행','detail':'재개 확인'})
        return r
    with TestClient(create_app(tmp_path/'db.sqlite3',processor=process)) as client:
        r=client.post('/inquiries',json={'question':'졸업 문의'}).json()
        url='/inquiries/'+r['inquiry_id']
        client.post(url+'/continue',json={'profile':{'admission_year':2022},'target_term':'2026-2'})
        client.post(url+'/run')
        resumed=client.post(url+'/run').json()
        assert resumed['inquiry_id']==r['inquiry_id'] and resumed['status']=='draft_ready'
        assert len(seen)==2 and seen[-1]['target_term']=='2026-2'
        assert len(resumed['trace'])>len(r['trace'])
        spec=client.get('/openapi.json').json()
        assert '/api/inquiries' not in spec['paths']
        assert spec['paths']['/inquiries']['post']['summary']=='담당자 · 전화 문의 등록'


def test_citations_titles_grouped_and_invented():
    a='851b638aada959a970d749ee_0004_fbf107b7fd_h20_0000'
    b='abb8ff0a6e5c7dd4d8df3042_0012_a3a873b867_h20_0000'
    fake='111111111111111111111111_0000_fake_h20_0000'
    assert agent.valid_citations('[학부] 안내입니다. ['+a+']',{a,b})
    assert agent.valid_citations('두 자료를 확인합니다. ['+a+', '+b+']',{a,b})
    assert not agent.valid_citations('없는 근거 ['+a+', '+fake+']',{a,b})
    assert not agent.valid_citations('[처리 순서] 근거 인용 없음',{a,b})
    assert not agent.valid_citations('일부만 일치 [c1, invented]',{'c1'})

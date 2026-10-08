import json
import sqlite3
from app.courses import lookup_courses,course_codes
from app import agent


def test_exact_code_index_not_substring(tmp_path):
    db=tmp_path/'index'
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE chunks(chunk_id TEXT PRIMARY KEY,body TEXT)')
        c.execute('CREATE TABLE codes(code TEXT,chunk_id TEXT)')
        for code,name in [('20481','자료구조'),('39144','자료구조')]:
            body={'chunk_id':code,'title':'교육과정','text':code+' '+name,'source_url':'https://example.edu'}
            c.execute('INSERT INTO chunks VALUES (?,?)',(code,json.dumps(body)))
            c.execute('INSERT INTO codes VALUES (?,?)',(code,code))
    r=lookup_courses(['20481','39144','20480'],path=db)
    assert r['missing_codes']==['20480']
    assert {h['matched_course_codes'][0] for h in r['evidence']}=={'20481','39144'}
    assert course_codes('학수번호 20481과 39144, 2022학번')==['20481','39144']
    assert course_codes('2026년 2학기 문의')==[]


def test_other_department_curriculum_not_student_requirement():
    r={'question':'학수번호 20481을 이수했습니다.','profile':{'department':'컴퓨터공학과','admission_year':2022}}
    h={'title':'2022학년도 교과과정안내_주전공_지리교육전공.pdf','text':'개설학과 컴퓨터공학','dates':{}}
    assert any('다른 학과' in reason for reason in agent.assess(h,r)['excluded'])
    h['retrieval_method']='course_code_exact'
    assert any('다른 학과' in reason for reason in agent.assess(h,r)['excluded'])


def test_course_search_fallback_preserves_ids_and_handoff(monkeypatch):
    r={'question':'학수번호 20481과 39144 대체 인정 문의','profile':{'department':'컴퓨터공학과','admission_year':2022},'trace':[]}
    monkeypatch.setattr(agent,'lookup_courses',lambda *args, **kwargs:{'available':True,'matches':{'20481':{'chunk_count':1},'39144':{'chunk_count':1}},'missing_codes':[],'evidence':[]})
    monkeypatch.setattr(agent,'decide_action',lambda *args:{'action':'search','reason':'규정 찾기','query':'','missing_fields':[],'evidence_ids':[]})
    queries=[]
    monkeypatch.setattr(agent,'search',lambda q, **kwargs:queries.append(q) or [])
    result=agent.run_agent(r)
    assert len(queries)==3 and len(set(queries))==3
    assert '20481' in queries[0] and '39144' in queries[0]
    assert result['status']=='needs_review'
    assert result['draft'] and result['support_summary']['confirmed_courses']==[]
    assert any('동일·대체' in item for item in result['support_summary']['unverified_items'])
    assert '3회 검색' in result['unresolved_reason']

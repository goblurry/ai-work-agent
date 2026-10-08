from app import agent
from app.course_support import relevant_course_evidence


def course_hit():
    return {'chunk_id':'course_c1','doc_id':'course_doc','title':'2022학년도 컴퓨터공학 교과과정표 (주전공)',
            'source_type':'교육과정','source_file':'2022_컴공_주전공.pdf','page':7,'text':'학수번호20481 자료구조 전공필수',
            'major_track':'주전공','matched_course_codes':['20481'],
            'course_rows':[{'영역명/학수번호':'20481','교과목명':'자료구조','학점':'3','category':'전공',
                            'group':'-전공필수','필수여부':'Y','개설학과':'컴퓨터공학'}],
            'applicability':{'department':{'status':'specified','values':['컴퓨터공학']},
                             'admission_year':{'status':'specified','from':2022,'to':2022},
                             'major_track':{'status':'specified','values':['주전공']}},'dates':{}}


def test_partial_facts_return_without_llm_or_equivalence_rule(monkeypatch):
    h=course_hit()
    monkeypatch.setattr(agent,'lookup_courses',lambda *args,**kw:{'available':True,'evidence':[h],
        'matches':{'20481':{'examples':[]},'39144':{'examples':[]}}})
    def unexpected(*args):raise AssertionError('확보한 과목 정보에 추가 LLM 검색이 필요 없음')
    monkeypatch.setattr(agent,'decide_action',unexpected)
    monkeypatch.setattr(agent,'generate_draft',unexpected)
    r={'question':'학수번호 20481과 39144 이수 인정 문의','profile':{'department':'컴퓨터공학과','admission_year':2022,'major_track':'주전공'},'trace':[]}
    result=agent.run_agent(r)
    assert result['status']=='needs_review' and result['draft']
    assert result['support_summary']['confirmed_courses'][0]['course_code']=='20481'
    assert any('39144' in item for item in result['support_summary']['unverified_items'])
    assert '대체 가능·불가능' in result['draft'] and result.get('final_answer') is None
    assert not result['unresolved_reason']
    q=result['support_summary']['staff_question']
    assert '20481' in q['text'] and '39144' in q['text']
    assert q['options']==['yes','no','check']


def test_irrelevant_notices_rejected_but_recognition_notice_allowed():
    for title in ['2026 폐강 교과목','교과목 증원 안내','추가분반 개설 안내']:
        assert not relevant_course_evidence({'title':title,'source_type':'공지'})
    assert relevant_course_evidence({'title':'동일교과목 및 재수강 인정 안내','source_type':'공지'})

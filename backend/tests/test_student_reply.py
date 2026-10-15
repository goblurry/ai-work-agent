from app import llm


def test_document_facts_are_separate_from_staff_judgment(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    sent=[]
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self,url,**kwargs):
            sent.append(kwargs['json'])
            return self
        def raise_for_status(self): pass
        def json(self):
            return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'해당 과목은 대체 인정되지 않습니다.'}]}]}
    monkeypatch.setattr(llm.httpx,'Client',Client)
    r={'question':'가상 문의','receipt_no':'private-id','profile':{'admission_year':2022},'support_summary':{'confirmed_courses':[
        {'course_code':'20481','course_name':'자료구조','credits':'3','requirement_group':'-전공필수','source_file':'교과과정.pdf','page':7}]},'evidence':[{'title':'교과과정','text':'20481은 공과대학 지정 필수과목이며, 39144는 인공지능대학 개설 과목이다.'}], 'details':{'required_course_code':'20481','completed_course_code':'39144'}}
    answer=llm.generate_student_reply(r,'아니요. 개설 단과대학이 달라 인정되지 않으므로 20481을 재수강해야 합니다.')
    facts,judgment=answer.split('\n\n')
    assert facts=='2022학년도 교육과정 기준으로 자료구조(20481) 과목은 전공필수 3학점입니다.'
    assert judgment.startswith('해당 과목은') and '교과과정.pdf' not in answer
    assert 'private-id' not in sent[0]['input'] and sent[0]['store'] is False

    import json
    context=json.loads(sent[0]['input'])
    assert context['evidence'][0]['text'].startswith('20481은 공과대학')
    assert context['student_conditions']['admission_year']==2022
    assert context['inquiry_details']['completed_course_code']=='39144'
    assert '개설 단과대학이 달라' in context['staff_decision']
    assert '1~2문장' not in sent[0]['instructions']
    assert '그 이유를 빠짐없이' in sent[0]['instructions']

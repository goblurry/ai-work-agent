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
            return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'담당자 확인에 따르면 해당 과목은 대체 인정되지 않습니다.'}]}]}
    monkeypatch.setattr(llm.httpx,'Client',Client)
    r={'question':'가상 문의','receipt_no':'private-id','support_summary':{'confirmed_courses':[
        {'course_code':'20481','course_name':'자료구조','credits':'3','requirement_group':'전공필수','source_file':'교과과정.pdf','page':7}]},'evidence':[]}
    answer=llm.generate_student_reply(r,'아니요')
    facts,judgment=answer.split('\n\n')
    assert '전공필수' in facts and '교과과정.pdf 7쪽' in facts
    assert judgment.startswith('담당자 확인에 따르면') and '교과과정.pdf' not in judgment
    assert 'private-id' not in sent[0]['input'] and sent[0]['store'] is False

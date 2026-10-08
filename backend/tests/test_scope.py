from app.scope import scope_exclusions, qdrant_scope_filter
from app.courses import lookup_courses
import json
import sqlite3


def test_scope_does_not_use_department_mentioned_in_body():
    h={'title':'2022 교과과정안내_통계.pdf','source_type':'교육과정',
       'text':'20481 자료구조 컴퓨터공학과', 'retrieval_method':'course_code_exact'}
    assert scope_exclusions(h,'컴퓨터공학과',2022)
    common={'title':'타전공 교과목 인정 규정','source_type':'규정'}
    assert not scope_exclusions(common,'컴퓨터공학과',2022)


def test_owner_alias_year_and_unknown_curriculum():
    h={'title':'2022 교과과정안내_컴퓨터공학.pdf','source_type':'교육과정'}
    assert not scope_exclusions(h,'컴퓨터공학과',2022)
    assert scope_exclusions(h,'컴퓨터공학전공',2021)
    assert scope_exclusions({'title':'교육과정','source_type':'교육과정'},'컴퓨터공학과',2022)
    h['applicability']={'department':{'status':'specified','values':['컴퓨터공학전공']}}
    assert not scope_exclusions(h,'컴퓨터공학과',2022)


def test_exact_search_filters_before_selecting_top_examples(tmp_path):
    db=tmp_path/'index'
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE chunks(chunk_id TEXT PRIMARY KEY,body TEXT)')
        c.execute('CREATE TABLE codes(code TEXT,chunk_id TEXT)')
        for i,title in enumerate(['2022 교과과정안내_통계.pdf','2021 교과과정안내_컴퓨터공학.pdf',
                                  '2022 교과과정안내_컴퓨터공학.pdf','학칙']):
            h={'chunk_id':str(i),'title':title,'source_type':'규정' if title=='학칙' else '교육과정',
               'text':'20481 자료구조','source_url':'https://example.edu'}
            c.execute('INSERT INTO chunks VALUES (?,?)',(str(i),json.dumps(h)))
            c.execute('INSERT INTO codes VALUES (?,?)',('20481',str(i)))
    result=lookup_courses(['20481'],'컴퓨터공학과',2022,path=db)
    assert {h['title'] for h in result['evidence']}=={'2022 교과과정안내_컴퓨터공학.pdf','학칙'}
    assert result['matches']['20481']['chunk_count']==2


def test_qdrant_filter_excludes_only_explicit_mismatches():
    f=qdrant_scope_filter('컴퓨터공학과',2022)
    assert len(f['must_not'])==3
    assert '컴퓨터공학전공' in f['must_not'][0]['must_not'][0]['match']['any']

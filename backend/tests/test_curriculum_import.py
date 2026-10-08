"""실제 입수한 유레카 출력물의 핵심 행·적용 조건 회귀 검사."""
import importlib.util
from pathlib import Path
import pytest
from app import agent
spec=importlib.util.spec_from_file_location('curriculum_import',Path(__file__).parents[1]/'scripts/import_curriculum_pdfs.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_2022_course_row_preserves_required_major_classification():
    path=Path('/Users/hyun/Downloads/2022_컴공_주전공.pdf')
    if not path.exists():pytest.skip('로컬 원본이 없는 환경')
    doc,chunks=module.extract(path)
    hits=[(h,r) for h in chunks for r in h['course_rows'] if r['영역명/학수번호']=='20481']
    assert len(hits)==1
    h,row=hits[0]
    assert row['교과목명']=='자료구조' and row['학점']=='3' and row['필수여부']=='Y'
    assert row['category']=='전공' and row['group']=='-전공필수'
    assert h['page']==7 and doc['admission_year']==2022 and doc['major_track']=='주전공'
    assert h['dates']['effective_from'] is None  # 출력일과 시행일을 혼동하지 않음


def test_track_mismatch_excluded_and_missing_track_requested():
    h={'title':'2022학년도 컴퓨터공학 교과과정표 (복수전공)','source_type':'교육과정',
       'applicability':{'department':{'status':'specified','values':['컴퓨터공학과']},
                        'major_track':{'status':'specified','values':['복수전공']}}}
    r={'question':'학수번호 20481 문의','profile':{'department':'컴퓨터공학과','major_track':'주전공','admission_year':2022}}
    assert agent.assess(h,r)['excluded']
    r['profile'].pop('major_track')
    assert 'major_track' in agent.assess(h,r)['missing_fields']

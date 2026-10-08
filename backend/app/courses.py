"""Qdrant 본문에서 만든 로컬 학수번호 정확 검색 인덱스."""
import json
import re
import sqlite3
from pathlib import Path
from .scope import scope_exclusions

INDEX_PATH=Path(__file__).resolve().parents[1] / 'data' / 'course_index.sqlite3'


def course_codes(question):
    if '학수번호' not in question:
        return []
    return list(dict.fromkeys(re.findall(r'(?<!\d)\d{5}(?!\d)',question)))


def lookup_courses(codes, department=None, admission_year=None, path=None, major_track=None):
    path=Path(path or INDEX_PATH)
    if not path.exists():
        return {'available':False,'codes':codes,'matches':{},'missing_codes':codes,'evidence':[]}
    matches, all_hits = {}, {}
    ranking_department=(department or '').replace('과','').replace('전공','').replace(' ','')
    with sqlite3.connect(path) as conn:
        for code in codes:
            rows=conn.execute('SELECT body FROM chunks JOIN codes ON chunks.chunk_id=codes.chunk_id WHERE codes.code=?',(code,)).fetchall()
            hits=[json.loads(row[0]) for row in rows]
            hits=[h for h in hits if not scope_exclusions(h, department, admission_year)
                  and (not major_track or not h.get('major_track') or h['major_track']==major_track)]
            def rank(h):
                title=h.get('title','')
                score=int(bool(ranking_department and ranking_department in title.replace(' ',''))) * 10
                score+=int(bool(admission_year and str(admission_year) in title))*2
                score+=int(h.get('source_type')=='교육과정')*4
                score+=int('교과과정' in title)*3
                return score
            hits.sort(key=rank,reverse=True)
            examples=[]
            for h in hits[:max(1,8//max(1,len(codes)))]:
                text=h['text']
                spans=[]
                for m in list(re.finditer(r'(?<!\d)'+re.escape(code)+r'(?!\d)',text))[:3]:
                    spans.append(text[max(0,m.start()-200):min(len(text),m.end()+500)])
                excerpt='\n…\n'.join(spans)
                examples.append({'chunk_id':h['chunk_id'],'title':h['title'],'source_url':h['source_url'],'excerpt':excerpt,
                                 'source_file':h.get('source_file'),'page':h.get('page'),'major_track':h.get('major_track'),
                                 'course_rows':[row for row in h.get('course_rows',[])
                                                if row.get('영역명/학수번호','').lstrip('*')==code]})
                h={**h,'text':excerpt,'retrieval_method':'course_code_exact','matched_course_codes':[code]}
                if h['chunk_id'] in all_hits:
                    all_hits[h['chunk_id']]['text']+='\n…\n'+excerpt
                    all_hits[h['chunk_id']]['matched_course_codes'].append(code)
                else:
                    all_hits[h['chunk_id']]=h
            matches[code]={'chunk_count':len(hits),'examples':examples}
    return {'available':True,'codes':codes,'matches':matches,
            'missing_codes':[c for c in codes if not matches[c]['chunk_count']],
            'evidence':list(all_hits.values())}

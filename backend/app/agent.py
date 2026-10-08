"""도구 선택 → 검색 → 관찰 → 재검색/정보 요청/초안/종료."""
from datetime import datetime
from zoneinfo import ZoneInfo
import re
from .search import search, SearchError
from .intake import processing_record
from .courses import course_codes, lookup_courses
from .scope import scope_exclusions, normalize_department
from .course_support import relevant_course_evidence, build_course_support
from .llm import decide_action, generate_draft, LLMConfigurationError, LLMServiceError


def valid_citations(text, evidence_ids):
    """일반 대괄호 제목과 인용을 구분하고 묶음 인용도 검증한다."""
    allowed=set(evidence_ids)
    found=set()
    for group in re.findall(r'\[([^\[\]\n]+)\]',text):
        # 실제 청크 ID는 24자리 문서 해시와 밑줄로 시작한다.
        # [학부], [처리 순서] 등 일반적인 제목은 인용으로 오인하지 않는다.
        tokens=re.findall(r'(?<![a-zA-Z0-9_])[0-9a-f]{24}_[a-zA-Z0-9_]+',group)
        if any(token not in allowed for token in tokens):
            return False
        found.update(tokens)
        if not tokens:
            # 테스트·외부 자료의 짧은 ID도 정확히 일치하면 허용한다.
            short=[t.strip() for t in re.split(r'[,;，；]',group)]
            matched={t for t in short if t in allowed}
            if matched and len(matched)!=len(short):
                return False
            found.update(matched)
    return bool(found)


def assess(evidence, record):
    """확인 가능한 조건만 검증하고 미확인은 명시적으로 남긴다."""
    profile = record['profile']
    missing, warnings, excluded = set(), [], []
    for field in ('department','admission_year','student_status','major_track'):
        if field == 'major_track' and field not in (evidence.get('applicability') or {}):
            continue
        condition = (evidence.get('applicability') or {}).get(field) or {}
        status = condition.get('status','unknown')
        value = profile.get(field)
        if status == 'unknown':
            warnings.append(f'{field}: 원문 적용 조건 미확인')
        elif status == 'specified':
            if value is None or value == '':
                missing.add(field)
            elif field == 'admission_year':
                if ((condition.get('from') is not None and value < condition['from']) or
                    (condition.get('to') is not None and value > condition['to'])):
                    excluded.append('입학연도 조건 불일치')
            elif (normalize_department(value) not in {normalize_department(v) for v in condition.get('values',[])} if field == 'department' else value not in condition.get('values',[])):
                excluded.append(f'{field} 조건 불일치')
    excluded.extend(scope_exclusions(evidence, profile.get('department'), profile.get('admission_year')))
    dates = evidence.get('dates') or {}
    as_of = record.get('as_of') or datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    if dates.get('effective_from') and dates['effective_from'][:10] > as_of:
        excluded.append('시행 전 자료')
    if dates.get('effective_until') and dates['effective_until'][:10] < as_of:
        excluded.append('적용 기간 종료')
    if record.get('target_term') and dates.get('target_term') and dates['target_term'] != record['target_term']:
        excluded.append('대상 학기 불일치')
    if evidence.get('source_type') == '공지' and not record.get('target_term'):
        warnings.append('공지의 대상 학기·기간 확인 필요')
    if evidence.get('metadata_review_required') or evidence.get('quality_flags'):
        warnings.append('추출 내용·메타데이터 검토 필요')
    return {'missing_fields':sorted(missing),'warnings':warnings,'excluded':excluded}


def run_agent(record):
    result = _run_agent(processing_record(record))
    # 검색에는 문의 대상 전공·체크리스트를 사용하되 응답에는 원래 입력을 보존한다.
    result['question'] = record['question']
    result['profile'] = record['profile']
    if result.get('support_summary'):
        result['support_summary']['student_reported'] = {'question': record['question'], 'profile': dict(record['profile'])}
    return result


def _run_agent(record):
    record.update(status='processing', draft=None, evidence=[], missing_fields=[],
                  unresolved_reason=None, next_actions=[], warnings=[], support_summary=None, staff_decision=None, staff_choice=None, staff_memo=None, draft_kind=None)
    searches, candidates = [], {}
    codes=course_codes(record['question'])
    record['course_lookup']=None
    def trace(step, detail):
        record['trace'].append({'step':step,'detail':detail})
    def course_result(reason=None):
        evidence=[h for h in candidates.values() if relevant_course_evidence(h)]
        summary, text=build_course_support(record,evidence,codes)
        missing=sorted({f for h in evidence for f in h.get('verification',{}).get('missing_fields',[])})
        record.update(support_summary=summary,draft=text,draft_kind='evidence_summary',evidence=evidence,
                      status='need_info' if missing else 'needs_review',missing_fields=missing,
                      unresolved_reason=reason,
                      next_actions=[], warnings=[])
        record['next_actions']=(['적용 조건을 보완한 뒤 다시 실행해 주세요.'] if missing else summary['staff_decisions'])
        trace('근거정리','확인된 과목 정보와 미확인 항목을 정리했습니다. 최종 판단은 담당자에게 넘깁니다.')
        return record
    def unresolved(reason):
        if codes:
            return course_result(reason)
        record.update(status='needs_review',unresolved_reason=reason,
                      next_actions=['근거·실행 기록을 확인한 뒤 담당자가 판단해 주세요.'])
        trace('확인필요',reason)
        return record
    try:
        if codes:
            lookup=lookup_courses(codes,record['profile'].get('department'),record['profile'].get('admission_year'),major_track=record['profile'].get('major_track'))
            relevant_hits=[h for h in lookup['evidence'] if relevant_course_evidence(h)]
            allowed_ids={h['chunk_id'] for h in relevant_hits}
            filtered_matches={}
            for code,item in lookup.get('matches',{}).items():
                examples=[e for e in item.get('examples',[]) if e['chunk_id'] in allowed_ids]
                filtered_matches[code]={'chunk_count':sum(code in h.get('matched_course_codes',[]) for h in relevant_hits),'examples':examples}
            record['course_lookup']={'available':lookup.get('available',False),'codes':codes,'matches':filtered_matches,
                                     'missing_codes':[c for c in codes if not filtered_matches.get(c,{}).get('chunk_count')]}
            lookup['evidence']=relevant_hits
            trace('학수번호정확조회',', '.join(f"{code}: {filtered_matches.get(code,{}).get('chunk_count',0)}개 청크" for code in codes))
            for h in lookup['evidence']:
                h['verification']=assess(h,record)
                if not h['verification']['excluded'] and relevant_course_evidence(h):
                    candidates[h['chunk_id']]=h
            record['evidence']=list(candidates.values())
            if any(any(row.get('영역명/학수번호','').lstrip('*') in codes for row in h.get('course_rows',[])) for h in candidates.values()):
                trace('목표확인','적용 가능한 과목표의 핵심 행을 확보하여 추가 인정 판단 검색 없이 담당자용 결과를 작성합니다.')
                return course_result()
        for _ in range(5):
            decision = decide_action(record, list(candidates.values()), searches)
            action = decision['action']
            trace('행동선택',f"{action}: {decision['reason']}")
            if action == 'search':
                query = decision['query'].strip()[:1000]
                if len(searches) >= 3:
                    return unresolved('3회 검색 후에도 적용 가능한 답변 근거를 확보하지 못했습니다.')
                if not query or query in searches:
                    alternatives=[
                        f"{record['profile'].get('department') or ''} {' '.join(codes)} 동일교과목 대체 인정 필수과목",
                        f"{record['profile'].get('admission_year') or ''} {record['profile'].get('department') or ''} {' '.join(codes)} 타전공 인정 졸업요건",
                        record['question'][:700]]
                    query=next((q.strip() for q in alternatives if q.strip() not in searches),None)
                    if query is None:
                        return unresolved('새로운 검색어를 구성하지 못했습니다. 수집된 자료를 담당자가 확인해 주세요.')
                    trace('검색어보완','비어 있거나 반복된 검색어를 핵심 식별자가 포함된 검색어로 바꿨습니다.')
                hits = search(query, department=record['profile'].get('department'),
                              admission_year=record['profile'].get('admission_year'))
                searches.append(query)
                trace('자료검색',f'{query} → {len(hits)}개 검색')
                for h in hits:
                    check = assess(h,record)
                    h['verification'] = check
                    if not check['excluded'] and (not codes or relevant_course_evidence(h)):
                        candidates[h['chunk_id']] = h
                # 컨텍스트·비용을 제한하며 가장 최근 검색 결과를 우선한다.
                exact={k:v for k,v in candidates.items() if v.get('retrieval_method')=='course_code_exact'}
                semantic={k:v for k,v in candidates.items() if v.get('retrieval_method')!='course_code_exact'}
                candidates={**dict(list(exact.items())[:8]),**dict(list(semantic.items())[-8:])}
                record['evidence'] = list(candidates.values())
                trace('조건검토',f'적용 조건 불일치 자료 제외 후 {len(candidates)}개 후보 유지')
                if codes and any(any(row.get('영역명/학수번호','').lstrip('*') in codes for row in h.get('course_rows',[])) for h in candidates.values()):
                    return course_result()
            elif action == 'ask':
                fields = [f for f in decision['missing_fields']
                          if not (record['profile'].get(f) if f in record['profile'] else record.get(f))]
                if not fields:
                    return unresolved('추가 정보 요청에 유효한 누락 항목이 없습니다.')
                record.update(status='need_info',missing_fields=fields,
                              next_actions=['학생 조건을 보완하여 /run으로 재실행해 주세요.'])
                trace('정보요청',', '.join(fields))
                return record
            elif action == 'draft':
                if codes:
                    return course_result()
                selected = [candidates[c] for c in decision['evidence_ids'] if c in candidates][:5]
                if not selected:
                    return unresolved('선택된 답변 근거가 없습니다.')
                # 같은 문서에서 검색된 예외·절차 조각을 모델 선택만으로 누락하지 않는다.
                docs = {h.get('doc_id') for h in selected if h.get('doc_id')}
                selected_ids = {h['chunk_id'] for h in selected}
                selected += [h for h in candidates.values() if h.get('doc_id') in docs
                             and h['chunk_id'] not in selected_ids][:max(0, 8-len(selected))]
                missing = sorted({f for h in selected for f in h['verification']['missing_fields']})
                if missing:
                    record.update(status='need_info',missing_fields=missing,
                                  next_actions=['적용 조건 확인을 위해 학생 정보를 보완해 주세요.'])
                    trace('정보요청',', '.join(missing))
                    return record
                warnings = sorted({w for h in selected for w in h['verification']['warnings']})
                text = generate_draft(record['question'], {**record['profile'],'target_term':record.get('target_term'),
                                      'as_of':record.get('as_of')}, selected)
                valid = {h['chunk_id'] for h in selected}
                if not valid_citations(text, valid):
                    return unresolved('생성된 초안의 근거 인용을 확인할 수 없습니다.')
                record.update(draft=text,draft_kind='student_reply', evidence=selected,warnings=warnings,
                              status='needs_review' if warnings else 'draft_ready',
                              unresolved_reason='근거 적용 범위 또는 추출 품질 확인이 필요합니다.' if warnings else None,
                              next_actions=['초안과 출처를 검토하고 수정·완료 처리해 주세요.'])
                trace('초안작성','검색 근거로 초안을 작성하고 인용 ID를 검사했습니다.')
                return record
            else:
                return unresolved(decision['reason'] or '근거가 부족해 자동 처리를 종료했습니다.')
        return unresolved('최대 실행 횟수에 도달했습니다.')
    except (SearchError, LLMConfigurationError, LLMServiceError) as exc:
        return unresolved(str(exc))

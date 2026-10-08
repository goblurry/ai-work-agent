"""과목 문의의 담당자용 근거 정리. 인정·졸업 여부는 판정하지 않는다."""
import re


def relevant_course_evidence(h):
    title = h.get('title') or ''
    url = h.get('source_url') or ''
    if any(term in title for term in ('폐강', '증원', '추가분반', '추가 분반', '장학', '모집', '취업')):
        return False
    if 'scsc' in url.lower():
        return False
    if h.get('course_rows'):
        return True
    return h.get('source_type') == '규정' or any(term in title for term in
        ('교과과정', '교육과정', '졸업요건', '동일교과목', '대체', '학점인정', '학점 인정', '재수강 인정'))


def build_course_support(record, evidence, codes):
    facts, sources, seen = [], [], set()
    for h in evidence:
        for row in h.get('course_rows') or []:
            code = row.get('영역명/학수번호', '').lstrip('*')
            if code not in codes:
                continue
            key = (code, h.get('doc_id'), h.get('major_track'))
            if key in seen:
                continue
            seen.add(key)
            facts.append({'course_code': code, 'course_name': row.get('교과목명'),
                          'credits': row.get('학점'), 'category': row.get('category'),
                          'requirement_group': row.get('group'), 'group_rule': row.get('group_rule'),
                          'required_flag': row.get('필수여부'), 'offering_department': row.get('개설학과'),
                          'admission_year': (h.get('applicability') or {}).get('admission_year', {}).get('from'),
                          'major_track': h.get('major_track'), 'chunk_id': h['chunk_id'],
                          'source_file': h.get('source_file'), 'page': h.get('page')})
        if h.get('course_rows') and any(row.get('영역명/학수번호','').lstrip('*') in codes for row in h['course_rows']):
            sources.append({'chunk_id':h['chunk_id'],'title':h.get('title'),'source_url':h.get('source_url'),
                            'source_file':h.get('source_file'),'page':h.get('page')})
    checked={f['course_code'] for f in facts}
    unknown=[f'학수번호 {code}의 과목 정보: 적용 범위 내 과목표에서 확인하지 못함' for code in codes if code not in checked]
    unknown.append('동일·대체 인정 관계와 최종 필수요건 충족 여부는 이 결과에서 확정하지 않음')
    summary={'purpose':'담당자 판단을 위한 과목 정보·근거 정리',
             'student_reported':{'question':record['question'],'profile':dict(record['profile'])},
             'confirmed_courses':facts,'unverified_items':unknown,
             'staff_question': {'text': f"문의에 제시된 학수번호 {' · '.join(codes)}의 이수·대체 관계로 학생이 질문한 필수 이수요건을 충족할 수 있나요?",
                                'options': ['yes', 'no', 'check'],
                                'labels': ['예', '아니요', '추가 확인 필요']},
             'staff_decisions':['근거를 확인하고 담당자 질문에 답한 뒤 /compose로 학생 답변 초안을 작성해 주세요.'],
             'sources':sources,'coverage':'과목표의 구조화된 행에서 확인한 정보만 아래 확인 사항으로 표시합니다.'}
    lines=['[담당자용 근거 요약]', '학생 진술과 아래 원문 확인 사항은 구분됩니다.', '', '[원문에서 확인된 과목 정보]']
    for f in facts:
        lines.append(f"- {f['course_code']} {f['course_name']} / {f['credits']}학점 / {f['category']} · {f['requirement_group']} / 필수 표시: {f['required_flag'] or '없음'}")
        lines.append(f"  적용: {f['admission_year']}학년도 · {f['major_track']} / 출처: {f['source_file']} {f['page']}페이지 [{f['chunk_id']}]")
        if f['group_rule']:
            lines.append('  상위 이수 조건: '+f['group_rule'])
    if not facts:
        lines.append('- 적용 범위 내 과목표에서 해당 과목의 구조화된 행을 확보하지 못했습니다.')
    lines += ['', '[미확인·담당자 판단]', *('- '+item for item in unknown),
              '- 다른 학수번호라는 사실만으로 Agent가 대체 가능·불가능이나 재수강 필요를 결정하지 않습니다.',
              '- 담당자가 판단한 답변을 작성한 뒤 최종 확정해 주세요.']
    return summary, '\n'.join(lines)

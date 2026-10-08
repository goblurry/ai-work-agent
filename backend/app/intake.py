"""문의 유형별 접수 항목. 모르는 값은 null로 보존한다."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

InquiryType = Literal['graduation', 'course_recognition', 'leave_return', 'other']


class InquiryDetails(BaseModel):
    model_config = ConfigDict(extra='forbid')
    required_course_code: str | None = Field(default=None, pattern=r'^\d{5}$', description='지정 과목 학수번호 (모름: null)')
    completed_course_code: str | None = Field(default=None, pattern=r'^\d{5}$', description='이수한 과목 학수번호 (모름: null)')
    procedure: Literal['leave', 'return'] | None = Field(default=None, description='휴학 / 복학')
    application_status: Literal['not_applied', 'saved', 'submitted', 'received', 'unknown'] | None = Field(default=None, description='미신청 / 임시저장 / 제출 / 접수완료 / 모름')
    application_date: date | None = Field(default=None, description='신청일 (실제 접수일과 구분)')
    receipt_date: date | None = Field(default=None, description='실제 접수일 (확인한 경우만)')

    @field_validator('required_course_code', 'completed_course_code', mode='before')
    @classmethod
    def clean_code(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    def check_type(self, inquiry_type):
        supplied = {k for k, v in self.model_dump().items() if v is not None}
        allowed = {'course_recognition': {'required_course_code', 'completed_course_code'},
                   'leave_return': {'procedure', 'application_status', 'application_date', 'receipt_date'}}.get(inquiry_type, set())
        if supplied - allowed:
            raise ValueError('선택한 문의 유형에 해당하는 상세 항목만 입력해 주세요.')


def processing_record(record):
    """원본 접수 내용을 바꾸지 않고 검색·생성용 조건을 구성한다."""
    from copy import deepcopy
    work = deepcopy(record)
    profile = work.setdefault('profile', {})
    if record.get('inquiry_type') in ('graduation', 'course_recognition') and profile.get('target_department'):
        profile['department'] = profile['target_department']
    details = record.get('details') or {}
    labels = {'graduation': '졸업·교과과정', 'course_recognition': '과목 이수·대체 인정',
              'leave_return': '휴학·복학', 'other': '기타 학사 문의'}
    context = []
    if record.get('inquiry_type') and record['inquiry_type'] != 'other':
        context.append('문의 유형: ' + labels[record['inquiry_type']])
    for field, label in [('required_course_code', '지정 과목 학수번호'), ('completed_course_code', '이수 과목 학수번호')]:
        if details.get(field):
            context.append(f'{label}: {details[field]}')
    if details.get('procedure'):
        context.append('신청 종류: ' + {'leave':'휴학','return':'복학'}[details['procedure']])
    if details.get('application_status'):
        context.append('신청 상태(학생 입력): ' + {'not_applied':'미신청','saved':'임시저장','submitted':'제출 (접수완료 여부 미확인)',
            'received':'접수완료','unknown':'모름'}[details['application_status']])
    for field, label in [('application_date','신청일'), ('receipt_date','실제 접수일')]:
        if details.get(field):
            context.append(f'{label}(학생 입력): {details[field]}')
    if context:
        work['question'] += '\n\n[접수 폼 입력]\n' + '\n'.join(context)
    return work

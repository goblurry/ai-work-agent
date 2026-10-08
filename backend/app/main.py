"""수업 시연용 웹·전화 문의 접수와 담당자 처리 API."""
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
import json
import os
from uuid import uuid4
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .database import Database
from .auth import Auth
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .intake import InquiryType, InquiryDetails
from .agent import run_agent
from .search import embedding_ready
from .courses import lookup_courses
from .llm import LLMConfigurationError, LLMServiceError, generate_student_reply

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
load_dotenv(ROOT.parent / '.env')

class Profile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    department: str | None = Field(default=None, description='학생의 소속 학과 (문의 대상 전공 학과와 구분)', examples=['컴퓨터공학과'])
    target_department: str | None = Field(default=None, description='졸업·교과과정 문의 대상 전공 학과. 비우면 소속 학과 사용', examples=['컴퓨터공학과'])
    major_track: Literal['주전공', '복수전공', '부전공'] | None = Field(default=None, description='교과과정 적용 구분')
    admission_year: int | None = Field(default=None, ge=1900, le=2100, description='입학연도', examples=[2022])
    student_status: str | None = Field(default=None, description='학적 상태: 재학·휴학 등', examples=['휴학'])

class NewInquiry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=10000, description='행정 담당자가 처리할 문의 내용', examples=['복학 신청 절차를 알려 주세요.'])
    inquiry_type: InquiryType = Field(default='other', description='graduation: 졸업·교과과정 / course_recognition: 과목 인정 / leave_return: 휴학·복학 / other: 기타')
    details: InquiryDetails = Field(default_factory=InquiryDetails, description='유형별 상세 조건. 모르는 값은 null')
    profile: Profile = Field(default_factory=Profile, description='학생 입력 또는 담당자가 확인한 조건')
    as_of: date | None = Field(default=None, description='판단 기준일 (YYYY-MM-DD), 비우면 오늘')
    target_term: str | None = Field(default=None, description='문의 대상 학기', examples=['2026-2'])

    @model_validator(mode='after')
    def validate_details(self):
        self.details.check_type(self.inquiry_type)
        return self

    @field_validator('question')
    @classmethod
    def clean_question(cls, value):
        if not value.strip():
            raise ValueError('문의 내용을 입력해 주세요.')
        return value.strip()

class ContinueInquiry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    inquiry_type: InquiryType | None = Field(default=None, description='문의 유형 변경')
    details: InquiryDetails | None = Field(default=None, description='변경할 상세 항목만 입력')
    profile: Profile = Field(default_factory=Profile, description='추가 확인한 학생 조건, 입력한 항목만 변경')
    as_of: date | None = Field(default=None, description='판단 기준일')
    target_term: str | None = Field(default=None, description='문의 대상 학기')

class StaffInquiry(NewInquiry):
    channel: Literal['phone', 'web'] = Field(default='phone', description='전화 문의는 phone, 직원이 대신 접수한 웹 문의는 web')

class InformationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=1, max_length=2000, description='담당자가 확인한 정보 보완 요청 안내')
    fields: list[Literal['department','admission_year','student_status','major_track','target_term','as_of']] = Field(min_length=1, description='보완이 필요한 입력 항목')

class ComposeReply(BaseModel):
    model_config = ConfigDict(extra='forbid')
    choice: Literal['yes', 'no', 'check'] | None = Field(default=None, description='예 / 아니요 / 추가 확인 필요')
    memo: str = Field(default='', max_length=4000, description='판단 이유 또는 추가 안내')
    text: str | None = Field(default=None, min_length=1, max_length=4000, description='선택형 질문이 없는 문의의 담당자 판단')

class ReviewInquiry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['edit', 'complete'] = Field(description='edit: 수정 저장 / complete: 완료 처리')
    text: str = Field(min_length=1, max_length=20000, description='담당자가 검토·수정한 답변')


def create_app(db_path: str | Path | None = None, processor=None, reply_writer=generate_student_reply):
    process = processor or run_agent
    write_reply = reply_writer
    path = Path(db_path or os.getenv('INQUIRY_DB_PATH', str(ROOT / 'data' / 'inquiries.sqlite3')))

    database = Database(path, None if db_path is not None else os.getenv('DATABASE_URL') or None)
    connect = database.connect

    auth = Auth(connect)

    @asynccontextmanager
    async def lifespan(app):
        auth.initialize()
        database.initialize_inquiries()
        with connect() as conn:
            columns = conn.columns('inquiries')
            if 'receipt_no' not in columns:
                conn.execute('ALTER TABLE inquiries ADD COLUMN receipt_no TEXT')
            if 'student_id' not in columns:
                conn.execute('ALTER TABLE inquiries ADD COLUMN student_id TEXT REFERENCES users(id)')
            for inquiry_id, body in conn.execute('SELECT id, body FROM inquiries').fetchall():
                record = json.loads(body)
                record.setdefault('receipt_no', uuid4().hex)
                record.setdefault('channel', 'phone')
                record.setdefault('student_id', None)
                record.setdefault('final_answer', record.get('draft') if record.get('status') == 'completed' else None)
                record.setdefault('information_request', None)
                record.setdefault('completed_at', record.get('updated_at') if record.get('status') == 'completed' else None)
                conn.execute('UPDATE inquiries SET body=?, receipt_no=? WHERE id=?',
                             (json.dumps(record, ensure_ascii=False),record['receipt_no'],inquiry_id))
            conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS inquiries_receipt_no ON inquiries(receipt_no)')
            conn.execute('CREATE INDEX IF NOT EXISTS inquiries_student_id ON inquiries(student_id)')
        yield

    app = FastAPI(title='학사 행정 Agent', version='0.6.0', lifespan=lifespan,
                  description='수업 시연용 MVP입니다. 학생 웹 접수 또는 담당자 전화 접수 → 담당자 Agent 실행 → 정보 보완 → 답변 확정 순서로 처리합니다. 학생 API는 확정된 답변만 제공합니다. 학생은 자신의 문의만 조회하며 담당자 API는 직원 계정으로만 이용합니다. API 키는 서버 설정에서 읽습니다.')
    origins = [v.strip() for v in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if v.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET','POST'], allow_headers=['Content-Type'], allow_credentials=True)

    app.state.auth = auth
    app.include_router(auth.router())

    @app.middleware('http')
    async def check_origin(request, call_next):
        origin = request.headers.get('origin')
        allowed = {*origins, str(request.base_url).rstrip('/')}
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin not in allowed:
            return JSONResponse(status_code=403, content={'detail': '허용되지 않은 요청 출처입니다.'})
        return await call_next(request)

    def get_record(inquiry_id):
        with connect() as conn:
            row = conn.execute('SELECT body FROM inquiries WHERE id=?', (inquiry_id,)).fetchone()
        if row is None:
            raise HTTPException(404, '문의를 찾을 수 없습니다.')
        return json.loads(row[0])

    def save(record):
        record['updated_at'] = datetime.now(timezone.utc).isoformat()
        with connect() as conn:
            conn.execute('INSERT INTO inquiries(id, body, receipt_no, student_id) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET body=excluded.body, receipt_no=excluded.receipt_no, student_id=excluded.student_id',
                         (record['inquiry_id'], json.dumps(record, ensure_ascii=False),record['receipt_no'],record.get('student_id')))
        return record

    @app.get('/health', summary='서버 상태 확인', description='서버 응답과 설정 여부를 확인합니다. 외부 서비스 접속 성공을 검사하는 기능은 아닙니다.', tags=['상태'])
    def health():
        return {'status':'ok', 'processing_connected':bool(embedding_ready() and os.getenv('OPENAI_API_KEY') and os.getenv('QDRANT_COLLECTION')),
                'openai_configured':bool(os.getenv('OPENAI_API_KEY')),
                'qdrant_configured':bool(os.getenv('QDRANT_URL') and os.getenv('QDRANT_API_KEY')),
                'embedding_configured':embedding_ready(), 'openai_model':os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')}

    def register(payload, channel, student_id=None):
        now = datetime.now(timezone.utc).isoformat()
        values = payload.model_dump(mode='json')
        values.pop('channel', None)
        return save({**values, 'inquiry_id':str(uuid4()), 'receipt_no':uuid4().hex,
                     'channel':channel, 'student_id':student_id, 'status':'received', 'draft':None, 'final_answer':None,
                     'information_request':None, 'completed_at':None,
                     'evidence':[], 'missing_fields':[], 'warnings':[], 'unresolved_reason':None,
                     'next_actions':['담당자가 Agent를 실행하거나 직접 답변해 주세요.'],
                     'trace':[{'step':'문의접수','detail':f'{channel} 경로로 문의를 접수했습니다.'}],
                     'created_at':now, 'updated_at':now})

    def student_view(record):
        labels = {'received':'접수 완료','processing':'처리 중','need_info':'담당자 확인 중',
                  'waiting_student':'추가 정보 요청','draft_ready':'담당자 검토 중',
                  'needs_review':'담당자 확인 중','completed':'답변 완료'}
        return {key:record.get(key) for key in
                ('receipt_no','question','inquiry_type','details','profile','target_term','as_of','created_at','updated_at','information_request')} | {
            'status':labels.get(record['status'],'담당자 확인 중'),
            'final_answer':record.get('final_answer') if record['status']=='completed' else None}

    def get_by_receipt(receipt_no, student_id):
        with connect() as conn:
            row=conn.execute("SELECT body FROM inquiries WHERE receipt_no=? AND student_id=? AND json_extract(body, '$.channel')=?",
                             (receipt_no,student_id,'web')).fetchone()
        if row is None:
            raise HTTPException(404,'접수번호에 해당하는 웹 문의를 찾을 수 없습니다.')
        return json.loads(row[0])

    def ensure_open(record):
        if record['status'] in ('completed','processing'):
            raise HTTPException(409,'완료되었거나 처리 중인 문의는 변경할 수 없습니다.')

    def supplement(record, payload):
        if not payload.model_fields_set:
            raise HTTPException(422,'보완할 정보를 입력해 주세요.')
        updated_details = dict(record.get('details') or {})
        inquiry_type = payload.inquiry_type or record.get('inquiry_type', 'other')
        if payload.inquiry_type and payload.inquiry_type != record.get('inquiry_type', 'other'):
            updated_details = {}
        if payload.details is not None:
            updated_details.update(payload.details.model_dump(mode='json', exclude_unset=True))
        try:
            InquiryDetails(**updated_details).check_type(inquiry_type)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        record.update(inquiry_type=inquiry_type, details=updated_details)
        record['profile'].update(payload.profile.model_dump(exclude_unset=True))
        for field in ('as_of','target_term'):
            if field in payload.model_fields_set:
                record[field]=payload.model_dump(mode='json')[field]
        record.update(status='received',draft=None,final_answer=None,evidence=[],missing_fields=[],
                      warnings=[],support_summary=None,staff_decision=None,staff_choice=None,staff_memo=None,draft_kind=None,information_request=None,unresolved_reason=None,
                      next_actions=['보완된 정보로 Agent를 다시 실행해 주세요.'])
        record['trace'].append({'step':'정보보완','detail':'조건을 보완했습니다. 담당자 재실행을 기다립니다.'})
        return save(record)

    @app.get('/materials/courses/{course_code}', summary='담당자 · 학수번호 정확 조회',
             description='수집된 본문에서 학수번호를 정확히 찾습니다. 과목 대체 인정이나 졸업 가능 여부를 판정하는 기능은 아닙니다.',tags=['보조'], include_in_schema=False, dependencies=[Depends(auth.require_staff)])
    def lookup_course(course_code: str, department: str | None = None, admission_year: int | None = None, major_track: str | None = None):
        import re
        if not re.fullmatch(r'\d{5}',course_code):
            raise HTTPException(422,'학수번호는 숫자 5자리로 입력해 주세요.')
        result=lookup_courses([course_code],department,admission_year,major_track=major_track)
        return {k:v for k,v in result.items() if k!='evidence'}

    @app.post('/students/inquiries', status_code=201, summary='학생 · 웹 문의 접수',
              description='문의만 저장합니다. Agent는 담당자가 실행합니다. 반환된 접수번호로 조회합니다.',tags=['학생'])
    def student_register(payload: NewInquiry, user=Depends(auth.require_student)):
        return student_view(register(payload,'web',user['id']))

    @app.get('/students/inquiries', summary='학생 · 내 문의 목록', tags=['학생'])
    def student_list(user=Depends(auth.require_student)):
        with connect() as conn:
            rows = conn.execute("SELECT body FROM inquiries WHERE student_id=? AND json_extract(body, '$.channel')='web' ORDER BY rowid DESC", (user['id'],)).fetchall()
        return [student_view(json.loads(row[0])) for row in rows]

    @app.get('/students/inquiries/{receipt_no}', summary='학생 · 접수번호로 문의·최종 답변 조회',
             description='시연용 접수번호 조회입니다. 내부 초안·검색 근거·실행 기록은 반환하지 않습니다.',tags=['학생'])
    def student_read(receipt_no: str, user=Depends(auth.require_student)):
        return student_view(get_by_receipt(receipt_no,user['id']))

    @app.post('/students/inquiries/{receipt_no}/supplement', summary='학생 · 요청받은 정보 보완',
              description='담당자가 정보 보완을 요청한 웹 문의에 추가 정보를 저장합니다. Agent는 자동 실행하지 않습니다.',tags=['학생'])
    def student_supplement(receipt_no: str, payload: ContinueInquiry, user=Depends(auth.require_student)):
        record=get_by_receipt(receipt_no,user['id'])
        ensure_open(record)
        if record['status']!='waiting_student':
            raise HTTPException(409,'현재 추가 정보를 요청받은 문의가 아닙니다.')
        return student_view(supplement(record,payload))

    @app.post('/inquiries', status_code=201, summary='담당자 · 전화 문의 등록',
              description='통화 중 확인한 질문과 학생 조건을 입력합니다. 등록만 하며 Agent는 실행 API에서 실행합니다.',tags=['담당자'], dependencies=[Depends(auth.require_staff)])
    def new_inquiry(payload: StaffInquiry):
        return register(payload,payload.channel)

    @app.post('/inquiries/{inquiry_id}/run', summary='담당자 · Agent 실행·재실행',
              description='본문 없이 실행하거나, 변경한 profile·details 등을 본문으로 보내 저장 후 바로 재실행합니다. 검색·조건 확인 후 담당자용 결과를 반환합니다. 학수번호 문의는 support_summary에 확인된 과목 정보·미확인 항목·출처를, draft에 읽기 쉬운 근거 요약을 제공합니다. 최종 답변은 담당자가 /review로 확정합니다. trace에 실제 실행 기록이 남습니다.',tags=['담당자'], dependencies=[Depends(auth.require_staff)])
    def run_inquiry(inquiry_id: str, payload: ContinueInquiry | None = None):
        record=get_record(inquiry_id)
        ensure_open(record)
        if payload is not None and payload.model_fields_set:
            record = supplement(record, payload)
        if record['status']=='waiting_student':
            raise HTTPException(409,'학생의 정보 보완을 기다리고 있습니다.')
        record['status']='processing'
        record['trace'].append({'step':'Agent실행','detail':'담당자가 Agent 실행을 요청했습니다.'})
        save(record)
        return save(process(record))

    @app.post('/inquiries/{inquiry_id}/request-info', summary='담당자 · 정보 보완 요청 확정',
              description='담당자가 요청 안내를 확인합니다. 웹 문의는 학생 조회에 표시하고, 전화 문의는 직원이 통화 중 질문합니다. 메일·문자를 발송하지 않습니다.',tags=['담당자'], include_in_schema=False, dependencies=[Depends(auth.require_staff)])
    def request_information(inquiry_id: str,payload: InformationRequest):
        record=get_record(inquiry_id)
        ensure_open(record)
        if not payload.message.strip():
            raise HTTPException(422,'보완 요청 내용을 입력해 주세요.')
        record.update(information_request={'message':payload.message.strip(),'fields':payload.fields},
                      status='waiting_student' if record['channel']=='web' else 'need_info')
        record['trace'].append({'step':'보완요청확정','detail':'담당자가 추가 정보 요청을 확인했습니다.'})
        return save(record)

    @app.get('/inquiries', summary='담당자 · 웹·전화 문의 목록', tags=['담당자'], dependencies=[Depends(auth.require_staff)])
    def list_inquiries():
        with connect() as conn:
            rows = conn.execute('SELECT body FROM inquiries ORDER BY rowid DESC').fetchall()
        return [json.loads(row[0]) for row in rows]

    @app.get('/inquiries/{inquiry_id}', summary='담당자 · 문의 상세·실행 기록 조회', tags=['담당자'], dependencies=[Depends(auth.require_staff)])
    def read_inquiry(inquiry_id: str):
        return get_record(inquiry_id)

    @app.post('/inquiries/{inquiry_id}/continue', summary='담당자 · 학생 조건 보완',
              description='전화 중 확인한 조건 등을 저장합니다. 이후 /run으로 Agent를 재실행합니다.',tags=['담당자'], include_in_schema=False, dependencies=[Depends(auth.require_staff)])
    def continue_inquiry(inquiry_id: str, payload: ContinueInquiry):
        record=get_record(inquiry_id)
        ensure_open(record)
        return supplement(record,payload)

    @app.post('/inquiries/{inquiry_id}/compose', summary='담당자 · 판단을 학생 답변 초안으로 작성',
              description='choice(yes/no/check)와 선택 메모를 입력합니다. 생성된 draft를 검토한 뒤 /review의 complete로 확정합니다.', tags=['담당자'], dependencies=[Depends(auth.require_staff)])
    def compose_reply(inquiry_id: str, payload: ComposeReply):
        record=get_record(inquiry_id)
        ensure_open(record)
        if record['status']=='waiting_student':
            raise HTTPException(409,'학생 정보 보완을 기다리고 있습니다.')
        question=(record.get('support_summary') or {}).get('staff_question')
        if payload.choice is not None:
            if not question:
                raise HTTPException(409,'선택할 담당자 질문이 없습니다. text로 판단을 입력해 주세요.')
            if payload.text is not None:
                raise HTTPException(422,'choice와 text 중 하나만 입력해 주세요.')
            label={'yes':'예','no':'아니요','check':'추가 확인 필요'}[payload.choice]
            decision=f"담당자 질문: {question['text']}\n담당자 답변: {label}"
            if payload.memo.strip():
                decision+='\n담당자 메모: '+payload.memo.strip()
        else:
            decision=(payload.text or '').strip()
            if not decision:
                raise HTTPException(422,'choice 또는 text를 입력해 주세요.')
            if payload.memo.strip():
                decision+='\n담당자 메모: '+payload.memo.strip()
        if not record.get('evidence'):
            raise HTTPException(409,'먼저 Agent를 실행하여 근거를 확인해 주세요.')
        if record.get('missing_fields'):
            raise HTTPException(409,'적용 조건을 보완하고 Agent를 다시 실행한 뒤 작성해 주세요.')
        if write_reply is None:
            raise HTTPException(503,'안내문 작성 서비스가 아직 연결되지 않았습니다.')
        try:
            text=write_reply(record,decision)
        except (LLMConfigurationError,LLMServiceError) as exc:
            raise HTTPException(503,str(exc)) from None
        if not isinstance(text,str) or not text.strip():
            raise HTTPException(503,'작성된 안내문이 비어 있습니다.')
        record.update(staff_decision=decision,staff_choice=payload.choice,staff_memo=payload.memo.strip(),draft=text.strip(),draft_kind='student_reply',status='needs_review',
                      next_actions=['작성된 안내문을 확인·수정한 뒤 /review에서 complete로 확정해 주세요.'])
        record['trace'].append({'step':'학생답변작성','detail':'담당자 판단과 근거로 안내문 초안을 작성했습니다. 아직 확정되지 않았습니다.'})
        return save(record)

    @app.post('/inquiries/{inquiry_id}/review', summary='담당자 · 초안 저장·최종 답변 확정', description='edit는 내부 초안만 저장합니다. complete는 최종 답변으로 확정하며 웹 문의의 학생 조회에 표시합니다. 전화 문의는 통화 안내를 완료한 것으로 기록합니다.', tags=['담당자'], dependencies=[Depends(auth.require_staff)])
    def review_inquiry(inquiry_id: str, payload: ReviewInquiry):
        record = get_record(inquiry_id)
        ensure_open(record)
        if not payload.text.strip():
            raise HTTPException(422, '안내 내용을 입력해 주세요.')
        record['draft'] = payload.text.strip()
        if payload.action == 'complete':
            record.update(status='completed',final_answer=payload.text.strip(),information_request=None,
                          completed_at=datetime.now(timezone.utc).isoformat())
        record['trace'].append({'step':'담당자검토','detail':'담당자가 안내 내용을 직접 작성·저장했습니다.'})
        return save(record)

    return app

app = create_app()

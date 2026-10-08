# Academic Inquiry Management System — Backend

문의 저장, 근거 검색, Agent 실행, 답변 작성·승인을 제공하는 FastAPI 서버입니다.

## 핵심 기능

- 학생·직원 로그인과 역할별 접근 제한
- 웹·전화 문의 접수와 목록·상세 조회
- 문의 유형별 학생 조건 저장 및 수정
- BGE-M3·Qdrant 기반 문서 검색과 적용 조건 검토
- 학수번호 정확 조회와 교과과정 근거 정리
- 검색 결과에 따른 재검색·정보 보완·초안 작성·중단
- 담당자 판단·메모를 반영한 답변 초안 작성
- 초안 수정 저장, 최종 승인, 학생 답변 조회

선택형 담당자 질문은 현재 과목 문의에 제공됩니다. 일반 문의는 근거 기반 초안을 검토하거나 담당자 판단을 텍스트로 입력합니다.

## 주요 API

### 로그인

- `POST /auth/login`: `{"username":"student","password":"설정한 비밀번호"}`로 로그인, 세션 쿠키 발급
- `POST /auth/logout`: 세션 종료
- `GET /auth/me`: 현재 계정의 `id`, `username`, `role` 조회

`.env`의 `DEMO_STUDENT_PASSWORD`, `DEMO_STAFF_PASSWORD`를 설정하면 첫 실행 시 계정을 생성합니다. DB에는 비밀번호 해시와 세션 토큰 해시를 저장합니다. 재시작 시 기존 계정·문의는 보존합니다. 기본 세션 유효기간은 12시간입니다.

### 학생

- `POST /students/inquiries`: 로그인한 학생의 문의 접수
- `GET /students/inquiries`: 내 문의 목록
- `GET /students/inquiries/{receipt_no}`: 처리 상태·최종 답변 조회

### 담당자

- `POST /inquiries`: 전화 문의 접수
- `GET /inquiries`: 문의 목록
- `GET /inquiries/{inquiry_id}`: 문의 상세·근거·실행 기록
- `POST /inquiries/{inquiry_id}/run`: Agent 실행. 변경할 조건을 함께 보내면 저장 후 재실행
- `POST /inquiries/{inquiry_id}/compose`: 담당자 선택·메모 또는 판단 텍스트로 답변 초안 작성
- `POST /inquiries/{inquiry_id}/review`: `edit`는 초안 저장, `complete`는 최종 승인

학생은 자기 문의만 조회하고 직원은 전체 문의를 처리합니다. 기존 작성자 없는 문의는 직원만 조회합니다. 전화 문의는 학생 계정에 자동 연결하지 않습니다.

접수는 저장만 합니다. 초안은 승인 전까지 학생에게 공개되지 않습니다.

## 문의 입력

`inquiry_type`: `graduation` / `course_recognition` / `leave_return` / `other`

- `question`: 문의 내용
- `profile`: 소속 학과, 문의 대상 전공 학과, 입학연도, 전공 구분, 학적 상태
- `details`: 유형별 학수번호 또는 휴·복학 신청 상태·신청일·실제 접수일
- `target_term`: 문의 대상 학기

모르는 값은 `null`, 해당하지 않는 항목은 생략합니다. 문의 대상 전공 학과가 있으면 그 학과로 검색합니다.

## 업무 DB

`DATABASE_URL`에 PostgreSQL 연결 문자열을 설정하면 계정·세션·문의를 해당 DB에 저장합니다. Supabase에서는 Connect → Session pooler(5432)의 연결 문자열을 사용합니다. 미설정 시 로컬 SQLite를 사용합니다. 원격 연결은 TLS를 사용하며 시작 시 테이블을 생성합니다.

기존 SQLite 자료를 옮기려면 서버를 중지하고 `backend/scripts/migrate_inquiries.py`를 실행합니다. 계정과 문의를 보존하고 로그인 세션은 새로 발급합니다. 동일 ID는 건너뛰며 다른 계정과 충돌하면 전체 작업을 취소합니다.

## 실행

저장소 루트에서 실행합니다. `.env`는 `backend/.env.example`을 참고해 설정합니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt -r backend/requirements-embedding.txt
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

로컬 임베딩은 `EMBEDDING_MODE=local`, `BGE_MODEL_PATH=BAAI/bge-m3`로 설정합니다. 학수번호 조회 인덱스는 `backend/scripts/build_course_index.py`로 생성합니다.

요청 형식과 응답은 [API 문서](http://127.0.0.1:8000/docs)에서 확인할 수 있습니다.


## 프론트 연결

모든 API 요청에 `credentials: "include"`를 넣습니다. `/auth/me`의 `role`이 `student`이면 학생 화면, `staff`이면 직원 화면을 표시합니다. `student_id`와 역할은 클라이언트가 지정하지 않습니다.

```javascript
fetch(`${API_URL}/auth/login`, {
  method: "POST",
  credentials: "include",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username, password })
});
```

로컬에서는 프론트와 API 주소의 호스트를 통일합니다(`127.0.0.1` 또는 `localhost`). HTTPS 배포 시 `COOKIE_SECURE=true`로 설정하고, 프론트와 API가 서로 다른 사이트이면 `COOKIE_SAMESITE=none` 및 정확한 `CORS_ORIGINS`를 설정합니다.

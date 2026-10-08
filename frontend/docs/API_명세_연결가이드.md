# API 명세 및 프론트 연결 가이드

기준: 백엔드 0.6.0. 정식 스키마는 이 폴더의 `openapi.json`, 실행 문서는 https://goblurry-academic-ai-agent.hf.space/docs 입니다. 숨겨진 보조 API는 아래에 별도 명시합니다.

## 1. 연결과 인증

백엔드 주소: `https://goblurry-academic-ai-agent.hf.space`.

로컬 프론트는 `http://127.0.0.1:5173`에서 실행하고 **/api 프록시**를 사용합니다. `src/shared/api.js`가 접두어를 자동으로 추가하므로 호출할 때 `/api`를 다시 붙이지 않습니다.

```javascript
import { request, post } from '../shared/api';
const me = await request('/auth/me');
const inquiries = await request('/inquiries');
const result = await post(`/inquiries/${id}/compose`, { choice: 'no', memo });
```

로그인은 아이디·비밀번호를 POST하고 응답 쿠키로 인증합니다. Bearer 토큰이나 API 키를 브라우저에서 입력하는 방식이 아닙니다. 로그인 정보나 세션 쿠키를 localStorage에 저장하지 않습니다.

| 메서드 | 경로 | 요청 | 결과 |
|---|---|---|---|
| POST | /auth/login | `{"username":"staff","password":"별도로 전달한 비밀번호"}` | `{id, username, role}`, HttpOnly 세션 쿠키 |
| GET | /auth/me | 없음 | 현재 계정 `{id, username, role}` |
| POST | /auth/logout | `{}` | 세션 만료·쿠키 삭제 |

role은 student 또는 staff. 최초 /auth/me가 401이면 로그인 화면을 보여 줍니다. 학생 계정이 담당자 API를 호출하면 403입니다. 로그아웃 시 화면의 기존 문의·근거·답변 상태를 비웁니다. 서버 세션 유효기간은 12시간입니다.

## 2. 담당자 핵심 API

모든 담당자 API는 staff 로그인 필요. 대부분 응답은 변경 후의 **전체 문의 객체**이므로 반환값으로 화면 상태를 교체합니다.

| 메서드 | 경로 | 용도 |
|---|---|---|
| GET | /inquiries | 모든 문의 목록, 최근 접수순 |
| GET | /inquiries/{inquiry_id} | 문의 상세 |
| POST | /inquiries | 전화 문의 등록, 201 |
| POST | /inquiries/{inquiry_id}/run | Agent 실행·조건 변경 후 재실행 |
| POST | /inquiries/{inquiry_id}/compose | 담당자 판단과 근거로 답변 초안 생성 |
| POST | /inquiries/{inquiry_id}/review | 초안 수정 저장 또는 최종 답변 확정 |

### 전화 문의 등록

```json
{
  "channel": "phone",
  "inquiry_type": "course_recognition",
  "question": "동일한 과목명이지만 학수번호가 다른 과목을 이수했습니다. 필수요건 인정이 가능한가요?",
  "profile": {
    "department": "컴퓨터공학과",
    "target_department": null,
    "admission_year": 2022,
    "major_track": "주전공",
    "student_status": "재학"
  },
  "details": {"required_course_code": "20481", "completed_course_code": "39144"},
  "target_term": null
}
```

접수는 저장만 합니다. run을 별도로 호출해야 합니다. 전화 문의는 학생 계정에 자동 연결되지 않습니다.

### run: Agent 실행

본문 없이 POST하면 현재 조건으로 실행합니다. `post(path,{})`도 가능합니다. 조건을 변경할 때는 아래처럼 보내면 저장과 재실행을 한 번에 합니다.

```json
{"profile":{"major_track":"주전공","admission_year":2022}}
```

반환 후 evidence·조건 검토 결과·trace를 표시합니다. run은 동기 실행이며 SSE/작업 polling API가 없습니다. 요청이 오래 걸릴 수 있으므로 로딩과 중복 실행 방지만 제공합니다. processing에서 강제 재실행하는 버튼을 만들지 않습니다.

### compose: 답변 초안 작성

`support_summary.staff_question`이 있으면 아래 형식을 사용합니다.

```json
{"choice":"no","memo":"학수번호가 같아야 필수요건으로 인정됩니다."}
```

choice: yes / no / check. labels와 질문은 응답을 사용합니다. 모든 문의에 선택형 질문이 있는 것은 아닙니다.

선택형 질문이 없다면 아래처럼 판단 텍스트를 보냅니다.

```json
{"text":"담당자가 확인한 안내 방향","memo":"추가 안내 사항"}
```

choice와 text는 함께 보내지 않습니다. 검색 근거가 없거나 missing_fields가 남아 있으면 409입니다. 먼저 조건 보완·근거 확보를 진행하거나 직접 답변을 작성해 review로 저장합니다.

성공 시 draft에 학생 답변 초안, draft_kind=student_reply, status=needs_review. 아직 final_answer는 확정되지 않습니다. 이 단계에서 OpenAI가 호출됩니다. 초안이 마음에 들지 않으면 판단/메모를 바꿔 compose 재호출하거나 직접 편집합니다.

### review: 편집 저장·최종 답변 등록

```json
{"action":"edit","text":"담당자가 편집한 초안"}
```

edit는 draft만 저장하고 학생에게 공개하지 않습니다. 상태를 별도로 완료로 바꾸지 않습니다.

```json
{"action":"complete","text":"학생에게 제공할 최종 답변"}
```

complete는 status=completed, final_answer, completed_at을 저장합니다. 학생의 내 문의에서 확인 가능합니다. 전화 문의는 통화 안내 완료 기록으로 사용합니다. edit/complete는 LLM을 호출하지 않으며 text를 그대로 저장합니다. 확정할 문장은 담당자가 확인해야 합니다. 완료된 문의는 현재 MVP에서 다시 편집하지 않습니다.

## 3. 전체 문의 응답에서 사용하는 필드

| 필드 | 화면에서의 사용 |
|---|---|
| inquiry_id | 담당자 API 요청용 ID |
| receipt_no | 학생 조회용 접수번호. inquiry_id와 혼동하지 않기 |
| channel | web / phone |
| inquiry_type | graduation / course_recognition / leave_return / other |
| question, profile, details | 원문 문의와 학생이 제출한 조건 |
| status | 아래 처리 상태 |
| evidence | 근거 청크. title, text, source_url, chunk_id, verification 등. 없는 속성은 생략 처리 |
| support_summary | 학수번호 문의의 확인된 정보와 담당자 판단 질문. 다른 문의에서는 null 가능 |
| support_summary.confirmed_courses | course_code, course_name, credits, category, required_flag, major_track, page 등 |
| support_summary.unverified_items | 확인되지 않은 항목, 불가 판정과 구분 |
| support_summary.sources | 출처, PDF 파일명·페이지 등 |
| support_summary.staff_question | `{text, options:["yes","no","check"], labels:["예","아니요","추가 확인 필요"]}` |
| draft, draft_kind | 초안과 그 종류. evidence_summary는 담당자용 근거 요약, student_reply는 학생 답변 초안 |
| final_answer, completed_at | 확정 답변·완료 시각 |
| missing_fields | 필요한 학생 조건 목록 |
| warnings, unresolved_reason, next_actions | 주의점·확인 필요 이유·다음 작업 |
| information_request | `{message, fields}` 형태의 보완 요청, 없으면 null |
| staff_decision, staff_choice, staff_memo | 담당자 판단 기록, 실행 전에는 없거나 null |
| trace | `{step, detail}` 목록. 결과 반환 후 실행 기록으로 표시 |
| created_at, updated_at | 접수·수정 시각 |

null/빈 배열/속성 누락을 모두 처리합니다. API 답변 문자열은 HTML로 삽입하지 말고 텍스트로 표시합니다. 출처 링크는 http/https만 허용하고 새 탭 링크에는 rel=noopener를 사용합니다.

### 상태별 동작

| status | 표시 | 다음 작업 |
|---|---|---|
| received | 접수 완료 | run 또는 직접 답변 작성 |
| processing | 처리 중 | 실행 중복 방지 |
| need_info | 정보 확인 필요 | 조건 보완 후 run 또는 학생 보완 요청 |
| waiting_student | 학생 보완 대기 | 학생 보완을 기다림. run 금지 |
| draft_ready | 초안 준비 | 검토·편집·확정 |
| needs_review | 담당자 검토 필요 | 근거/판단 확인·compose 또는 직접 작성 |
| completed | 답변 완료 | 읽기 전용 |

status만 보고 답변 성격을 추정하지 않습니다. needs_review라도 draft가 근거 요약일 수 있으므로 draft_kind와 support_summary를 함께 확인합니다.

## 4. 보완 요청 API (Swagger에서 숨김)

`POST /inquiries/{inquiry_id}/request-info`, staff 필요.

```json
{"message":"입학연도와 전공 구분을 알려 주세요.","fields":["admission_year","major_track"]}
```

fields 허용값: department, admission_year, student_status, major_track, target_term, as_of. 웹 문의는 waiting_student가 되고 학생 화면에 보완 요청이 표시됩니다. 메일·문자는 발송하지 않습니다. 학생이 보완하면 received로 돌아옵니다. 목록을 새로고침해서 확인한 뒤 run을 눌러 주세요.

전화 문의는 need_info가 되며 직원이 통화 중 조건을 확인합니다. run 본문에 변경 조건을 보내는 방식을 우선 사용합니다. 필요하면 `POST /inquiries/{id}/continue`로 조건만 저장할 수 있지만 저장 후 run을 별도로 호출해야 합니다.

학생 화면에서는 학기 입력을 휴학·복학에만 표시합니다. target_term은 휴학·복학 대상 학기이며 신청일과 다릅니다. 담당자가 다른 유형의 문의에 특정 학기를 요청하면 정보 보완 화면에서 입력할 수 있습니다. unknown 값은 null로 보존하며 전원 적용으로 취급하지 않습니다.

## 5. 학생 API (이미 학생 화면에 연결)

| 메서드 | 경로 | 용도 |
|---|---|---|
| POST | /students/inquiries | 학생 자신의 웹 문의 접수, 201 |
| GET | /students/inquiries | 자기 문의 목록 |
| GET | /students/inquiries/{receipt_no} | 자기 문의·상태·확정 답변 조회 |
| POST | /students/inquiries/{receipt_no}/supplement | 요청받은 정보 보완, 요청 상태일 때만 가능 |

학생 접수에는 channel, student_id, role을 넣지 않습니다. 작성자는 로그인 세션에서 결정됩니다. 요청 형식은 전화 문의 예시에서 channel을 뺀 것과 같습니다.

학생 응답은 내부 ID·검색 근거·실행 기록·초안을 제외하고 status를 한국어 표시명으로 반환합니다. 직원 응답의 원시 status와 다릅니다. final_answer는 completed일 때만 공개됩니다. 다른 학생의 문의는 404입니다.

### 접수 조건

- question: 공백 제외 필수, 최대 20,000자.
- profile: department, target_department, admission_year(1900~2100), major_track(주전공/복수전공/부전공), student_status.
- target_term: 예 `2026-2`, 모르면 null. as_of: 판단 기준일 YYYY-MM-DD, 생략 가능.
- course_recognition details: required_course_code, completed_course_code. 각각 숫자 5자리 문자열 또는 null.
- leave_return details: procedure(leave/return), application_status(not_applied/saved/submitted/received/unknown), application_date, receipt_date.
- graduation/other의 details는 `{}`. 다른 유형의 상세 항목을 섞으면 422.

## 6. 오류와 로딩

401은 로그인 필요, 403은 역할/출처 불일치, 404는 존재하지 않거나 접근할 수 없는 문의, 409는 현재 상태에서 수행 불가, 422는 입력값 오류, 503은 LLM/외부 서비스 오류입니다. `detail`은 문자열 또는 검증 오류 배열일 수 있습니다.

네트워크 오류 시 편집 내용은 보존합니다. 문의 등록 요청이 시간 초과되었을 때 바로 중복 접수하지 말고 목록에서 접수 여부를 먼저 확인합니다. 완료 버튼은 중복 제출 방지합니다.

## 7. 최종 프론트 배포

Vite의 server.proxy는 **개발 전용**이며 npm run build 결과에 포함되지 않습니다. 정적 호스팅에 파일만 올리면 /api가 자동 연결되지 않습니다.

권장: 배포 서비스에서 `/api/:path*`를 `https://goblurry-academic-ai-agent.hf.space/:path*`로 전달하는 역방향 프록시를 설정합니다. 쿠키의 Set-Cookie 전달이 가능한지 확인합니다. 배포는 HTTPS로 하고 로컬 Vite의 Secure 제거 로직을 운영 환경에 복사하지 않습니다.

예: Vercel에서 프론트 디렉터리를 프로젝트 루트로 배포할 경우 vercel.json에 다음 rewrite를 설정합니다.

```json
{
  "rewrites": [{"source":"/api/:path*","destination":"https://goblurry-academic-ai-agent.hf.space/:path*"}]
}
```

앱에 경로 기반 라우터를 추가했다면 정적 페이지 fallback도 별도로 설정하고 /api 규칙보다 앞에 두지 않습니다.

배포된 프론트의 정확한 주소를 Hugging Face Space Settings의 `CORS_ORIGINS` Variable에 추가합니다. 기존 로컬 주소는 쉼표로 함께 유지할 수 있습니다. 프론트와 API의 HTTPS 쿠키 설정은 COOKIE_SECURE=true / COOKIE_SAMESITE=none입니다.

대안: VITE_API_URL에 배포 API 주소를 넣어 직접 호출할 수 있습니다. 이 경우도 CORS 설정이 필요하며 브라우저의 타사 쿠키 차단 영향을 받을 수 있어 동일 출처 프록시를 우선 권장합니다.

Supabase 서비스 키, DATABASE_URL, Qdrant 키, OpenAI 키는 프론트에 넣지 않습니다. 백엔드 Secrets로 이미 설정되어 있습니다. CORS 변경을 위한 관리 권한이 없다면 현선에게 최종 배포 주소를 전달합니다.

## 8. 통합 확인 순서

1. 학생 계정 로그인→문의 접수→내 문의에 접수 완료 확인.
2. 직원 계정 로그인→같은 문의 조회→run→근거 확인.
3. 판단·메모 입력→compose→draft_kind와 초안 확인.
4. edit 저장 후 학생에게 최종 답변이 없는지 확인.
5. complete 승인→학생으로 다시 로그인→내 문의 최종 답변 확인.
6. 추가 정보 요청→학생 보완→직원 재실행 확인.
7. 전화 문의 등록·처리 및 계정 역할별 접근 확인.

같은 브라우저의 탭들은 쿠키를 공유합니다. 학생과 직원으로 동시에 시연하려면 별도 브라우저 또는 시크릿 창을 사용합니다.

## 담당자 화면별 연결 위치

- 공통 진입: GET /auth/me. 401이면 POST /auth/login. 모든 요청은 쿠키 인증.
- 대시보드: GET /inquiries로 집계·미처리 목록·최근 완료 목록을 구성. 오늘 기준은 Asia/Seoul. 집계 전용 API는 없습니다.
- 웹/전화 목록: 같은 목록 응답을 channel로 구분. 웹 탭은 completed / waiting_student / 나머지 상태로 분류. 탭 전환은 로컬 필터링, 새로고침은 목록 재조회.
- 목록 행 클릭: GET /inquiries/{inquiry_id}로 상세·기존 초안·근거·최종 답변 복원.
- 전화 접수: POST /inquiries(channel: phone) → 반환된 ID로 run. 저장 성공·실행 실패 시 같은 ID로 재실행.
- 근거 확인 버튼: run → evidence, support_summary, missing_fields, warnings, trace 표시.
- 답변 초안 생성 버튼: compose → draft 표시. 선택형 질문은 yes/no/check, 일반 문의는 text 판단 입력.
- 초안 저장 버튼: review(action: edit). 승인·등록 버튼: review(action: complete).
- 정보 보완 요청 버튼: request-info. 학생 보완 후 목록을 다시 조회하고 run 재실행.
- 최종 등록 후: 응답으로 상세 상태를 갱신하고 목록 재조회. 대기 목록에서 제외하고 완료 탭에 보관합니다.

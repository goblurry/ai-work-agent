담당자 화면은 이 경로에서 개발합니다. 학생 화면은 ../student, 공통 색상·컴포넌트·API는 ../shared를 사용합니다.

## 구성

| 파일 | 역할 |
|---|---|
| `StaffApp.jsx` | 헤더·왼쪽 메뉴와 화면 전환, `/inquiries` 목록 보관 |
| `Dashboard.jsx` | 오늘 집계, 미처리 문의, 최근 등록한 답변 |
| `WebInquiries.jsx` | channel=web 목록. 답변 대기 / 학생 보완 대기 / 답변 완료 |
| `PhoneIntake.jsx` | channel=phone 접수 폼과 목록 |
| `InquiryDetail.jsx` | 공통 문의 처리 화면 |
| `SupplementRequest.jsx` | 정보 보완 요청 |
| `InquiryRow.jsx` | 목록 행 |
| `common.js` | 상태·유형 표시명, Asia/Seoul 날짜 |
| `styles.css` | `.staff-` 접두어 전용 스타일 |

## 알아 둘 점

- 화면 선택은 `src/Root.jsx`가 `/auth/me`의 role로 합니다. 역할을 임의로 고르지 않습니다.
- 기본 주소(`/`)는 담당자 로그인입니다. 학생 화면은 시연용이라 링크 없이 `/student`에서만 접근합니다.
- 집계는 `GET /inquiries` 한 번으로 계산합니다. 통계 전용 API를 쓰지 않습니다.
- 실행 기록은 run 응답의 trace만 보여 줍니다. 진행 단계를 만들어 내지 않습니다.
- `draft_kind`가 `evidence_summary`면 담당자용 근거 요약으로 표시하고 학생 답변으로 취급하지 않습니다.
- 전화 문의는 저장과 실행이 분리되어 있습니다. 저장 후 실행이 실패하면 같은 문의로 재실행하며 다시 등록하지 않습니다.
- 접수번호는 학생 조회용이므로 웹 문의에만 표시합니다.
- 자료에서 확인되지 않은 항목은 불가 판정으로 바꾸지 않고 확인 사항으로 표시합니다.

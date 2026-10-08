# 학사나침반 — 프론트엔드

담당자용 학사행정 문의 처리 화면. React + Vite.

## 실행

```bash
npm install
npm run dev
```

`.env` 가 없으면 **샘플 데이터로 동작**합니다. 백엔드 없이 모든 화면을 확인할 수 있습니다.

| 학번 입력 | 나오는 화면 |
|---|---|
| `2021…` | 답변 초안 (A) |
| `2022…` | 확정 불가 — 자료 충돌 (C) |
| 그 외 | 추가 확인 필요 (B) → 보완 입력 후 재개 |

## 백엔드 연결

```bash
cp .env.example .env
# VITE_API_BASE=http://localhost:8000
```

주소만 넣으면 실제 호출로 바뀝니다. **화면 코드는 수정하지 않습니다** (`src/api.js` 가 흡수).

## API 계약

`src/api.js` 가 기대하는 형식입니다. 응답 본문은 `../schemas/answer_result.json` 을 따릅니다.

```
POST /api/inquiry                      { question, student_id, as_of? }
POST /api/inquiry/{id}/resume          { answers: { ... } }
POST /api/inquiry/{id}/review          { action: "save"|"edit", text? }
GET  /api/student/{student_id}
```

## 처리 상태

| 상태 | 화면 |
|---|---|
| idle | 입력 대기 |
| running | 처리 중 + 실행 기록이 한 줄씩 쌓임 |
| A_draft | 초안 + 근거 + [초안 수정] [완료 저장] |
| B_need_info | 확인 항목 + 보완 입력 + [보완 후 재개] |
| C_undetermined | 확정 불가 + 사유 + 충돌 병치 + 다음 확인 사항 |
| error | 오류 + [재시도] |

## 구조

```
src/
  App.jsx          상태 관리 + 화면 조립
  api.js           API 어댑터 (mock ↔ 실제 전환)
  mock/            샘플 응답 A·B·C
  components/      결과 3종 + 근거 패널 + 실행 기록
```

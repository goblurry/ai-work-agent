# 이화여대 학사 자료 RAG 통합 노트북

사용할 노트북은 **학사자료_RAG_통합.ipynb 하나**입니다. 기존 파일을 보완본으로 교체했습니다. 이전 노트북은 기존 백업 ZIP 내부에만 보관합니다.

## 실행

Python 3.10+의 Jupyter/PyCharm에서 커널 재시작 후 모든 셀을 실행하세요.

- 입력: `03_정제문서/documents_unique.jsonl`, `02_원본/`, 수집 대장. 원본 데이터는 수정하지 않습니다.
- 필수 패키지: IPython, lxml. JSON Schema 추가 검증은 jsonschema가 설치되어 있으면 실행합니다.
- 기본 설정: 전체 원본 선별, 인계 표본 25개, `RUN_QDRANT_LOAD=False`.
- 전체 인계: 첫 설정 셀의 `HANDOFF_MODE="full"`.
- 실제 임베딩·DB 적재: `RUN_QDRANT_LOAD=True`, `%pip install FlagEmbedding qdrant-client huggingface-hub`.
- local은 PC 내부 DB, 공유 서버는 `QDRANT_MODE="server"`와 QDRANT_URL/QDRANT_API_KEY 환경변수. 키는 코드·Git·데이터 파일에 넣지 않습니다.

## 보완한 내용

- 학술지 투고·간행 규정과 외부 민간 자격·교육 과정을 학사 이수 자료와 구분.
- 짧은 신청 단계·조건 보존. 증명서 안내의 단계 1·2·3·5 복원 확인.
- 부분 본문·문자 손상·미확정 FAQ 연결을 인계/적재 전에 보류. DB 적재 코드에서도 같은 기준 재검사.
- 적용 조건 unknown, 날짜 null은 허용. 제한 없음의 근거가 있을 때만 all 사용.
- 원문에 함께 쓰인 `25학번(2025학년도)`처럼 근거가 있는 학번 표현 처리.
- FAQ 질문+답변, 표 행·열, 조문·예외·부칙·과거 연도 보존.

## 결과 파일

폴더: `10_학사선별/학부_학사_통합_v4_전달_sample/` 또는 `_전달_full/`.

- 정상 인계: `documents.jsonl`, `chunks.jsonl`.
- 구조/DB/조회: `schema.json`, `qdrant_spec.json`, `query_example.py`.
- 본문 결함 보류: `quarantined_documents.jsonl`, `quarantined_chunks.jsonl`, `quality_gate.json`.
- 추출 실패/미해결 참조: `extraction_failures.jsonl`, `unresolved_references.jsonl`, `referenced_documents.jsonl`.
- 결과·검증: `handoff_summary.json`, `verification.json`, `인계_안내.md`.

선별·검수 중간 파일은 최종 인계용 두 파일과 구분하세요. 보류 파일은 DB 적재 대상이 아닙니다.

## 확인 결과 — 2026-10-06

모든 코드 셀 **24개**를 순서대로 실행했고 표본 **문서 25개·청크 325개**를 생성했습니다. 보완 자동 검사 9개와 출력 검사 25개를 통과했습니다. 표본에는 규정·안내·FAQ·공지·교육과정 5개 유형과 표 8개가 포함됩니다.

전체 재조립 문서 8,449개 중 규칙상 통과 7,163개, 보류 1,286개입니다. 표본은 유형/형식 확인용으로 전체 의미 정확도나 오분류율을 평가한 결과는 아닙니다. 기존 PDF/HWP의 표·레이아웃 검토 표시는 유지됩니다.

**실제 BGE-M3 임베딩·Qdrant 적재는 미실행(not_loaded)**입니다. 별도의 가상 벡터 API 확인은 실제 자료 적재 완료를 뜻하지 않습니다. 적재를 실행하면 모델 커밋·벡터 명세·실제 적재 건수를 기록합니다.

### 장학 공고의 자격증 항목 판정 수정 (2026-10-07)

- 문서 전체에서 업무 목적을 확인하고, 청크 검수·저장·DB 적재에도 같은 문서 문맥을 사용합니다.
- 장학생 선발 공고의 자격증 평가표를 외부 민간자격 취득 안내로 분류하지 않습니다.
- 모든 문서의 청크 결함을 표본 선택 전에 검사합니다. 결함 문서는 이유와 함께 보류 JSONL로 분리하며 전체 실행을 중단하지 않습니다.
- 이번 수정 후에는 커널을 재시작하고 처음부터 실행하세요. 기존 결과 파일은 자동 갱신되지 않으며, 다시 실행한 뒤에만 수정된 기준이 반영됩니다.

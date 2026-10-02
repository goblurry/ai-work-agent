"""에이전트 루프. 담당: 현선 + 한준

출처: CRAG / Self-RAG 계열 (Agentic RAG Survey arXiv:2501.09136)
차이: 일반 CRAG 의 루프 종료 조건은 '검색 품질 점수' 지만,
      우리는 '적용 조건 검증 통과' 를 종료 조건으로 삼는다. (문헌에 없음)
"""
MAX_RETRY = 3


def run(question: str, student_id: str) -> dict:
    """반환: schemas/answer_result.json 형식

    1. 의도 분류 (hoBIT §2.2.1) — retrieval 질의만 통과
    2. 학적 DB 조회 → profile (verified=True)
    3. search()
    4. verify()
    5. 실패 + 재시도 여지 → 검색 범위 조정 후 3으로 (최대 MAX_RETRY)
    6. 분기
         ok                → A_draft
         프로필 필드 부족    → B_need_info
         충돌/불명/재량      → C_undetermined
    모든 단계는 trace 에 기록한다. 화면에 그대로 노출된다.
    """
    raise NotImplementedError

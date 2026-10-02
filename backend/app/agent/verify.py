"""적용 조건 검증. 담당: 현선 — ★ 우리 시스템의 핵심

선행연구에 없는 부분. 검색이 끝이 아니라, 찾아온 근거가
'이 학생에게, 이 시점에' 실제로 적용되는지 따로 판정한다.
"""


def verify(evidence: list[dict], profile: dict, as_of: str) -> dict:
    """반환: {"ok": bool, "reason": str|None, "conflicts": [...]}

    판정 규칙 (정리본 §2):
      - 입학연도가 applies_to.admission_years 범위에 들어가는가
      - as_of 가 validity 구간에 들어가는가
      - transitional(경과조치) 이 있으면 기존 입학생 적용 여부를 따로 확인
      - confirm_status 가 '확인완료' 가 아니면 ok=False, reason='최신성불명'
      - 같은 주제에 서로 다른 결론이면 ok=False, reason='자료충돌'
        → 최신 게시물이라는 이유만으로 자동 선택하지 않는다
    """
    raise NotImplementedError


def compute_credits(profile: dict, requirement: dict) -> dict:
    """학점 충족 여부는 벡터 유사도가 아니라 여기서 계산한다 (정리본 §4).
    반환: {"met": bool, "shortfall": {...}}
    """
    raise NotImplementedError

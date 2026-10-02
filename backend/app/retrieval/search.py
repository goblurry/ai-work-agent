"""검색. 담당: 현선

하이브리드: arXiv:2502.16767 (규정 텍스트에서 BM25+dense 가 단독보다 우수)
융합:     RRF (Cormack et al., SIGIR 2009) — hoBIT 채택
임베딩:   BGE-M3 (arXiv:2402.03216)
시간 필터: TimelyRAG(arXiv:2609.11572) 의 as-of 하드 필터링 아이디어
"""
from typing import Optional


def search(
    query: str,
    profile: dict,              # schemas/student_profile.json
    as_of: Optional[str] = None,  # 기준일. 없으면 오늘
    target_term: Optional[str] = None,
    top_k: int = 20,
) -> list[dict]:
    """3축 조건부 하이브리드 검색.

    축1 프로필: applies_to.admission_years / department / major_type 필터
    축2 시간:   validity.effective_from <= as_of <= effective_until
    축3 학기:   validity.target_term == target_term

    주의: 필터를 너무 세게 걸면 아무것도 안 나온다.
          0건이면 필터를 단계적으로 풀고, '어느 축을 풀었는지' 를 반환에 남길 것.
          (그게 C분기의 '확정 불가' 판단 근거가 된다)
    """
    raise NotImplementedError

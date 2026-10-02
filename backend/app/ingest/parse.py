"""문서 → 청크. 담당: 한준 (원본 데이터 보유)

참고: SLLM 교육기관 문서 QA 논문(KCI ART003249789)의 '섹션 기반 파싱'과
표 데이터 처리 기법. 교육과정 표는 제목·열이름·단위·주석을 함께 보존한다.
"""
from typing import Iterable, Literal

SourceType = Literal["규정", "안내", "FAQ", "공지", "교육과정"]


def clean_html(raw: str) -> str:
    """메뉴·푸터·중복 문구 제거. 본문과 표의 의미는 유지."""
    raise NotImplementedError


def split_chunks(text: str, source_type: SourceType) -> Iterable[dict]:
    """의미 단위로 분할.

    규정   → 조문 단위 (예외·부칙은 본문과 연결)
    안내   → 의미가 완결되는 항목 단위
    FAQ    → 질문+답변 1쌍 = 1청크
    교육과정 → 표 1개 = 1청크 (열 이름 보존)
    """
    raise NotImplementedError

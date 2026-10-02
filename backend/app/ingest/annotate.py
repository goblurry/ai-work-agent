"""청크에 메타데이터 주석. 담당: 한준 + 현선

출처: hoBIT(arXiv:2608.26604) §2.1
  - LLM이 각 청크의 '적용 대상을 결정하는 속성'만 채우고 나머지는 null
  - 적용범위와 무관한 필드를 억지로 채우지 않는 것이 핵심

우리 추가분: validity(시간 축). 선행연구에 없다.
"""
from datetime import date

# schemas/chunk_metadata.json 과 1:1 대응


def annotate(chunk_text: str, source_meta: dict) -> dict:
    """chunk_metadata.json 형식의 dict 반환.

    규칙:
      1. 적용 범위를 결정하지 않는 필드는 반드시 None
      2. posted_date 를 effective_from 으로 대신 쓰지 않는다
      3. 적용 연도를 알 수 없으면 confirm_status = "적용범위_확인필요"
      4. 부칙·경과조치는 transitional 에 원문 보존
    """
    raise NotImplementedError


def pick_index(source_type: str) -> str:
    """static / dynamic 분리 (hoBIT §2.1). 규정=static, 공지=dynamic"""
    return "dynamic" if source_type == "공지" else "static"

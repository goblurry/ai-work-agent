"""학생의 적용 범위 검사. 본문의 개설 학과를 문서 소유 학과로 추정하지 않는다."""
import re
from urllib.parse import urlparse


def normalize_department(value):
    value = (value or "").replace(" ", "")
    if value.endswith("공학과"):
        return value[:-1]
    return re.sub(r"(학과|전공|과)$", "", value)


def department_aliases(value):
    base = normalize_department(value)
    return list(dict.fromkeys([value, base, base + "과", base + "학과", base + "전공"])) if base else []


def scope_exclusions(evidence, department=None, admission_year=None):
    applicability = evidence.get("applicability") or {}
    title = evidence.get("title") or ""
    reasons = []
    condition = applicability.get("department") or {}
    if department and condition.get("status") == "specified":
        if normalize_department(department) not in {normalize_department(v) for v in condition.get("values", [])}:
            reasons.append("학과 적용 조건 불일치")
    year = applicability.get("admission_year") or {}
    if admission_year and year.get("status") == "specified":
        if ((year.get("from") is not None and admission_year < year["from"]) or
            (year.get("to") is not None and admission_year > year["to"])):
            reasons.append("입학연도 조건 불일치")
    curriculum = evidence.get("source_type") == "교육과정" or bool(re.search(r"교과과정|교육과정|이수체계도", title))
    if curriculum and department and condition.get("status", "unknown") == "unknown":
        owner = re.search(r"교과과정안내[_ ]+(?:주전공[_ ]+)?([^_.\s]+)", title)
        # URL은 학과 사이트의 문서 소유자를 확인하는 보조 근거이다.
        path = urlparse(evidence.get("source_url") or "").path
        inferred = owner.group(1) if owner else None
        if not inferred:
            for segment, name in (("cse", "컴퓨터공학"), ("deptai", "인공지능"), ("statistics", "통계")):
                if segment in path.split("/"):
                    inferred = name
                    break
        if inferred and normalize_department(inferred) != normalize_department(department):
            reasons.append("다른 학과의 교육과정: " + inferred)
        elif not inferred:
            reasons.append("교육과정의 적용 학과 미확인")
    if curriculum and admission_year and year.get("status", "unknown") == "unknown":
        match = re.match(r"(20\d{2}|19\d{2})(?:학년도)?[ _]", title)
        # 제목에 명시된 연도만 사용. 본문의 게시일이나 연도를 입학연도로 삼지 않는다.
        if match and int(match.group(1)) != admission_year:
            reasons.append("다른 연도의 교육과정: " + match.group(1))
    return list(dict.fromkeys(reasons))


def qdrant_scope_filter(department=None, admission_year=None):
    """명시된 불일치를 검색 전에 제외. 미확인 교육과정은 조회 후 재검사한다."""
    excluded = []
    if department:
        excluded.append({"must": [{"key": "applicability.department.status", "match": {"value": "specified"}}],
                         "must_not": [{"key": "applicability.department.values", "match": {"any": department_aliases(department)}}]})
    if admission_year:
        for bound, operator in (("from", "gt"), ("to", "lt")):
            excluded.append({"must": [{"key": "applicability.admission_year.status", "match": {"value": "specified"}},
                                       {"key": "applicability.admission_year." + bound, "range": {operator: admission_year}}]})
    return {"must_not": excluded} if excluded else None

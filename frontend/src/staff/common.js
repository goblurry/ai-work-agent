// 담당자 화면 공통 상수와 표시 함수.
export const TYPE_LABEL = {
  graduation: "졸업 · 교과과정",
  course_recognition: "과목 이수 · 인정",
  leave_return: "휴학 · 복학",
  other: "기타 학사 문의",
};
export const STATUS_LABEL = {
  received: "접수 완료",
  processing: "처리 중",
  need_info: "정보 확인 필요",
  waiting_student: "학생 보완 대기",
  draft_ready: "초안 준비",
  needs_review: "담당자 검토 필요",
  completed: "답변 완료",
};
// 담당자가 다음에 할 일 기준으로 색을 나눈다.
export const STATUS_TONE = {
  received: "new",
  processing: "busy",
  needs_review: "urgent",
  need_info: "attention",
  waiting_student: "attention",
  draft_ready: "ready",
  completed: "done",
};
export const CHANNEL_LABEL = { web: "웹", phone: "전화" };
export const TRACK_OPTIONS = ["주전공", "복수전공", "부전공"];
export const STATUS_OPTIONS = ["재학", "휴학", "수료", "졸업"];
export const FIELD_LABEL = {
  department: "학과",
  target_department: "대상 학과",
  admission_year: "입학연도",
  major_track: "전공 구분",
  student_status: "학적 상태",
  target_term: "대상 학기",
  as_of: "판단 기준일",
  required_course_code: "필수 과목 학수번호",
  completed_course_code: "이수 과목 학수번호",
  procedure: "구분",
  application_status: "신청 상태",
  application_date: "신청일",
  receipt_date: "접수일",
};
// 상세 항목의 코드 값을 운영 화면 표기로 바꾼다.
const DETAIL_VALUE = {
  procedure: { leave: "휴학", return: "복학" },
  application_status: {
    not_applied: "신청 전",
    saved: "임시 저장",
    submitted: "제출 완료",
    received: "접수 확인",
    unknown: "확인 어려움",
  },
};
export function detailValue(key, value) {
  const map = DETAIL_VALUE[key];
  const text = String(value);
  return map?.[text] || text;
}
// 진행 중이거나 담당자 처리가 남은 상태.
export const isOpen = (s) => s !== "completed" && s !== "waiting_student";
export const isLocked = (s) => s === "completed";

const SEOUL = "Asia/Seoul";
const pad = (n) => String(n).padStart(2, "0");
/** Asia/Seoul 기준 YYYY-MM-DD */
export function seoulDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: SEOUL,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(d);
  const get = (t) => parts.find((p) => p.type === t)?.value;
  return `${get("year")}-${get("month")}-${get("day")}`;
}
export const todaySeoul = () => seoulDate(new Date());
export function dateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: SEOUL,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(d);
}
export function todayLabel() {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: SEOUL,
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
}
/** 목록 행에 보여 줄 질문 요약 */
export function summarize(text, limit = 120) {
  const value = (text || "").replace(/\s+/g, " ").trim();
  if (!value) return "내용 없음";
  return value.length > limit ? value.slice(0, limit) + "…" : value;
}
/** 학생 조건을 한 줄로 */
export function profileLine(profile) {
  if (!profile) return "";
  const parts = [
    profile.department,
    profile.admission_year ? `${profile.admission_year}학번` : "",
    profile.major_track,
    profile.student_status,
  ].filter(Boolean);
  return parts.join(" · ");
}
/** http/https 출처만 링크로 사용 */
export function safeUrl(url) {
  if (typeof url !== "string") return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:"
      ? url
      : null;
  } catch {
    return null;
  }
}
export const asList = (value) => (Array.isArray(value) ? value : []);

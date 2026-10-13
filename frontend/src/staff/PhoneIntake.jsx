import { useState } from "react";
import InquiryRow from "./InquiryRow";
import {
  STATUS_OPTIONS,
  TRACK_OPTIONS,
  TYPE_LABEL,
} from "./common";

const EMPTY = {
  inquiry_type: "graduation",
  question: "",
  department: "",
  target_department: "",
  admission_year: "",
  major_track: "",
  student_status: "",
  target_term: "",
  required_course_code: "",
  completed_course_code: "",
  procedure: "",
  application_status: "",
  application_date: "",
  receipt_date: "",
};
const PROCEDURE = [
  ["leave", "휴학"],
  ["return", "복학"],
];
const APPLICATION_STATUS = [
  ["not_applied", "신청 전"],
  ["saved", "임시 저장"],
  ["submitted", "제출 완료"],
  ["received", "접수 확인"],
  ["unknown", "확인 어려움"],
];
const code = (value) => {
  const v = (value || "").trim();
  return /^\d{5}$/.test(v) ? v : null;
};
const blank = (value) => {
  const v = (value || "").trim();
  return v === "" ? null : v;
};

function Field({ label, hint, full, children }) {
  return (
    <label className={"staff-field" + (full ? " full" : "")}>
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}

export default function PhoneIntake({ items, onOpen, onCreated, onReload, loading }) {
  const [form, setForm] = useState({ ...EMPTY });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // 저장은 됐지만 실행이 실패한 문의. 같은 ID 로 재시도하고 다시 등록하지 않는다.
  const [savedId, setSavedId] = useState(null);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const phone = items.filter((i) => i.channel === "phone");
  const type = form.inquiry_type;

  function payload() {
    const details = {};
    if (type === "course_recognition") {
      details.required_course_code = code(form.required_course_code);
      details.completed_course_code = code(form.completed_course_code);
    } else if (type === "leave_return") {
      details.procedure = blank(form.procedure);
      details.application_status = blank(form.application_status);
      details.application_date = blank(form.application_date);
      details.receipt_date = blank(form.receipt_date);
    }
    const year = parseInt(form.admission_year, 10);
    return {
      channel: "phone",
      inquiry_type: type,
      question: form.question.trim(),
      profile: {
        department: blank(form.department),
        target_department: blank(form.target_department),
        admission_year: Number.isFinite(year) ? year : null,
        major_track: blank(form.major_track),
        student_status: blank(form.student_status),
      },
      details,
      target_term: blank(form.target_term),
    };
  }

  async function submit(e) {
    e.preventDefault();
    if (busy) return;
    if (!form.question.trim()) {
      setError("문의 내용을 입력해 주세요.");
      return;
    }
    const year = form.admission_year.trim();
    if (year && !/^\d{4}$/.test(year)) {
      setError("입학연도는 네 자리 숫자로 입력해 주세요.");
      return;
    }
    setBusy(true);
    setError("");
    let id = savedId;
    try {
      if (!id) {
        const created = await onCreated.create(payload());
        id = created.inquiry_id;
        setSavedId(id);
      }
      await onCreated.run(id);
      setForm({ ...EMPTY });
      setSavedId(null);
      onCreated.open(id);
    } catch (err) {
      setError(
        id
          ? `문의는 저장되었지만 실행하지 못했습니다. ${err.message} 다시 시도하면 같은 문의로 실행합니다.`
          : err.message,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="staff-page-top staff-phone-heading">
        <div>
          <h1 className="staff-title">전화 문의</h1>
          <p className="staff-today">통화 중 확인한 내용을 입력해 접수합니다.</p>
        </div>
      </div>

      {error && <p className="staff-error">{error}</p>}

      <section className="staff-panel">
        <div className="staff-panel-head">
          <h2>문의 접수</h2>
          {savedId && <span className="staff-count">저장됨 · 실행 대기</span>}
        </div>
        <form className="staff-panel-body" onSubmit={submit}>
          <div className="staff-form-grid">
            <Field label="문의 유형">
              <select value={type} onChange={set("inquiry_type")}>
                {Object.entries(TYPE_LABEL).map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="학과">
              <input
                value={form.department}
                onChange={set("department")}
                placeholder="예: 컴퓨터공학과"
              />
            </Field>
            <Field label="입학연도">
              <input
                value={form.admission_year}
                onChange={set("admission_year")}
                inputMode="numeric"
                placeholder="예: 2022"
              />
            </Field>
            <Field label="전공 구분">
              <select value={form.major_track} onChange={set("major_track")}>
                <option value="">선택 안 함</option>
                {TRACK_OPTIONS.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="학적 상태">
              <select value={form.student_status} onChange={set("student_status")}>
                <option value="">선택 안 함</option>
                {STATUS_OPTIONS.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            {(type === "graduation" || type === "course_recognition") && (
              <Field label="대상 학과" hint="복수전공·부전공 대상이 있으면 입력">
                <input
                  value={form.target_department}
                  onChange={set("target_department")}
                />
              </Field>
            )}

            {type === "course_recognition" && (
              <>
                <Field label="필수 과목 학수번호" hint="숫자 다섯 자리">
                  <input
                    value={form.required_course_code}
                    onChange={set("required_course_code")}
                    inputMode="numeric"
                    placeholder="예: 20481"
                  />
                </Field>
                <Field label="이수 과목 학수번호" hint="숫자 다섯 자리">
                  <input
                    value={form.completed_course_code}
                    onChange={set("completed_course_code")}
                    inputMode="numeric"
                    placeholder="예: 39144"
                  />
                </Field>
              </>
            )}

            {type === "leave_return" && (
              <>
                <Field label="구분">
                  <select value={form.procedure} onChange={set("procedure")}>
                    <option value="">선택 안 함</option>
                    {PROCEDURE.map(([v, n]) => (
                      <option key={v} value={v}>
                        {n}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="신청 상태">
                  <select
                    value={form.application_status}
                    onChange={set("application_status")}
                  >
                    <option value="">선택 안 함</option>
                    {APPLICATION_STATUS.map(([v, n]) => (
                      <option key={v} value={v}>
                        {n}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="신청일">
                  <input
                    type="date"
                    value={form.application_date}
                    onChange={set("application_date")}
                  />
                </Field>
                <Field label="접수일">
                  <input
                    type="date"
                    value={form.receipt_date}
                    onChange={set("receipt_date")}
                  />
                </Field>
                <Field label="대상 학기" hint="휴학·복학 대상 학기. 예: 2026-2">
                  <input
                    value={form.target_term}
                    onChange={set("target_term")}
                    placeholder="2026-2"
                  />
                </Field>
              </>
            )}

            <Field label="문의 내용" full>
              <textarea
                rows={5}
                value={form.question}
                onChange={set("question")}
                placeholder="통화 중 확인한 질문을 그대로 입력합니다."
              />
            </Field>
          </div>

          <div className="staff-button-row" style={{ marginTop: 16 }}>
            <button type="submit" className="staff-action" disabled={busy}>
              {busy ? "처리 중" : savedId ? "다시 실행" : "저장하고 근거 확인"}
            </button>
            {savedId && (
              <button
                type="button"
                className="staff-text-button"
                onClick={() => onCreated.open(savedId)}
              >
                저장된 문의 열기
              </button>
            )}
          </div>
          <p className="staff-hint">
            접수 후 바로 근거를 확인합니다. 전화 문의는 학생 계정에 연결되지 않으며
            통화 처리 기록으로 남습니다.
          </p>
        </form>
      </section>

      <section className="staff-panel" style={{ marginTop: 18 }}>
        <div className="staff-panel-head">
          <h2>전화 문의 목록</h2>
          <span className="staff-count">{phone.length}건</span>
          <button type="button" className="staff-text-button" onClick={onReload}>
            새로고침
          </button>
        </div>
        {loading && !items.length ? (
          <p className="staff-loading" style={{ padding: "20px 18px" }}>
            불러오는 중입니다.
          </p>
        ) : phone.length ? (
          <ul className="staff-rows">
            {phone.map((item) => (
              <InquiryRow key={item.inquiry_id} item={item} onOpen={onOpen} />
            ))}
          </ul>
        ) : (
          <p className="staff-empty">등록된 전화 문의가 없습니다.</p>
        )}
      </section>
    </>
  );
}

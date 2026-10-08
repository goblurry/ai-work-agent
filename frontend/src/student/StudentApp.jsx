import { useEffect, useState } from "react";
import { request, post } from "../shared/api";
import Icon from "../shared/Icon";

const TYPES = [
  {
    id: "graduation",
    name: "졸업 · 교과과정",
    description: "졸업요건, 전공 이수, 교육과정",
    icon: "book",
  },
  {
    id: "course_recognition",
    name: "과목 이수 · 인정",
    description: "학수번호, 필수과목, 대체 인정",
    icon: "course",
  },
  {
    id: "leave_return",
    name: "휴학 · 복학",
    description: "신청 절차, 접수 상태, 학적 변동",
    icon: "leave",
  },
  {
    id: "other",
    name: "기타 학사 문의",
    description: "그 밖에 확인이 필요한 학사 사항",
    icon: "other",
  },
];
const EMPTY = {
  department: "",
  target_department: "",
  admission_year: "",
  major_track: "",
  student_status: "",
  target_term: "",
  procedure: "",
  application_status: "",
  application_date: "",
  receipt_date: "",
  required_course_code: "",
  completed_course_code: "",
  question: "",
};
const date = (value) =>
  value
    ? new Intl.DateTimeFormat("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(new Date(value))
    : "—";
function Field({ label, hint, children, wide }) {
  return (
    <label className={"field" + (wide ? " wide" : "")}>
      <span className="field-label">{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
function Status({ status }) {
  return (
    <span
      className={
        "status " +
        (status === "답변 완료"
          ? "done"
          : status === "추가 정보 요청"
            ? "attention"
            : "")
      }
    >
      {status}
    </span>
  );
}

export default function StudentApp() {
  const [user, setUser] = useState(null),
    [authLoading, setAuthLoading] = useState(true),
    [loginOpen, setLoginOpen] = useState(false),
    [login, setLogin] = useState({ username: "", password: "" }),
    [loginError, setLoginError] = useState(""),
    [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("new"),
    [type, setType] = useState("graduation"),
    [form, setForm] = useState({ ...EMPTY }),
    [error, setError] = useState(""),
    [items, setItems] = useState([]),
    [loading, setLoading] = useState(false),
    [selected, setSelected] = useState(null),
    [success, setSuccess] = useState(null),
    [supplement, setSupplement] = useState({}),
    [supplementError, setSupplementError] = useState("");
  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const setValue = (key) => (e) => update(key, e.target.value);
  async function loadList() {
    setLoading(true);
    setError("");
    try {
      setItems(await request("/students/inquiries"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    request("/auth/me")
      .then(setUser)
      .catch((e) => {
        if (e.status !== 401) setError(e.message);
      })
      .finally(() => setAuthLoading(false));
  }, []);
  useEffect(() => {
    if (user?.role === "student" && tab === "list") loadList();
  }, [user, tab]);
  useEffect(() => {
    if (!loginOpen && !selected && !success) return;
    const previous = document.activeElement;
    const frame = requestAnimationFrame(() =>
      document
        .querySelector(".modal [autofocus], .modal button, .modal input")
        ?.focus(),
    );
    const handler = (e) => {
      if (e.key === "Tab") {
        const nodes = [
          ...document.querySelectorAll(
            ".modal button:not(:disabled), .modal input, .modal select, .modal textarea",
          ),
        ];
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
      if (e.key === "Escape" && !busy) {
        setLoginOpen(false);
        setSelected(null);
        setSuccess(null);
      }
    };
    document.addEventListener("keydown", handler);
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = old;
      cancelAnimationFrame(frame);
      previous?.focus();
    };
  }, [loginOpen, selected, success, busy]);
  async function signIn(e) {
    e.preventDefault();
    setBusy(true);
    setLoginError("");
    try {
      const u = await post("/auth/login", login);
      setUser(u);
      setLoginOpen(false);
      setLogin({ username: "", password: "" });
      if (u.role !== "student")
        setError("학생 화면입니다. 학생 계정으로 로그인해 주세요.");
    } catch (e) {
      setLoginError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function signOut() {
    setBusy(true);
    try {
      await post("/auth/logout", {});
      setUser(null);
      setItems([]);
      setSelected(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function payload() {
    const details = {};
    if (type === "course_recognition") {
      details.required_course_code = form.required_course_code || null;
      details.completed_course_code = form.completed_course_code || null;
    }
    if (type === "leave_return") {
      details.procedure = form.procedure || null;
      details.application_status = form.application_status || null;
      details.application_date = ["submitted", "received"].includes(
        form.application_status,
      )
        ? form.application_date || null
        : null;
      details.receipt_date =
        form.application_status === "received"
          ? form.receipt_date || null
          : null;
    }
    const profile = {
      department: form.department.trim() || null,
      admission_year: form.admission_year ? Number(form.admission_year) : null,
      student_status: form.student_status || null,
    };
    if (["graduation", "course_recognition"].includes(type)) {
      profile.target_department = form.target_department.trim() || null;
      profile.major_track = form.major_track || null;
    }
    return {
      question: form.question.trim(),
      inquiry_type: type,
      profile,
      details,
      target_term: type === "leave_return" ? form.target_term || null : null,
    };
  }
  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!user) {
      setLoginOpen(true);
      return;
    }
    if (user.role !== "student") {
      setError("학생 계정으로 로그인해 주세요.");
      return;
    }
    setBusy(true);
    try {
      const item = await post("/students/inquiries", payload());
      setSuccess(item);
      setForm({
        ...EMPTY,
        department: form.department,
        admission_year: form.admission_year,
        student_status: form.student_status,
      });
    } catch (e) {
      setError(e.message);
      if (e.status === 401) {
        setUser(null);
        setLoginOpen(true);
      }
    } finally {
      setBusy(false);
    }
  }
  async function openInquiry(item) {
    setSupplement({});
    setSupplementError("");
    setLoading(true);
    setError("");
    try {
      setSelected(await request("/students/inquiries/" + item.receipt_no));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  async function sendSupplement(e) {
    e.preventDefault();
    setBusy(true);
    setSupplementError("");
    try {
      const data = { profile: {} };
      for (const [key, value] of Object.entries(supplement)) {
        if (!value) continue;
        if (["target_term", "as_of"].includes(key)) data[key] = value;
        else
          data.profile[key] = key === "admission_year" ? Number(value) : value;
      }
      const result = await post(
        "/students/inquiries/" + selected.receipt_no + "/supplement",
        data,
      );
      setSelected(result);
      setSupplement({});
    } catch (e) {
      setSupplementError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const input = (key, props = {}) => (
    <input value={form[key]} onChange={setValue(key)} {...props} />
  );
  const select = (key, options) => (
    <select value={form[key]} onChange={setValue(key)}>
      <option value="">선택해 주세요</option>
      {options.map((o) => (
        <option
          key={typeof o === "string" ? o : o[0]}
          value={typeof o === "string" ? o : o[0]}
        >
          {typeof o === "string" ? o : o[1]}
        </option>
      ))}
    </select>
  );
  return (
    <>
      <header className="site-header">
        <a
          className="wordmark"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setTab("new");
          }}
        >
          <span>
            <strong>학사 문의</strong>
            <small>ACADEMIC SUPPORT</small>
          </span>
        </a>
        <nav aria-label="주요 메뉴">
          <button
            className={tab === "new" ? "active" : ""}
            onClick={() => {
              setTab("new");
              setError("");
            }}
          >
            문의하기
          </button>
          <button
            className={tab === "list" ? "active" : ""}
            onClick={() => {
              setTab("list");
              setError("");
            }}
          >
            내 문의
          </button>
        </nav>
        <div className="account">
          {user ? (
            <>
              <span>
                <Icon name="user" size={16} />
                {user.username}
              </span>
              <button onClick={signOut} disabled={busy}>
                로그아웃
              </button>
            </>
          ) : (
            <button onClick={() => setLoginOpen(true)} disabled={authLoading}>
              {authLoading ? "확인 중…" : "로그인"}
              <Icon name="arrow" size={16} />
            </button>
          )}
        </div>
      </header>
      <main className="page">
        <div className="breadcrumb">
          학사 지원 <span>/</span> {tab === "new" ? "문의하기" : "내 문의"}
        </div>
        <div className="page-heading">
          <div>
            <h1>{tab === "new" ? "문의하기" : "내 문의"}</h1>
            <p>
              {tab === "new"
                ? "학사 관련 문의를 접수하고 담당자의 답변을 확인하세요."
                : "접수한 문의의 처리 상태와 담당자 답변을 확인하세요."}
            </p>
          </div>
          <div className="heading-process" aria-label="문의 처리 순서">
            <span>문의 접수</span>
            <Icon name="chevron" size={12} />
            <span>담당자 확인</span>
            <Icon name="chevron" size={12} />
            <span>답변 등록</span>
          </div>
        </div>
        {error && (
          <div className="error-banner" role="alert">
            {error}
            <button aria-label="안내 닫기" onClick={() => setError("")}>
              <Icon name="close" size={16} />
            </button>
          </div>
        )}
        {tab === "new" ? (
          <div className="workspace">
            <aside className="guide">
              <div className="guide-label">문의 접수 안내</div>
              <ol>
                <li>
                  <span>01</span>
                  <div>
                    문의 유형 선택
                    <small>문의에 맞는 항목을 안내해 드려요.</small>
                  </div>
                </li>
                <li>
                  <span>02</span>
                  <div>
                    학생 정보 입력
                    <small>적용되는 교육과정과 규정을 확인해요.</small>
                  </div>
                </li>
                <li>
                  <span>03</span>
                  <div>
                    문의 내용 작성
                    <small>확인하고 싶은 내용을 구체적으로 남겨요.</small>
                  </div>
                </li>
              </ol>
              <div className="guide-note">
                <Icon name="clock" />
                <strong>접수 후에는?</strong>
                <p>
                  내 문의에서 처리 상태를 확인할 수 있어요. 답변이 등록되면 같은
                  화면에서 확인해 주세요.
                </p>
              </div>
              <p className="privacy-note">
                입력한 정보는 문의 확인과 답변 작성에 사용됩니다. 주민등록번호나
                비밀번호는 적지 마세요.
              </p>
            </aside>
            <form className="inquiry-form" onSubmit={submit}>
              <section>
                <div className="section-title">
                  <span>01</span>
                  <h2>어떤 내용이 궁금하세요?</h2>
                </div>
                <div className="type-grid" role="group" aria-label="문의 유형">
                  {TYPES.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      aria-pressed={type === t.id}
                      className={
                        "type-option " + (type === t.id ? "selected" : "")
                      }
                      onClick={() => setType(t.id)}
                    >
                      <div className="type-top">
                        <Icon name={t.icon} />
                        <span className="selection-mark">
                          {type === t.id && <Icon name="check" size={12} />}
                        </span>
                      </div>
                      <strong>{t.name}</strong>
                      <small>{t.description}</small>
                    </button>
                  ))}
                </div>
              </section>
              <section>
                <div className="section-title">
                  <span>02</span>
                  <h2>학생 정보를 알려 주세요</h2>
                  <small>모르는 항목은 비워 두어도 괜찮아요.</small>
                </div>
                <div className="form-grid">
                  <Field label="소속 학과">
                    {input("department", {
                      placeholder: "예: 컴퓨터공학과",
                      maxLength: 100,
                    })}
                  </Field>
                  <Field label="입학연도">
                    {input("admission_year", {
                      type: "number",
                      placeholder: "예: 2022",
                      min: 1900,
                      max: 2100,
                    })}
                  </Field>
                  <Field label="학적 상태">
                    {select("student_status", [
                      "재학",
                      "휴학",
                      "수료",
                      "졸업예정",
                    ])}
                  </Field>
                  {["graduation", "course_recognition"].includes(type) && (
                    <>
                      <Field
                        label="확인할 전공 학과"
                        hint="소속 학과와 같으면 비워 두세요."
                      >
                        {input("target_department", {
                          placeholder: "예: 컴퓨터공학과",
                          maxLength: 100,
                        })}
                      </Field>
                      <Field label="전공 구분">
                        {select("major_track", [
                          "주전공",
                          "복수전공",
                          "부전공",
                        ])}
                      </Field>
                    </>
                  )}
                  {type === "course_recognition" && (
                    <div className="conditional-block wide">
                      <h3>확인할 과목 정보</h3>
                      <p>과목명이 같아도 학수번호가 다를 수 있어요.</p>
                      <div className="form-grid">
                        <Field label="지정 과목 학수번호">
                          {input("required_course_code", {
                            placeholder: "5자리 학수번호",
                            inputMode: "numeric",
                            pattern: "[0-9]{5}",
                            maxLength: 5,
                          })}
                        </Field>
                        <Field label="이수한 과목 학수번호">
                          {input("completed_course_code", {
                            placeholder: "5자리 학수번호",
                            inputMode: "numeric",
                            pattern: "[0-9]{5}",
                            maxLength: 5,
                          })}
                        </Field>
                      </div>
                    </div>
                  )}
                  {type === "leave_return" && (
                    <div className="conditional-block wide">
                      <h3>휴학 · 복학 신청 정보</h3>
                      <div className="form-grid">
                        <Field
                          label="휴학·복학 대상 학기"
                          hint="신청일이 아니라, 휴학하거나 복학할 학기를 선택하세요."
                        >
                          {select(
                            "target_term",
                            Array.from(
                              { length: 12 },
                              (_, i) => new Date().getFullYear() + 1 - i,
                            ).flatMap((year) =>
                              [2, 1].map((term) => [
                                `${year}-${term}`,
                                `${year}학년도 ${term}학기`,
                              ]),
                            ),
                          )}
                        </Field>
                        <Field label="신청 종류">
                          {select("procedure", [
                            ["leave", "휴학"],
                            ["return", "복학"],
                          ])}
                        </Field>
                        <Field label="현재 신청 상태">
                          {select("application_status", [
                            ["not_applied", "아직 신청하지 않음"],
                            ["saved", "임시저장"],
                            ["submitted", "신청서 제출"],
                            ["received", "접수 완료"],
                            ["unknown", "상태를 모름"],
                          ])}
                        </Field>
                        {["submitted", "received"].includes(
                          form.application_status,
                        ) && (
                          <Field label="신청일">
                            {input("application_date", { type: "date" })}
                          </Field>
                        )}
                        {form.application_status === "received" && (
                          <Field
                            label="실제 접수일"
                            hint="신청일과 접수일이 다르면 실제 접수일을 적어 주세요."
                          >
                            {input("receipt_date", { type: "date" })}
                          </Field>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </section>
              <section>
                <div className="section-title">
                  <span>03</span>
                  <h2>문의 내용을 남겨 주세요</h2>
                  <small className="required-label">필수</small>
                </div>
                <Field label="문의 내용" wide>
                  <textarea
                    required
                    minLength={2}
                    maxLength={20000}
                    value={form.question}
                    onChange={setValue("question")}
                    placeholder={
                      type === "course_recognition"
                        ? "과목명과 이수 상황, 확인하고 싶은 내용을 적어 주세요."
                        : "현재 상황과 확인하고 싶은 내용을 구체적으로 적어 주세요."
                    }
                    rows={6}
                  />
                </Field>
                <div className="textarea-footer">
                  <span>
                    관련된 과목명이나 신청 상황을 함께 적으면 확인에 도움이
                    돼요.
                  </span>
                  <span>{form.question.length.toLocaleString()} / 20,000</span>
                </div>
              </section>
              <div className="form-actions">
                <p>
                  접수한 문의와 답변은 <b>내 문의</b>에서 확인할 수 있어요.
                </p>
                <button
                  className="button primary"
                  disabled={busy || authLoading}
                  type="submit"
                >
                  {busy ? "접수 중…" : "문의 접수하기"}
                  <Icon name="arrow" size={18} />
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div className="list-surface">
            {!user ? (
              <div className="empty-state">
                <Icon name="user" size={28} />
                <h2>로그인 후 내 문의를 확인하세요</h2>
                <p>학생 계정으로 접수한 문의와 답변을 볼 수 있어요.</p>
                <button
                  className="button primary"
                  onClick={() => setLoginOpen(true)}
                >
                  로그인
                  <Icon name="arrow" size={16} />
                </button>
              </div>
            ) : user.role !== "student" ? (
              <div className="empty-state">
                <h2>학생 계정으로 로그인해 주세요</h2>
                <p>담당자 계정에서는 내 문의를 조회할 수 없습니다.</p>
              </div>
            ) : (
              <>
                <div className="list-toolbar">
                  <span>
                    전체 <b>{items.length}</b>건
                  </span>
                  <button
                    className="text-button"
                    disabled={loading}
                    onClick={loadList}
                  >
                    {loading ? "불러오는 중…" : "새로고침"}
                  </button>
                </div>
                {loading && items.length === 0 ? (
                  <p className="loading-note" role="status">
                    문의 목록을 불러오고 있어요.
                  </p>
                ) : items.length === 0 ? (
                  <div className="empty-state">
                    <Icon name="other" size={30} />
                    <h2>아직 접수한 문의가 없어요</h2>
                    <p>궁금한 학사 사항이 있다면 첫 문의를 남겨 보세요.</p>
                    <button
                      className="button primary"
                      onClick={() => setTab("new")}
                    >
                      문의하기
                      <Icon name="plus" size={16} />
                    </button>
                  </div>
                ) : (
                  <div className="inquiry-list">
                    {items.map((item) => (
                      <button
                        className="inquiry-row"
                        key={item.receipt_no}
                        onClick={() => openInquiry(item)}
                        disabled={loading}
                      >
                        <div className="row-type">
                          {TYPES.find((t) => t.id === item.inquiry_type)
                            ?.name || "학사 문의"}
                        </div>
                        <div className="row-question">
                          <strong>{item.question}</strong>
                          <small>
                            {date(item.created_at)}
                            <span>접수번호 {item.receipt_no.slice(0, 8)}</span>
                          </small>
                        </div>
                        <Status status={item.status} />
                        <Icon name="chevron" size={18} />
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </main>
      <footer className="site-footer">
        <span>ACADEMIC INQUIRY</span>
        <p>학사 문의 처리 시스템 · 수업 시연용 프로젝트</p>
      </footer>
      {loginOpen && (
        <div
          className="modal-backdrop"
          onClick={() => !busy && setLoginOpen(false)}
        >
          <section
            className="modal login-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="login-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close"
              aria-label="로그인 창 닫기"
              disabled={busy}
              onClick={() => setLoginOpen(false)}
            >
              <Icon name="close" />
            </button>
            <span className="eyebrow">STUDENT SIGN IN</span>
            <h2 id="login-title">학사 문의 로그인</h2>
            <p>문의 접수와 답변 확인을 위해 로그인해 주세요.</p>
            <form onSubmit={signIn}>
              <Field label="아이디">
                <input
                  autoFocus
                  required
                  autoComplete="username"
                  value={login.username}
                  onChange={(e) =>
                    setLogin((l) => ({ ...l, username: e.target.value }))
                  }
                />
              </Field>
              <Field label="비밀번호">
                <input
                  required
                  type="password"
                  autoComplete="current-password"
                  value={login.password}
                  onChange={(e) =>
                    setLogin((l) => ({ ...l, password: e.target.value }))
                  }
                />
              </Field>
              {loginError && (
                <p className="error-text" role="alert">
                  {loginError}
                </p>
              )}
              <button className="button primary full" disabled={busy}>
                {busy ? "로그인 중…" : "로그인"}
                <Icon name="arrow" size={18} />
              </button>
            </form>
            <p className="login-caption">
              학교 포털 통합 로그인은 연결되지 않은 시연용 화면입니다.
            </p>
          </section>
        </div>
      )}
      {success && (
        <div className="modal-backdrop">
          <section
            className="modal success-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="success-title"
          >
            <div className="success-icon">
              <Icon name="check" size={26} />
            </div>
            <span className="eyebrow">INQUIRY RECEIVED</span>
            <h2 id="success-title">문의가 접수되었어요</h2>
            <p>
              담당자가 내용을 확인한 후 답변을 등록합니다.
              <br />내 문의에서 처리 상태를 확인해 주세요.
            </p>
            <div className="receipt-box">
              <span>접수번호</span>
              <code>{success.receipt_no.slice(0, 8)}</code>
            </div>
            <button
              autoFocus
              className="button primary full"
              onClick={() => {
                setSuccess(null);
                setTab("list");
              }}
            >
              내 문의 확인하기
              <Icon name="arrow" size={18} />
            </button>
            <button className="text-button" onClick={() => setSuccess(null)}>
              다른 문의 남기기
            </button>
          </section>
        </div>
      )}
      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <section
            className="modal detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="detail-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              autoFocus
              className="modal-close"
              aria-label="문의 상세 닫기"
              onClick={() => setSelected(null)}
            >
              <Icon name="close" />
            </button>
            <span className="eyebrow">MY INQUIRY</span>
            <h2 id="detail-title">문의 상세</h2>
            <div className="detail-meta">
              <Status status={selected.status} />
              <span>{date(selected.created_at)}</span>
            </div>
            <h3>문의 내용</h3>
            <p className="preserve">{selected.question}</p>
            <div className="detail-conditions">
              {[
                selected.profile?.department,
                selected.profile?.admission_year &&
                  selected.profile.admission_year + "학번",
                selected.profile?.major_track,
                selected.profile?.student_status,
              ]
                .filter(Boolean)
                .map((x) => (
                  <span key={x}>{x}</span>
                ))}
            </div>
            <div className="answer-block">
              <div className="answer-heading">
                <Icon name="other" />
                <h3>담당자 답변</h3>
              </div>
              {selected.final_answer ? (
                <p className="preserve">{selected.final_answer}</p>
              ) : (
                <p className="waiting-note">
                  담당자가 문의를 확인하고 있어요.
                  <br />
                  답변이 등록되면 이곳에서 확인할 수 있습니다.
                </p>
              )}
            </div>
            {selected.information_request && (
              <div className="supplement-note">
                <h3>추가 정보 요청</h3>
                <p>{selected.information_request.message}</p>
                <form onSubmit={sendSupplement}>
                  <div className="form-grid">
                    {selected.information_request.fields.map((key) => (
                      <Field
                        key={key}
                        hint={
                          key === "target_term"
                            ? selected.inquiry_type === "leave_return"
                              ? "휴학하거나 복학할 학기를 알려 주세요. 예: 2026-2는 2026학년도 2학기입니다."
                              : "담당자가 요청한 안내에 맞춰 학기를 적어 주세요. 예: 2026-2는 2026학년도 2학기입니다."
                            : undefined
                        }
                        label={
                          {
                            department: "소속 학과",
                            admission_year: "입학연도",
                            student_status: "학적 상태",
                            major_track: "전공 구분",
                            target_term:
                              selected.inquiry_type === "leave_return"
                                ? "휴학·복학 대상 학기"
                                : "확인이 필요한 학기",
                            as_of: "판단 기준일",
                          }[key]
                        }
                      >
                        {["student_status", "major_track"].includes(key) ? (
                          <select
                            required
                            value={supplement[key] || ""}
                            onChange={(e) =>
                              setSupplement((v) => ({
                                ...v,
                                [key]: e.target.value,
                              }))
                            }
                          >
                            <option value="">선택해 주세요</option>
                            {(key === "major_track"
                              ? ["주전공", "복수전공", "부전공"]
                              : ["재학", "휴학", "수료", "졸업예정"]
                            ).map((x) => (
                              <option key={x}>{x}</option>
                            ))}
                          </select>
                        ) : (
                          <input
                            required
                            type={
                              key === "admission_year"
                                ? "number"
                                : key === "as_of"
                                  ? "date"
                                  : "text"
                            }
                            min={key === "admission_year" ? 1900 : undefined}
                            max={key === "admission_year" ? 2100 : undefined}
                            placeholder={
                              key === "target_term" ? "예: 2026-2" : undefined
                            }
                            value={supplement[key] || ""}
                            onChange={(e) =>
                              setSupplement((v) => ({
                                ...v,
                                [key]: e.target.value,
                              }))
                            }
                          />
                        )}
                      </Field>
                    ))}
                  </div>
                  {supplementError && (
                    <p className="error-text" role="alert">
                      {supplementError}
                    </p>
                  )}
                  <button
                    className="button primary"
                    disabled={busy}
                    style={{ marginTop: 18 }}
                  >
                    {busy ? "저장 중…" : "정보 보완하기"}
                    <Icon name="arrow" size={16} />
                  </button>
                </form>
              </div>
            )}
            <div className="detail-receipt">
              접수번호 <code>{selected.receipt_no}</code>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

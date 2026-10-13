import { useEffect, useRef, useState } from "react";
import { post, request } from "../shared/api";
import Icon from "../shared/Icon";
import {
  CHANNEL_LABEL,
  FIELD_LABEL,
  STATUS_LABEL,
  STATUS_TONE,
  TYPE_LABEL,
  asList,
  dateTime,
  detailValue,
  isLocked,
  safeUrl,
} from "./common";
import SupplementRequest from "./SupplementRequest";

const CHOICE_FALLBACK = { yes: "예", no: "아니요", check: "추가 확인 필요" };

function Evidence({ item }) {
  const url = safeUrl(item?.source_url);
  const bits = [item?.chunk_id, item?.verification].filter(
    (v) => typeof v === "string" && v,
  );
  return (
    <article className="staff-evidence">
      <div className="staff-evidence-top">
        <span className="staff-evidence-title">
          {item?.title || "제목 없음"}
        </span>
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer">
            원문
          </a>
        )}
      </div>
      {item?.text && <p className="staff-evidence-text">{item.text}</p>}
      {bits.length > 0 && <p className="staff-evidence-meta">{bits.join(" · ")}</p>}
    </article>
  );
}

function SupportSummary({ summary }) {
  if (!summary) return null;
  const courses = asList(summary.confirmed_courses);
  const unverified = asList(summary.unverified_items);
  const sources = asList(summary.sources);
  if (!courses.length && !unverified.length && !sources.length) return null;
  return (
    <section className="staff-section">
      <h3>확인된 정보</h3>
      {courses.length > 0 && (
        <ul className="staff-rows" style={{ border: "1px solid var(--line)", borderRadius: 6 }}>
          {courses.map((c, i) => (
            <li key={c?.course_code || i} style={{ padding: "11px 14px" }}>
              <div className="staff-row-top" style={{ marginBottom: 2 }}>
                <span className="staff-row-type">
                  {c?.course_name || "과목명 미상"}
                </span>
                {c?.course_code && <span className="staff-chip">{c.course_code}</span>}
                {c?.required_flag && <span className="staff-chip phone">필수</span>}
              </div>
              <div className="staff-row-meta">
                {c?.category && <span>{c.category}</span>}
                {c?.credits != null && <span>{c.credits}학점</span>}
                {c?.major_track && <span>{c.major_track}</span>}
                {c?.page != null && <span>{c.page}쪽</span>}
              </div>
            </li>
          ))}
        </ul>
      )}
      {unverified.length > 0 && (
        <div className="staff-note warn" style={{ marginTop: 10 }}>
          <strong>확인되지 않은 항목</strong>
          <ul>
            {unverified.map((u, i) => (
              <li key={i}>{typeof u === "string" ? u : JSON.stringify(u)}</li>
            ))}
          </ul>
          <p className="staff-hint" style={{ marginTop: 6 }}>
            자료에서 확인되지 않았다는 뜻이며 불가 판정이 아닙니다.
          </p>
        </div>
      )}
      {sources.length > 0 && (
        <p className="staff-evidence-meta" style={{ marginTop: 8 }}>
          출처 ·{" "}
          {sources
            .map((s) => (typeof s === "string" ? s : s?.title || s?.file || ""))
            .filter(Boolean)
            .join(", ")}
        </p>
      )}
    </section>
  );
}

export default function InquiryDetail({ inquiryId, onBack, onChanged }) {
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [action, setAction] = useState("");
  const [choice, setChoice] = useState("");
  const [memo, setMemo] = useState("");
  const [judgement, setJudgement] = useState("");
  const [draft, setDraft] = useState("");
  const [dirty, setDirty] = useState(false);
  const [supplementOpen, setSupplementOpen] = useState(false);
  const loadedFor = useRef(null);

  function apply(next) {
    setItem(next);
    // 서버 초안은 담당자가 편집하지 않은 동안에만 반영한다.
    setDraft((current) => (dirty ? current : next?.draft || ""));
    onChanged?.();
  }

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    request(`/inquiries/${inquiryId}`)
      .then((data) => {
        if (!alive) return;
        setItem(data);
        if (loadedFor.current !== inquiryId) {
          loadedFor.current = inquiryId;
          setDraft(data?.draft || "");
          setChoice(data?.staff_choice || "");
          setMemo(data?.staff_memo || "");
          setJudgement(data?.staff_decision || "");
          setDirty(false);
        }
      })
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [inquiryId]);

  async function call(name, fn) {
    if (action) return;
    setAction(name);
    setError("");
    try {
      apply(await fn());
    } catch (e) {
      setError(e.message);
    } finally {
      setAction("");
    }
  }

  if (loading && !item) return <p className="staff-loading">불러오는 중입니다.</p>;
  if (!item)
    return (
      <>
        <button type="button" className="staff-back" onClick={onBack}>
          <Icon name="arrow" size={15} style={{ transform: "rotate(180deg)" }} />
          목록으로
        </button>
        {error && <p className="staff-error">{error}</p>}
      </>
    );

  const locked = isLocked(item.status);
  const question = item.support_summary?.staff_question;
  const options = asList(question?.options);
  const labels = asList(question?.labels);
  const evidence = asList(item.evidence);
  const missing = asList(item.missing_fields);
  const warnings = asList(item.warnings);
  const next = asList(item.next_actions);
  const trace = asList(item.trace);
  const profile = item.profile || {};
  const details = item.details || {};
  // 학생 보완 대기 중에는 실행하지 않고, 처리 중에는 강제 재실행 버튼을 두지 않는다.
  const canRun =
    !locked &&
    item.status !== "waiting_student" &&
    item.status !== "processing";
  const studentReply = item.draft_kind === "student_reply";

  // 접수번호는 학생이 조회할 때 쓰는 번호라 웹 문의에만 표시한다.
  const metaRows = [
    ["접수 경로", CHANNEL_LABEL[item.channel] || item.channel],
    ["문의 유형", TYPE_LABEL[item.inquiry_type] || item.inquiry_type],
    item.channel === "web" && item.receipt_no
      ? ["접수번호", item.receipt_no]
      : null,
    ["접수 시각", dateTime(item.created_at)],
    ["학과", profile.department],
    ["입학연도", profile.admission_year],
    ["전공 구분", profile.major_track],
    ["학적 상태", profile.student_status],
    ["대상 학과", profile.target_department],
    ["대상 학기", item.target_term],
  ].filter((row) => row && row[1] != null && row[1] !== "");

  return (
    <>
      <button type="button" className="staff-back" onClick={onBack}>
        <Icon name="arrow" size={15} style={{ transform: "rotate(180deg)" }} />
        목록으로
      </button>

      <div className="staff-page-top">
        <div>
          <h1 className="staff-title">문의 처리</h1>
          <p className="staff-today">
            {TYPE_LABEL[item.inquiry_type] || "학사 문의"}
          </p>
        </div>
        <span
          className={"staff-status " + (STATUS_TONE[item.status] || "")}
          style={{ marginLeft: "auto", fontSize: 12, padding: "5px 12px" }}
        >
          {STATUS_LABEL[item.status] || item.status}
        </span>
      </div>

      {error && <p className="staff-error">{error}</p>}

      <section className="staff-panel">
        <div className="staff-panel-head">
          <h2>학생 문의</h2>
        </div>
        <div className="staff-panel-body">
          <p className="staff-question-text">{item.question}</p>
          <dl className="staff-meta-grid">
            {metaRows.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{String(v)}</dd>
              </div>
            ))}
            {Object.entries(details).map(([k, v]) =>
              v == null || v === "" ? null : (
                <div key={k}>
                  <dt>{FIELD_LABEL[k] || k}</dt>
                  <dd>{detailValue(k, v)}</dd>
                </div>
              ),
            )}
          </dl>
        </div>
      </section>

      {(missing.length > 0 || item.unresolved_reason || warnings.length > 0) && (
        <section className="staff-panel" style={{ marginTop: 18 }}>
          <div className="staff-panel-head">
            <h2>확인이 필요한 사항</h2>
          </div>
          <div className="staff-panel-body">
            {missing.length > 0 && (
              <div className="staff-note warn">
                <strong>부족한 학생 조건</strong>
                <ul>
                  {missing.map((f) => (
                    <li key={f}>{FIELD_LABEL[f] || f}</li>
                  ))}
                </ul>
              </div>
            )}
            {item.unresolved_reason && (
              <div className="staff-note warn" style={{ marginTop: 10 }}>
                {item.unresolved_reason}
              </div>
            )}
            {warnings.length > 0 && (
              <div className="staff-note" style={{ marginTop: 10 }}>
                <strong>주의</strong>
                <ul>
                  {warnings.map((w, i) => (
                    <li key={i}>{typeof w === "string" ? w : JSON.stringify(w)}</li>
                  ))}
                </ul>
              </div>
            )}
            {next.length > 0 && (
              <div className="staff-note" style={{ marginTop: 10 }}>
                <strong>다음 작업</strong>
                <ul>
                  {next.map((n, i) => (
                    <li key={i}>{typeof n === "string" ? n : JSON.stringify(n)}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      <section className="staff-panel" style={{ marginTop: 18 }}>
        <div className="staff-panel-head">
          <h2>근거</h2>
          {evidence.length > 0 && (
            <span className="staff-count">{evidence.length}건</span>
          )}
        </div>
        <div className="staff-panel-body">
          {evidence.length ? (
            evidence.map((e, i) => <Evidence key={e?.chunk_id || i} item={e} />)
          ) : (
            <p className="staff-hint" style={{ margin: 0 }}>
              아직 근거를 확인하지 않았습니다. Agent를 실행하면 관련 자료를 찾습니다.
            </p>
          )}
          <SupportSummary summary={item.support_summary} />
          <div className="staff-button-row" style={{ marginTop: 14 }}>
            <button
              type="button"
              className="staff-action"
              disabled={!canRun || !!action}
              onClick={() => call("run", () => post(`/inquiries/${item.inquiry_id}/run`, {}))}
            >
              {action === "run" ? "실행 중" : evidence.length ? "다시 실행" : "Agent 실행"}
            </button>
            {item.channel === "web" && !locked && (
              <button
                type="button"
                className="staff-action ghost"
                onClick={() => setSupplementOpen((v) => !v)}
              >
                정보 보완 요청
              </button>
            )}
          </div>
          {item.status === "waiting_student" && (
            <p className="staff-hint">
              학생의 보완을 기다리는 중입니다. 보완이 등록되면 다시 실행할 수 있습니다.
            </p>
          )}
          {supplementOpen && !locked && (
            <SupplementRequest
              inquiryId={item.inquiry_id}
              missing={missing}
              onDone={(next) => {
                setSupplementOpen(false);
                apply(next);
              }}
            />
          )}
          {item.information_request?.message && (
            <div className="staff-note" style={{ marginTop: 10 }}>
              <strong>보낸 보완 요청</strong>
              <p style={{ margin: "4px 0 0", whiteSpace: "pre-wrap" }}>
                {item.information_request.message}
              </p>
            </div>
          )}
        </div>
      </section>

      {!locked && (
        <section className="staff-panel" style={{ marginTop: 18 }}>
          <div className="staff-panel-head">
            <h2>담당자 판단</h2>
          </div>
          <div className="staff-panel-body">
            {question?.text ? (
              <>
                <p className="staff-question-text" style={{ fontSize: 13.5 }}>
                  {question.text}
                </p>
                <div className="staff-choices">
                  {(options.length ? options : ["yes", "no", "check"]).map((o, i) => (
                    <button
                      key={o}
                      type="button"
                      className="staff-choice"
                      aria-pressed={choice === o}
                      onClick={() => setChoice(o)}
                    >
                      {labels[i] || CHOICE_FALLBACK[o] || o}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <label className="staff-field" style={{ marginBottom: 12 }}>
                <span>판단 내용</span>
                <textarea
                  rows={3}
                  value={judgement}
                  onChange={(e) => setJudgement(e.target.value)}
                  placeholder="담당자가 확인한 안내 방향을 적습니다."
                />
              </label>
            )}
            <label className="staff-field">
              <span>메모</span>
              <textarea
                rows={3}
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                placeholder="추가 안내 사항이나 판단 근거"
              />
            </label>
            <div className="staff-button-row" style={{ marginTop: 14 }}>
              <button
                type="button"
                className="staff-action"
                disabled={
                  !!action ||
                  !evidence.length ||
                  missing.length > 0 ||
                  (question?.text ? !choice : !judgement.trim())
                }
                onClick={() => {
                  if (
                    dirty &&
                    draft.trim() &&
                    !window.confirm(
                      "편집한 초안이 새로 작성한 내용으로 바뀝니다. 계속할까요?",
                    )
                  )
                    return;
                  setDirty(false);
                  call("compose", () =>
                    post(
                      `/inquiries/${item.inquiry_id}/compose`,
                      question?.text ? { choice, memo } : { text: judgement, memo },
                    ),
                  );
                }}
              >
                {action === "compose"
                  ? "작성 중"
                  : studentReply
                    ? "답변 초안 다시 작성"
                    : "답변 초안 작성"}
              </button>
            </div>
            {!evidence.length ? (
              <p className="staff-hint">
                근거를 먼저 확인해야 초안을 작성할 수 있습니다.
              </p>
            ) : missing.length > 0 ? (
              <p className="staff-hint">
                부족한 학생 조건이 남아 있어 초안을 작성할 수 없습니다. 조건을
                보완해 다시 실행하거나, 직접 답변을 작성해 저장해 주세요.
              </p>
            ) : null}
          </div>
        </section>
      )}

      {(item.draft || locked) && (
        <section className="staff-panel" style={{ marginTop: 18 }}>
          <div className="staff-panel-head">
            <h2>{locked ? "최종 답변" : "학생에게 보낼 답변"}</h2>
          </div>
          <div className="staff-panel-body">
            {locked ? (
              <>
                <div className="staff-final">{item.final_answer || "—"}</div>
                <p className="staff-hint">
                  {dateTime(item.completed_at)} 등록 · 학생이 내 문의에서 확인할 수
                  있습니다.
                </p>
              </>
            ) : (
              <>
                <div className="staff-draft-label">
                  <span className="staff-kind">
                    {studentReply ? "학생 답변 초안" : "담당자용 근거 요약"}
                  </span>
                  {!studentReply && item.draft && (
                    <span className="staff-hint" style={{ margin: 0 }}>
                      그대로 등록하지 말고 학생 답변으로 다듬어 주세요.
                    </span>
                  )}
                </div>
                <label className="staff-field">
                  <textarea
                    rows={10}
                    value={draft}
                    onChange={(e) => {
                      setDraft(e.target.value);
                      setDirty(true);
                    }}
                  />
                </label>
                <div className="staff-button-row" style={{ marginTop: 12 }}>
                  <button
                    type="button"
                    className="staff-action ghost"
                    disabled={!!action || !draft.trim()}
                    onClick={() =>
                      call("edit", async () => {
                        const next = await post(
                          `/inquiries/${item.inquiry_id}/review`,
                          { action: "edit", text: draft },
                        );
                        setDirty(false);
                        return next;
                      })
                    }
                  >
                    {action === "edit" ? "저장 중" : "초안 저장"}
                  </button>
                  <button
                    type="button"
                    className="staff-action"
                    disabled={!!action || !draft.trim()}
                    onClick={() => {
                      if (
                        !window.confirm(
                          "이 내용을 최종 답변으로 등록합니다. 등록하면 학생에게 공개되며 되돌릴 수 없습니다.",
                        )
                      )
                        return;
                      call("complete", async () => {
                        const next = await post(
                          `/inquiries/${item.inquiry_id}/review`,
                          { action: "complete", text: draft },
                        );
                        setDirty(false);
                        return next;
                      });
                    }}
                  >
                    {action === "complete" ? "등록 중" : "답변 등록"}
                  </button>
                </div>
                <p className="staff-hint">
                  초안 저장은 학생에게 공개되지 않습니다. 답변 등록을 해야 학생이
                  확인할 수 있습니다.
                </p>
              </>
            )}
          </div>
        </section>
      )}

      {trace.length > 0 && (
        <details className="staff-trace" style={{ marginTop: 18 }}>
          <summary>실행 기록 {trace.length}단계</summary>
          <ol>
            {trace.map((t, i) => (
              <li key={i}>
                <span>{t?.step || "단계"}</span>
                <span>{t?.detail || ""}</span>
              </li>
            ))}
          </ol>
        </details>
      )}
    </>
  );
}

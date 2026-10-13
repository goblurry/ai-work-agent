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
      {item?.page != null && <span className="staff-evidence-meta">{item.page}쪽</span>}
    </article>
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
  const sources = evidence.filter((source, index, all) =>
    all.findIndex((other) => other?.title === source?.title &&
      other?.source_url === source?.source_url && other?.page === source?.page) === index,
  );
  const missing = asList(item.missing_fields);
  const warnings = asList(item.warnings);
  const next = asList(item.next_actions);
  const profile = item.profile || {};
  const details = item.details || {};
  const canRun = !locked && item.status !== "waiting_student";
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

  const groups = [
    { title: "학생 정보", rows: metaRows.filter(([label]) => ["학과", "입학연도", "전공 구분", "학적 상태"].includes(label)) },
    { title: "문의 조건", rows: [
      ...metaRows.filter(([label]) => ["대상 학과", "대상 학기"].includes(label)),
      ...Object.entries(details).filter(([, value]) => value != null && value !== "")
        .map(([key, value]) => [FIELD_LABEL[key] || key, detailValue(key, value)]),
    ] },
  ].filter((group) => group.rows.length);
  const receiptRows = metaRows.filter(([label]) => ["접수 경로", "문의 유형", "접수번호", "접수 시각"].includes(label));

  return (
    <>
      <button type="button" className="staff-back" onClick={onBack}>
        <Icon name="arrow" size={15} style={{ transform: "rotate(180deg)" }} />
        목록으로
      </button>

      <div className="staff-page-top staff-detail-heading">
        <div>
          <h1 className="staff-title">문의 처리</h1>
          <p className="staff-today">
            {TYPE_LABEL[item.inquiry_type] || "학사 문의"}
          </p>
        </div>
        <span
          className={"staff-status " + (STATUS_TONE[item.status] || "")}
          style={{ marginLeft: "auto", fontSize: "var(--staff-meta-size)", padding: "5px 12px" }}
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
          <div className="staff-receipt-meta">
            {receiptRows.map(([label, value]) => (
              <span key={label}><span>{label}</span> {String(value)}</span>
            ))}
          </div>
          <div className="staff-selected-groups">
            {groups.map((group) => (
              <section className="staff-selected-group" key={group.title}>
                <h3>{group.title}</h3>
                <dl className="staff-selected-grid">
                  {group.rows.map(([label, value]) => (
                    <div key={label}><dt>{label}</dt><dd>{String(value)}</dd></div>
                  ))}
                </dl>
              </section>
            ))}
          </div>
        </div>
      </section>

      {locked && (
        <section className="staff-panel staff-answer-panel" style={{ marginTop: 18 }}>
          <div className="staff-panel-head">
            <h2>최종 답변</h2>
            <span className="staff-count">{dateTime(item.completed_at)} 등록</span>
          </div>
          <div className="staff-panel-body">
            <div className="staff-final">{item.final_answer || "등록된 답변이 없습니다."}</div>
          </div>
        </section>
      )}

      {evidence.length > 0 && (
        <details className="staff-sources" style={{ marginTop: 18 }}>
          <summary>참고한 근거 자료 <span className="staff-count">{sources.length}건</span></summary>
          <div className="staff-sources-body">
            {sources.map((source, index) => <Evidence key={index} item={source} />)}
          </div>
        </details>
      )}

      {!locked && (missing.length > 0 || item.unresolved_reason || warnings.length > 0) && (
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

      {!locked && <section className="staff-panel" style={{ marginTop: 18 }}>
        <div className="staff-panel-head">
          <h2>문의 검토</h2>
        </div>
        <div className="staff-panel-body">
          <div className="staff-button-row" style={{ marginTop: 14 }}>
            <button
              type="button"
              className="staff-action"
              disabled={!canRun || !!action}
              onClick={() => call("run", () => post(`/inquiries/${item.inquiry_id}/run`, {}))}
            >
              {action === "run" ? "실행 중" : evidence.length ? "근거 다시 찾기" : "근거 찾기"}
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
      </section>}

      {!locked && (
        <section className="staff-panel" style={{ marginTop: 18 }}>
          <div className="staff-panel-head">
            <h2>담당자 판단</h2>
          </div>
          <div className="staff-panel-body">
            {question?.text ? (
              <>
                <p className="staff-question-text" >
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
            {!evidence.length && (
              <p className="staff-hint">
                근거를 먼저 확인해야 초안을 작성할 수 있습니다.
              </p>
            )}
          </div>
        </section>
      )}

      {!locked && item.draft && (
        <section className="staff-panel" style={{ marginTop: 18 }}>
          <div className="staff-panel-head">
            <h2>학생에게 보낼 답변</h2>
          </div>
          <div className="staff-panel-body">
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
          </div>
        </section>
      )}


    </>
  );
}

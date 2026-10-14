import Icon from "../shared/Icon";
import InquiryRow from "./InquiryRow";
import { seoulDate, summarize, todaySeoul, dateTime } from "./common";

export default function Dashboard({ items, loading, onOpen, onReload, onPhone }) {
  const today = todaySeoul();
  // 미처리는 completed·waiting_student 를 제외한 전체.
  const pending = items
    .filter((i) => i.status !== "completed" && i.status !== "waiting_student")
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  const waiting = items.filter((i) => i.status === "waiting_student");
  const doneToday = items.filter(
    (i) => i.status === "completed" && seoulDate(i.completed_at) === today,
  );
  const newToday = items.filter((i) => seoulDate(i.created_at) === today);
  const recent = items
    .filter((i) => i.status === "completed" && i.completed_at)
    .sort((a, b) => new Date(b.completed_at) - new Date(a.completed_at))
    .slice(0, 5);

  const counts = [
    ["미처리", pending.length, "other"],
    ["학생 보완 대기", waiting.length, "clock"],
    ["오늘 답변 완료", doneToday.length, "check"],
    ["오늘 접수", newToday.length, "plus"],
  ];

  return (
    <div className="staff-dashboard">
      <div className="staff-page-top">
        <div>
          <h1 className="staff-title">{today.replaceAll("-", ".")}</h1>
          <p className="staff-today">오늘의 업무</p>
        </div>
        <button type="button" className="staff-action" onClick={onPhone}>
          전화 문의 접수
        </button>
      </div>

      <dl className="staff-summary">
        {counts.map(([label, value, icon], i) => (
          <div key={label} className={i === 0 && value > 0 ? "highlight" : undefined}>
            <dt><span>{label}</span><Icon name={icon} size={18} /></dt>
            <dd className={value === 0 ? "zero" : ""}>{value}</dd>
          </div>
        ))}
      </dl>

      <div className="staff-split">
        <section className="staff-panel">
          <div className="staff-panel-head">
            <h2>답변을 기다리는 문의</h2>
            <span className="staff-count">{pending.length}건</span>
            <button type="button" className="staff-text-button" onClick={onReload}>
              새로고침
            </button>
          </div>
          {loading && !items.length ? (
            <p className="staff-loading" style={{ padding: "20px 18px" }}>
              불러오는 중입니다.
            </p>
          ) : pending.length ? (
            <ul className="staff-rows">
              {pending.map((item) => (
                <InquiryRow key={item.inquiry_id} item={item} onOpen={onOpen} showChannel />
              ))}
            </ul>
          ) : (
            <div className="staff-dashboard-empty">
              <span className="staff-dashboard-check"><Icon name="check" size={28} /></span>
              <strong>답변을 기다리는 문의가 없습니다</strong>
              <p>새로 접수되는 문의는 이곳에서 확인할 수 있습니다.</p>
            </div>
          )}
        </section>

        <section className="staff-panel">
          <div className="staff-panel-head">
            <h2>최근 등록한 답변</h2>
          </div>
          {recent.length ? (
            <ul className="staff-recent">
              {recent.map((item) => (
                <li key={item.inquiry_id}>
                  <button
                    type="button"
                    className="staff-recent-open"
                    onClick={() => onOpen(item.inquiry_id)}
                    aria-label={`등록한 답변 보기: ${summarize(item.question, 48)}`}
                  >
                    <span className="staff-recent-content">
                      <span className="staff-recent-q">{item.question}</span>
                      <span className="staff-recent-time">{dateTime(item.completed_at)} 등록</span>
                    </span>
                    <span className="staff-recent-arrow" aria-hidden="true">→</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="staff-empty">등록한 답변이 아직 없습니다.</p>
          )}
        </section>
      </div>
    </div>
  );
}

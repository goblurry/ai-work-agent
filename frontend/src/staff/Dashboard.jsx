import { useState } from "react";
import Icon from "../shared/Icon";
import InquiryRow from "./InquiryRow";
import { seoulDate, summarize, todaySeoul, dateTime } from "./common";

export default function Dashboard({ items, loading, onOpen, onReload, onPhone }) {
  const today = todaySeoul();
  const [statusFilter,setStatusFilter] = useState("all");
  const [channelFilter,setChannelFilter] = useState("all");
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

  const outstanding = items.filter(i=>i.status !== "completed").sort((a,b)=>new Date(a.created_at)-new Date(b.created_at));
  const matchesStatus = (item,filter)=>filter === "all" || (filter === "review" ? ["needs_review","need_info","draft_ready"].includes(item.status) : item.status === filter);
  const filtered = outstanding.filter(item=>matchesStatus(item,statusFilter) && (channelFilter === "all" || item.channel === channelFilter));
  const filters = [["all","전체"],["received","접수 완료"],["review","검토 필요"],["waiting_student","학생 보완 대기"],["processing","처리 중"]];
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
        <button type="button" className="staff-action staff-phone-action" onClick={onPhone}>
          <Icon name="phone" size={16} /> 전화 문의 접수
        </button>
      </div>

      <dl className="staff-summary">
        {counts.map(([label, value, icon]) => (
          <div key={label} className={label === "오늘 접수" ? "today-highlight" : ""}>
            <dt><span>{label}</span><Icon name={icon} size={18} /></dt>
            <dd className={value === 0 ? "zero" : ""}>{value}</dd>
          </div>
        ))}
      </dl>

      <div className="staff-split">
        <section className="staff-panel">
          <div className="staff-panel-head">
            <h2>답변을 기다리는 문의</h2>
            <span className="staff-count">{filtered.length}건</span>
            <button type="button" className="staff-text-button" onClick={onReload}>
              새로고침
            </button>
          </div>
          <div className="staff-inbox-filters">
            <div className="staff-filter-group" role="group" aria-label="문의 상태 필터">
              {filters.map(([id,label])=><button key={id} type="button" aria-pressed={statusFilter === id} onClick={()=>setStatusFilter(id)}>{label}<span>{outstanding.filter(item=>matchesStatus(item,id)).length}</span></button>)}
            </div>
            <div className="staff-channel-filter" role="group" aria-label="접수 경로 필터">
              {[["all","전체 경로"],["web","웹"],["phone","전화"]].map(([id,label])=><button key={id} type="button" aria-pressed={channelFilter === id} onClick={()=>setChannelFilter(id)}>{label}</button>)}
            </div>
          </div>
          {loading && !items.length ? (
            <p className="staff-loading" style={{ padding: "20px 18px" }}>
              불러오는 중입니다.
            </p>
          ) : filtered.length ? (
            <ul className="staff-rows">
              {filtered.map((item) => (
                <InquiryRow key={item.inquiry_id} item={item} onOpen={onOpen} showChannel />
              ))}
            </ul>
          ) : (
            <div className="staff-dashboard-empty">
              <span className="staff-dashboard-check"><Icon name="check" size={28} /></span>
              <strong>{outstanding.length ? "필터에 해당하는 문의가 없습니다" : "답변을 기다리는 문의가 없습니다"}</strong>
              <p>{outstanding.length ? "다른 상태나 접수 경로를 선택해 주세요." : "새로 접수되는 문의는 이곳에서 확인할 수 있습니다."}</p>
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

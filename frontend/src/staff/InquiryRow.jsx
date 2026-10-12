import {
  CHANNEL_LABEL,
  STATUS_LABEL,
  STATUS_TONE,
  TYPE_LABEL,
  dateTime,
  profileLine,
  summarize,
} from "./common";

export default function InquiryRow({ item, onOpen }) {
  const meta = profileLine(item.profile);
  return (
    <li>
      <button
        type="button"
        className="staff-row"
        onClick={() => onOpen(item.inquiry_id)}
      >
        <div className="staff-row-top">
          <span className={"staff-chip" + (item.channel === "phone" ? " phone" : "")}>
            {CHANNEL_LABEL[item.channel] || item.channel}
          </span>
          <span className="staff-row-type">
            {TYPE_LABEL[item.inquiry_type] || "학사 문의"}
          </span>
          <span className={"staff-status " + (STATUS_TONE[item.status] || "")}>
            {STATUS_LABEL[item.status] || item.status}
          </span>
          <span className="staff-row-time">{dateTime(item.created_at)}</span>
        </div>
        <p className="staff-row-question">{summarize(item.question)}</p>
        <div className="staff-row-meta">
          {meta && <span>{meta}</span>}
          {item.channel === "web" && item.receipt_no && (
            <span>접수번호 {item.receipt_no}</span>
          )}
        </div>
      </button>
    </li>
  );
}

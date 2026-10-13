import {
  CHANNEL_LABEL,
  STATUS_LABEL,
  STATUS_TONE,
  TYPE_LABEL,
  dateTime,
  profileLine,
} from "./common";

export default function InquiryRow({ item, onOpen, showChannel = false }) {
  const meta = profileLine(item.profile);
  return (
    <li>
      <button
        type="button"
        className="staff-row"
        onClick={() => onOpen(item.inquiry_id)}
      >
        <span className="staff-inquiry-content">
          <span className="staff-inquiry-title">{item.question.replace(/\s+/g," ")}</span>
          <span className="staff-row-meta">
            {showChannel && <span className={"staff-channel-badge " + item.channel}>{CHANNEL_LABEL[item.channel] || item.channel}</span>}
            <span className="staff-type-badge">{TYPE_LABEL[item.inquiry_type] || "학사 문의"}</span>
            {meta && <span>{meta}</span>}
            {item.channel === "web" && item.receipt_no && (
              <span className="staff-receipt-short">접수번호 {item.receipt_no.slice(0,8)}</span>
            )}
          </span>
        </span>
        <span className="staff-inquiry-end">
          <span className={"staff-status " + (STATUS_TONE[item.status] || "")}>
            {STATUS_LABEL[item.status] || item.status}
          </span>
          <span className="staff-inquiry-time">{dateTime(item.created_at)}</span>
        </span>
        <span className="staff-inquiry-arrow" aria-hidden="true">→</span>
      </button>
    </li>
  );
}

export default function TracePanel({ trace, running }) {
  if (!trace?.length && !running) return null
  return (
    <section className="panel trace">
      <h2>실행 기록</h2>
      <ol>
        {trace.map((t, i) => (
          <li key={i}>
            <span className="step">{t.step}</span>
            <span className="detail">{t.detail}</span>
            {t.hits > 0 && <span className="hits">{t.hits}건</span>}
          </li>
        ))}
        {running && (
          <li className="pending">
            <span className="step">진행 중</span>
            <span className="detail">…</span>
          </li>
        )}
      </ol>
    </section>
  )
}

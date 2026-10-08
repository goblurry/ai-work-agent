export default function EvidencePanel({ evidence }) {
  return (
    <section className="panel evidence">
      <h2>근거 {evidence?.length ? `(${evidence.length})` : ''}</h2>
      {!evidence?.length && <p className="empty">아직 없습니다.</p>}
      {evidence?.map((e) => (
        <article key={e.chunk_id} className="ev-item">
          <header>
            <a href={e.url} target="_blank" rel="noreferrer">{e.article || e.chunk_id}</a>
            <code>{e.chunk_id}</code>
          </header>
          <blockquote>{e.quote}</blockquote>
          <p className="why"><strong>적용 근거</strong> {e.why_applicable}</p>
        </article>
      ))}
    </section>
  )
}

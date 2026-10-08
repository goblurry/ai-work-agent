import { useState } from 'react'

export default function ResultDraft({ result, onSave, saving, savedStatus }) {
  const [text, setText] = useState(result.draft || '')
  const [editing, setEditing] = useState(false)

  return (
    <section className="panel result ok">
      <h2>답변 초안</h2>
      <p className="note">담당자 검토 후 발송됩니다. 시스템이 학생에게 직접 회신하지 않습니다.</p>

      {editing ? (
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={10} />
      ) : (
        <div className="draft">{text}</div>
      )}

      <div className="actions">
        <button onClick={() => setEditing((v) => !v)} className="secondary">
          {editing ? '수정 완료' : '초안 수정'}
        </button>
        <button onClick={() => onSave(text)} disabled={saving}>
          {saving ? '저장 중…' : '완료 저장'}
        </button>
        {savedStatus && <span className="saved">✓ {savedStatus}</span>}
      </div>
    </section>
  )
}

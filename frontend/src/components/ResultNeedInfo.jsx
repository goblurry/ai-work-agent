import { useState } from 'react'

export default function ResultNeedInfo({ result, onResume, resuming }) {
  const [answers, setAnswers] = useState({})
  const items = result.ask_student || []
  const filled = items.every((_, i) => (answers[`q${i}`] || '').trim())

  return (
    <section className="panel result need-info">
      <h2>추가 확인 필요</h2>
      <p className="note">아래 항목을 학생에게 확인한 뒤 입력하면 같은 문의로 이어서 처리합니다.</p>

      {items.map((q, i) => (
        <label key={i} className="field">
          <span>{q}</span>
          <input
            value={answers[`q${i}`] || ''}
            onChange={(e) => setAnswers({ ...answers, [`q${i}`]: e.target.value })}
            placeholder="확인한 내용 입력"
          />
        </label>
      ))}

      <div className="actions">
        <button onClick={() => onResume(answers)} disabled={!filled || resuming}>
          {resuming ? '처리 중…' : '보완 후 재개'}
        </button>
      </div>
    </section>
  )
}

import { useState } from 'react'
import * as api from './api'
import TracePanel from './components/TracePanel'
import EvidencePanel from './components/EvidencePanel'
import ResultDraft from './components/ResultDraft'
import ResultNeedInfo from './components/ResultNeedInfo'
import ResultUndetermined from './components/ResultUndetermined'

const TODAY = new Date().toISOString().slice(0, 10)

// 처리 상태: idle | running | done | error
export default function App() {
  const [question, setQuestion] = useState('')
  const [studentId, setStudentId] = useState('')
  const [asOf, setAsOf] = useState(TODAY)

  const [status, setStatus] = useState('idle')
  const [trace, setTrace] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const [resuming, setResuming] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savedStatus, setSavedStatus] = useState(null)

  const canSubmit = question.trim() && studentId.trim() && status !== 'running'

  function reset() {
    setStatus('idle'); setTrace([]); setResult(null)
    setError(null); setSavedStatus(null)
  }

  async function submit(e) {
    e?.preventDefault()
    if (!canSubmit) return
    reset()
    setStatus('running')
    try {
      const data = await api.createInquiry(
        { question: question.trim(), student_id: studentId.trim(), as_of: asOf },
        (step) => setTrace((t) => [...t, step])
      )
      setTrace(data.trace || [])
      setResult(data)
      setStatus('done')
    } catch (err) {
      setError(err.message || '알 수 없는 오류')
      setStatus('error')
    }
  }

  async function handleResume(answers) {
    setResuming(true); setError(null)
    try {
      const data = await api.resumeInquiry(
        result.inquiry_id, answers,
        (step) => setTrace((t) => [...t, step])
      )
      setTrace(data.trace || [])
      setResult(data)
    } catch (err) {
      setError(err.message || '재개 실패')
      setStatus('error')
    } finally {
      setResuming(false)
    }
  }

  async function handleSave(text) {
    setSaving(true); setError(null)
    try {
      const r = await api.reviewInquiry(result.inquiry_id, 'save', text)
      setSavedStatus(r.status || '완료')
    } catch (err) {
      setError(err.message || '저장 실패')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="app">
      <header className="top">
        <h1>학사나침반</h1>
        <p>학사행정 문의 처리 — 담당자용</p>
        {api.IS_MOCK && <span className="badge-mock">샘플 데이터</span>}
      </header>

      <form className="panel input" onSubmit={submit}>
        <label className="field">
          <span>문의 내용 <em>*</em></span>
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="학생이 문의한 내용을 그대로 입력하세요"
          />
        </label>

        <div className="row">
          <label className="field">
            <span>학번 <em>*</em></span>
            <input
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              placeholder="20211234"
            />
          </label>
          <label className="field small">
            <span>기준일</span>
            <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
          </label>
        </div>

        <div className="actions">
          <button type="submit" disabled={!canSubmit}>
            {status === 'running' ? '처리 중…' : '처리'}
          </button>
          {status !== 'idle' && (
            <button type="button" className="secondary" onClick={reset}>새 문의</button>
          )}
        </div>

        {api.IS_MOCK && (
          <p className="hint">
            샘플: 학번 <code>2021…</code> → 답변 초안 · <code>2022…</code> → 확정 불가 · 그 외 → 추가 확인
          </p>
        )}
      </form>

      {status === 'error' && (
        <section className="panel result error">
          <h2>오류</h2>
          <p className="err-msg">{error}</p>
          <div className="actions">
            <button onClick={submit}>재시도</button>
          </div>
        </section>
      )}

      <div className="split">
        <div className="col-main">
          {status === 'running' && (
            <section className="panel result loading">
              <h2>처리 중</h2>
              <p className="note">자료를 찾고 적용 조건을 확인하고 있습니다.</p>
            </section>
          )}

          {status === 'done' && result?.branch === 'A_draft' && (
            <ResultDraft result={result} onSave={handleSave} saving={saving} savedStatus={savedStatus} />
          )}
          {status === 'done' && result?.branch === 'B_need_info' && (
            <ResultNeedInfo result={result} onResume={handleResume} resuming={resuming} />
          )}
          {status === 'done' && result?.branch === 'C_undetermined' && (
            <ResultUndetermined result={result} onSave={handleSave} saving={saving} savedStatus={savedStatus} />
          )}

          <TracePanel trace={trace} running={status === 'running' || resuming} />
        </div>

        <aside className="col-side">
          <EvidencePanel evidence={result?.evidence} />
        </aside>
      </div>
    </div>
  )
}

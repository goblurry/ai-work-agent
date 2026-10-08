const REASON_LABEL = {
  근거없음: '관련 근거를 찾지 못했습니다',
  자료충돌: '자료가 서로 다른 내용을 담고 있습니다',
  최신성불명: '자료의 최신 여부를 확인할 수 없습니다',
  재량영역: '규정 외 재량 판단이 필요한 사안입니다',
}

export default function ResultUndetermined({ result, onSave, saving, savedStatus }) {
  const u = result.undetermined || {}
  return (
    <section className="panel result undetermined">
      <h2>확정 불가</h2>
      <p className="reason">
        <span className="tag">{u.reason}</span>
        {REASON_LABEL[u.reason]}
      </p>
      <p className="note">
        공개 자료만으로는 확정할 수 없어 답변을 생성하지 않았습니다. 아래 자료를 바탕으로 담당자가 판단해 주세요.
      </p>

      {u.conflicts?.length > 0 && (
        <div className="conflicts">
          <h3>충돌 지점</h3>
          <p className="note">어느 한쪽을 자동으로 선택하지 않았습니다.</p>
          <div className="conflict-grid">
            {u.conflicts.map((c) => (
              <div key={c.chunk_id} className="conflict">
                <code>{c.chunk_id}</code>
                <p>{c.claim}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {u.next_actions?.length > 0 && (
        <div className="next">
          <h3>다음 확인 사항</h3>
          <ul>{u.next_actions.map((a, i) => <li key={i}>{a}</li>)}</ul>
        </div>
      )}

      <div className="actions">
        <button onClick={() => onSave(null)} disabled={saving} className="secondary">
          {saving ? '저장 중…' : '이대로 기록'}
        </button>
        {savedStatus && <span className="saved">✓ {savedStatus}</span>}
      </div>
    </section>
  )
}

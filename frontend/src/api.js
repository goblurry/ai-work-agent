/**
 * API 어댑터.
 *
 * VITE_API_BASE 가 비어 있으면 mock 으로 동작한다.
 * 현선님 서버가 뜨면 .env 에 주소만 넣으면 실제 호출로 바뀐다.
 * 화면 코드는 건드리지 않는다.
 *
 * 응답 형식은 schemas/answer_result.json 을 따른다.
 */
import A from './mock/A_draft.json'
import B from './mock/B_need_info.json'
import C from './mock/C_undetermined.json'
import STUDENT from './mock/student.json'

const BASE = import.meta.env.VITE_API_BASE || ''
export const IS_MOCK = !BASE

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function real(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${body ? ` — ${body.slice(0, 200)}` : ''}`)
  }
  return res.json()
}

/** 학번 앞 4자리로 mock 분기. 2021→A, 2022→C, 그 외→B */
function pickMock(studentId) {
  const y = String(studentId || '').slice(0, 4)
  if (y === '2021') return A
  if (y === '2022') return C
  return B
}

/**
 * 문의 생성.
 * @param {{question: string, student_id: string, as_of?: string}} body
 * @param {(step: object) => void} [onStep] mock 에서 실행 기록을 한 줄씩 흘려보낸다.
 */
export async function createInquiry(body, onStep) {
  if (!IS_MOCK) return real('/api/inquiry', { method: 'POST', body: JSON.stringify(body) })

  const data = pickMock(body.student_id)
  if (onStep) {
    for (const step of data.trace) {
      await sleep(450)
      onStep(step)
    }
  } else {
    await sleep(1200)
  }
  // 입력한 학번이 화면에 반영되도록 얕게 덮어쓴다
  return { ...data, inquiry_id: data.inquiry_id }
}

/** B 분기 보완 후 재개. 같은 inquiry_id 로 이어진다. */
export async function resumeInquiry(inquiryId, answers, onStep) {
  if (!IS_MOCK) {
    return real(`/api/inquiry/${inquiryId}/resume`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    })
  }
  const extra = [
    { step: '학생조건확인', detail: `보완 입력 반영: ${Object.values(answers).filter(Boolean).join(' / ')}`, hits: 0 },
    { step: '재검색', detail: '보완된 조건으로 재검색', hits: 11 },
    { step: '적용조건검증', detail: '적용 조건 충족 확인', hits: 2 },
  ]
  if (onStep) for (const s of extra) { await sleep(450); onStep(s) }
  else await sleep(1000)

  return { ...A, inquiry_id: inquiryId, trace: [...A.trace, ...extra] }
}

/** 초안 수정 / 완료 저장 */
export async function reviewInquiry(inquiryId, action, text) {
  if (!IS_MOCK) {
    return real(`/api/inquiry/${inquiryId}/review`, {
      method: 'POST',
      body: JSON.stringify({ action, text }),
    })
  }
  await sleep(500)
  return { ok: true, status: action === 'save' ? '완료' : '수정됨' }
}

/** 학적 조회 */
export async function getStudent(studentId) {
  if (!IS_MOCK) return real(`/api/student/${studentId}`)
  await sleep(300)
  return { ...STUDENT, student_id: studentId }
}

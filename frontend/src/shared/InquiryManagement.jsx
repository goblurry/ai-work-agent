import { useState } from "react";
import { createPortal } from "react-dom";
import { request } from "./api";
import "./inquiry-management.css";

const TYPES = {graduation:"졸업 · 교과과정",course_recognition:"과목 이수 · 인정",leave_return:"휴학 · 복학",other:"기타 학사 문의"};
const OPTIONS = {
  major_track:["주전공","복수전공","부전공"],
  procedure:[["leave","휴학"],["return","복학"]],
  application_status:[["not_applied","미신청"],["saved","임시저장"],["submitted","신청서 제출"],["received","접수 완료"],["unknown","모름"]],
};

function initial(item) {
  return {question:item.question || "",inquiry_type:item.inquiry_type || "other",profile:{...item.profile},details:{...item.details},target_term:item.target_term || "",as_of:item.as_of || ""};
}

export default function InquiryManagement({item, path, canManage, onUpdated, onDeleted, actionsTarget}) {
  const [mode,setMode]=useState("");
  const [value,setValue]=useState(()=>initial(item));
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  if (!canManage) return null;
  const change=(group,key,next)=>setValue(v=>group ? {...v,[group]:{...v[group],[key]:next}} : {...v,[key]:next});
  async function save(event) {
    event.preventDefault();setBusy(true);setError("");
    const profile=Object.fromEntries(Object.entries(value.profile).map(([k,v])=>[k,v == null || v === "" ? null : k === "admission_year" ? Number(v) : v]));
    let details={};
    if (value.inquiry_type === "course_recognition") {
      for (const key of ["required_course_code","completed_course_code"]) details[key]=value.details[key] || null;
    } else if (value.inquiry_type === "leave_return") {
      for (const key of ["procedure","application_status","application_date","receipt_date"]) details[key]=value.details[key] || null;
    }
    try {
      const updated=await request(path,{method:"PUT",body:JSON.stringify({...value,question:value.question.trim(),profile,details,target_term:value.target_term || null,as_of:value.as_of || null})});
      onUpdated(updated);setMode("");
    } catch(e) {setError(e.message)} finally {setBusy(false)}
  }
  async function remove() {
    setBusy(true);setError("");
    try {await request(path,{method:"DELETE"});onDeleted()} catch(e) {setError(e.message)} finally {setBusy(false)}
  }
  function field(group,key,label,type="text") {
    const current=(group ? value[group]?.[key] : value[key]) ?? "";
    return <label key={key}><span>{label}</span>{OPTIONS[key] ? <select value={current} onChange={e=>change(group,key,e.target.value)} disabled={busy}><option value="">선택 안 함</option>{OPTIONS[key].map(o=><option key={Array.isArray(o)?o[0]:o} value={Array.isArray(o)?o[0]:o}>{Array.isArray(o)?o[1]:o}</option>)}</select> : <input type={type} value={current} onChange={e=>change(group,key,e.target.value)} disabled={busy} {...(key === "admission_year" ? {min:1900,max:2100} : {})} {...(key.endsWith("course_code") ? {pattern:"[0-9]{5}",inputMode:"numeric",maxLength:5} : {})}/>}</label>;
  }
  return <div className={"inquiry-management" + (actionsTarget ? " im-compact" : "")}>
    {!mode && (actionsTarget ? createPortal(<div className="im-actions"><button type="button" onClick={()=>{setValue(initial(item));setError("");setMode("edit")}}>문의 수정</button><button type="button" onClick={()=>{setError("");setMode("delete")}}>문의 삭제</button></div>, actionsTarget) : <div className="im-actions"><button type="button" onClick={()=>{setValue(initial(item));setError("");setMode("edit")}}>문의 수정</button><button type="button" onClick={()=>{setError("");setMode("delete")}}>문의 삭제</button></div>)}
    {mode === "edit" && <form onSubmit={save}>
      <h3>문의 수정</h3><p>수정하면 기존 검색 결과와 초안이 초기화됩니다. 담당자가 Agent를 다시 실행해야 합니다.</p>
      <fieldset disabled={busy}>
        <label><span>문의 유형</span><select value={value.inquiry_type} onChange={e=>setValue(v=>({...v,inquiry_type:e.target.value,details:{}}))}>{Object.entries(TYPES).map(([id,label])=><option value={id} key={id}>{label}</option>)}</select></label>
        <label><span>문의 내용</span><textarea required maxLength={10000} rows={5} value={value.question} onChange={e=>change(null,"question",e.target.value)}/></label>
        <div className="im-grid">
          {field("profile","department","소속 학과")}{field("profile","admission_year","입학연도","number")}
          {field("profile","student_status","학적 상태")}
          {["graduation","course_recognition"].includes(value.inquiry_type) && <>{field("profile","major_track","전공 구분")}{field("profile","target_department","대상 전공 학과")}</>}
          {field(null,"target_term","대상 학기")}{field(null,"as_of","판단 기준일","date")}
          {value.inquiry_type === "course_recognition" && <>{field("details","required_course_code","지정 과목 학수번호")}{field("details","completed_course_code","이수 과목 학수번호")}</>}
          {value.inquiry_type === "leave_return" && <>{field("details","procedure","신청 종류")}{field("details","application_status","신청 상태")}{field("details","application_date","신청일","date")}{field("details","receipt_date","접수일","date")}</>}
        </div>
      </fieldset>
      <div className="im-actions"><button type="submit" className="im-primary" disabled={busy}>{busy ? "저장 중…" : "수정 저장"}</button><button type="button" disabled={busy} onClick={()=>setMode("")}>취소</button></div>
    </form>}
    {mode === "delete" && <div role="group" aria-label="문의 삭제 확인"><h3>문의를 삭제하시겠습니까?</h3><p>학생과 담당자의 문의 목록에서 사라집니다. 삭제한 문의는 더 이상 처리할 수 없습니다.</p><div className="im-actions"><button type="button" className="im-danger" disabled={busy} onClick={remove}>{busy ? "삭제 중…" : "삭제 확인"}</button><button type="button" disabled={busy} onClick={()=>setMode("")}>취소</button></div></div>}
    {error && <p className="im-error" role="alert">{error}</p>}
  </div>;
}

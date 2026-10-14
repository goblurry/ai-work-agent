import { useState } from "react";
import { post } from "../shared/api";
import "./styles.css";

export default function StaffLogin({ onAuthChange }) {
  const [login, setLogin] = useState({ username: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signIn(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = await post("/auth/login", login);
      onAuthChange(user);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="staff-shell">
      <main className="staff-login">
        <section className="staff-panel" aria-labelledby="staff-login-title">
          <div className="staff-panel-body">
            <span className="eyebrow">ACADEMIC ADMINISTRATION</span>
            <h1 id="staff-login-title" className="staff-title">담당자 로그인</h1>
            <p className="staff-today">학생 문의를 확인하고 학사 행정 업무를 처리하세요.</p>
            <form onSubmit={signIn} className="staff-login-form">
              <label className="staff-field">
                아이디
                <input required autoComplete="username" value={login.username}
                  onChange={(e) => setLogin({ ...login, username: e.target.value })} />
              </label>
              <label className="staff-field">
                비밀번호
                <input required type="password" autoComplete="current-password" value={login.password}
                  onChange={(e) => setLogin({ ...login, password: e.target.value })} />
              </label>
              {error && <p className="staff-error" role="alert">{error}</p>}
              <button className="staff-action" disabled={busy}>
                {busy ? "로그인 중…" : "로그인"}
              </button>
            </form>
            <a className="staff-login-student" href="?view=student">학생 문의 화면으로 이동</a>
          </div>
        </section>
      </main>
    </div>
  );
}

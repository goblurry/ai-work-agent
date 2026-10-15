import { useCallback, useEffect, useState } from "react";
import { post, request } from "../shared/api";
import Icon from "../shared/Icon";
import Dashboard from "./Dashboard";
import InquiryDetail from "./InquiryDetail";
import PhoneIntake from "./PhoneIntake";
import WebInquiries from "./WebInquiries";
import "./styles.css";

const MENU = [
  { id: "dashboard", name: "대시보드", icon: "clock" },
  { id: "web", name: "웹 문의", icon: "other" },
  { id: "phone", name: "전화 문의", icon: "user" },
];

export default function StaffApp({ user, onSignOut }) {
  const [view, setView] = useState("dashboard");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState(null);
  const [busy, setBusy] = useState(false);

  // 세션이 끊기면(12시간) 모든 요청이 401 이 된다.
  // 같은 오류를 반복해서 보여 주지 말고 로그인 화면으로 돌려보낸다.
  const handleUnauthorized = useCallback(() => {
    setItems([]);
    setOpenId(null);
    onSignOut?.();
  }, [onSignOut]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await request("/inquiries");
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      if (e.status === 401) {
        handleUnauthorized();
        return;
      }
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [handleUnauthorized]);

  useEffect(() => {
    load();
  }, [load]);

  function go(next) {
    setOpenId(null);
    setView(next);
  }

  async function signOut() {
    setBusy(true);
    try {
      await post("/auth/logout", {});
      setItems([]);
      setOpenId(null);
      onSignOut?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const phoneActions = {
    create: (body) => post("/inquiries", body),
    run: (id) => post(`/inquiries/${id}/run`, {}),
    open: (id) => {
      load();
      setOpenId(id);
    },
  };

  return (
    <div className="staff-shell">
      <header className="staff-header">
        <div className="staff-brand"><span className="staff-brand-icon"><Icon name="book" size={18}/></span><span className="staff-wordmark">학사 문의 처리<small>학사 업무 지원 AI Agent</small></span></div>
        <div className="staff-header-right">
          <span className="staff-account"><Icon name="user" size={15}/>{user?.username}<small>담당자</small></span>
          <button
            type="button"
            className="staff-text-button"
            onClick={signOut}
            disabled={busy}
          >
            로그아웃
          </button>
        </div>
      </header>

      <div className="staff-body">
        <nav className="staff-nav" aria-label="주 메뉴">
          {MENU.map((m) => (
            <button
              key={m.id}
              type="button"
              aria-current={view === m.id && !openId ? "page" : undefined}
              onClick={() => go(m.id)}
            >
              <Icon name={m.icon} size={17} />
              {m.name}
            </button>
          ))}
        </nav>

        <main className="staff-main">
          {error && !openId && <p className="staff-error">{error}</p>}

          {openId ? (
            <InquiryDetail
              inquiryId={openId}
              onBack={() => setOpenId(null)}
              onChanged={load}
              onUnauthorized={handleUnauthorized}
            />
          ) : view === "dashboard" ? (
            <Dashboard
              items={items}
              loading={loading}
              onOpen={setOpenId}
              onReload={load}
              onPhone={() => go("phone")}
            />
          ) : view === "web" ? (
            <WebInquiries
              items={items}
              loading={loading}
              onOpen={setOpenId}
              onReload={load}
            />
          ) : (
            <PhoneIntake
              items={items}
              loading={loading}
              onOpen={setOpenId}
              onReload={load}
              onCreated={phoneActions}
            />
          )}
        </main>
      </div>
    </div>
  );
}

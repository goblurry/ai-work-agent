import { useEffect, useState } from "react";
import { request } from "./shared/api";
import StaffApp from "./staff/StaffApp";
import StudentApp from "./student/StudentApp";
import StaffLogin from "./staff/StaffLogin";

// /auth/me 의 role 로 화면을 고른다. 역할을 임의로 선택하지 않는다.
export default function Root() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    // 서버가 쉬다 깨어나면 첫 응답이 오래 걸린다. 그동안 빈 화면만
    // 보이지 않도록 잠시 뒤 안내를 띄운다.
    const timer = setTimeout(() => setSlow(true), 1500);
    request("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => {
        clearTimeout(timer);
        setReady(true);
      });
    return () => clearTimeout(timer);
  }, []);

  if (!ready)
    return (
      <div
        role="status"
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          padding: 24,
          textAlign: "center",
          color: "var(--muted)",
          fontSize: 14,
          lineHeight: 1.7,
        }}
      >
        {slow ? (
          <p>
            서버를 깨우는 중입니다.
            <br />
            처음 접속할 때는 시간이 조금 걸릴 수 있습니다.
          </p>
        ) : (
          <p>불러오는 중입니다.</p>
        )}
      </div>
    );
  if (user?.role === "staff")
    return <StaffApp user={user} onSignOut={() => setUser(null)} />;
  // 기본 주소는 담당자 로그인이다. 학생 화면은 시연용이라 링크 없이 /student 에서만 연다.
  if (window.location.pathname.replace(/\/+$/, "") === "/student")
    return <StudentApp onAuthChange={setUser} />;
  return <StaffLogin onAuthChange={setUser} />;
}

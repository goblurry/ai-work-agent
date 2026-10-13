import { Component } from "react";

// 렌더 중 오류가 나면 React 는 화면 전체를 비운다. 시연 중에 그러면
// 아무것도 남지 않으므로, 최소한의 안내와 복구 수단을 보여 준다.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    console.error("화면 오류", error, info);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div
        role="alert"
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          padding: 24,
          textAlign: "center",
          lineHeight: 1.7,
        }}
      >
        <div>
          <p style={{ fontSize: 15, fontWeight: 600, margin: "0 0 6px" }}>
            화면을 표시하지 못했습니다.
          </p>
          <p style={{ color: "var(--muted)", fontSize: 13, margin: "0 0 18px" }}>
            이미 저장된 문의와 답변은 영향을 받지 않습니다.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              background: "var(--green)",
              color: "#fff",
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            새로고침
          </button>
        </div>
      </div>
    );
  }
}

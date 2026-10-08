const base = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");
export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(base + path, {
      credentials: "include",
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new Error("서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      typeof body.detail === "string"
        ? body.detail
        : response.status === 422
          ? "입력한 항목을 다시 확인해 주세요."
          : "요청을 처리하지 못했습니다. 다시 시도해 주세요.",
    );
    error.status = response.status;
    throw error;
  }
  return body;
}
export const post = (path, data) =>
  request(path, { method: "POST", body: JSON.stringify(data) });

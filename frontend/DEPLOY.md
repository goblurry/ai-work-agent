# 프론트엔드 배포

API 가이드 7장을 그대로 따릅니다. **동일 출처 프록시** 방식입니다.

Vite 의 `server.proxy` 는 개발 전용이라 `npm run build` 결과에 포함되지 않습니다.
정적 호스팅에 파일만 올리면 `/api` 가 연결되지 않고, 쿠키 인증도 동작하지 않습니다.

## Vercel

운영 주소: https://sng-agent.vercel.app

`frontend/vercel.json` 이 `/api` 를 백엔드로 전달합니다. 설정은 이것뿐입니다.

```json
{ "rewrites": [{ "source": "/api/:path*",
                 "destination": "https://goblurry-academic-ai-agent.hf.space/:path*" }] }
```

프로젝트 설정은 **Root Directory `frontend`**, Framework Vite, Build `npm run build`, Output `dist` 입니다.

환경변수는 넣지 않습니다. `VITE_API_URL` 을 비워 두면 `src/shared/api.js` 가 `/api` 를 사용하고,
위 rewrite 가 백엔드로 전달합니다. 키·토큰은 프론트에 두지 않습니다.

## 배포 후 — 현선님께 요청할 것 (권한 필요)

Hugging Face Space Settings 의 **`CORS_ORIGINS`** 변수에 배포 주소를 추가해야 합니다.
기존 로컬 주소는 쉼표로 함께 두시면 됩니다.

```
http://127.0.0.1:5173,https://<배포주소>
```

쿠키 설정은 `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none` 입니다.
배포는 HTTPS 여야 하며, 로컬 Vite 의 Secure 제거 로직은 운영에 복사하지 않습니다.

## 확인 순서

1. 배포 주소 접속 → 로그인 화면이 뜨는지
2. 학생 계정 로그인 → 문의 접수 → 내 문의에 보이는지
3. 담당자 계정 로그인 → 같은 문의 → Agent 실행 → 근거 표시
4. 판단·메모 → 초안 작성 → 초안 저장 → 답변 등록
5. 학생 계정으로 다시 로그인 → 최종 답변 확인

> 같은 브라우저 탭은 쿠키를 공유합니다. 학생·담당자를 동시에 시연하려면
> 다른 브라우저나 시크릿 창을 쓰세요.

## 대안

`VITE_API_URL` 에 백엔드 주소를 직접 넣어 호출할 수도 있지만,
브라우저의 타사 쿠키 차단 영향을 받습니다. 동일 출처 프록시를 먼저 쓰세요.

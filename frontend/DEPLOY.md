# 프론트엔드 배포

API 가이드 7장을 그대로 따릅니다. **동일 출처 프록시** 방식입니다.

Vite 의 `server.proxy` 는 개발 전용이라 `npm run build` 결과에 포함되지 않습니다.
정적 호스팅에 파일만 올리면 `/api` 가 연결되지 않고, 쿠키 인증도 동작하지 않습니다.

## Netlify (권장)

저장소가 **조직(snu-sng) 소유**라 Vercel 무료 플랜으로는 배포되지 않습니다.
Vercel 은 조직 저장소에 Team(유료) 플랜을 요구합니다. Netlify 는 조직 저장소도 무료입니다.

`frontend/netlify.toml` 을 올려 두었습니다. 설정은 이것뿐입니다.

1. https://app.netlify.com/signup 에서 **GitHub 로 로그인**
2. **Add new site → Import an existing project → GitHub**
3. `snu-sng/ai-work-agent` 선택
4. 빌드 설정은 `netlify.toml` 이 지정하므로 **그대로 두고 Deploy**

`base`, `command`, `publish` 가 파일에 있어서 화면에서 따로 바꿀 것이 없습니다.

## Vercel (개인 저장소일 때)

`frontend/vercel.json` 을 같이 올려 두었습니다. 설정은 이것뿐입니다.

```json
{ "rewrites": [{ "source": "/api/:path*",
                 "destination": "https://goblurry-academic-ai-agent.hf.space/:path*" }] }
```

1. Vercel 에서 저장소를 가져오고 **Root Directory 를 `frontend`** 로 지정합니다
2. Framework 는 Vite, Build `npm run build`, Output `dist` (자동 인식됩니다)
3. 배포 후 나온 주소를 확인합니다

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

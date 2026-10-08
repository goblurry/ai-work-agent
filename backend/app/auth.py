"""시연 계정과 DB에 저장하는 만료 가능한 로그인 세션."""
import hashlib
import hmac
import os
import secrets
import time
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import APIKeyCookie
from pydantic import BaseModel, ConfigDict, Field

COOKIE = 'academic_session'
SESSION_SECONDS = 12 * 60 * 60
session_cookie = APIKeyCookie(name=COOKIE, auto_error=False)


def password_hash(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f'scrypt${salt.hex()}${digest.hex()}'


def verify_password(password, encoded):
    try:
        algorithm, salt, digest = encoded.split('$')
        if algorithm != 'scrypt':
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Login(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=100, examples=['student'])
    password: str = Field(min_length=1, max_length=256)


class Auth:
    def __init__(self, connect):
        self.connect = connect
        self.secure = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
        self.same_site = os.getenv('COOKIE_SAMESITE', 'lax').lower()
        if self.same_site not in ('lax', 'strict', 'none') or (self.same_site == 'none' and not self.secure):
            raise ValueError('COOKIE_SAMESITE는 lax/strict/none이며 none은 COOKIE_SECURE=true가 필요합니다.')

    def initialize(self, seed=True):
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('student','staff')))")
            db.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at DOUBLE PRECISION NOT NULL)')
            db.execute('DELETE FROM sessions WHERE expires_at <= ?', (time.time(),))
            if db.postgres:
                db.execute('ALTER TABLE users ENABLE ROW LEVEL SECURITY')
                db.execute('ALTER TABLE sessions ENABLE ROW LEVEL SECURITY')
        if not seed:
            return
        for role in ('student', 'staff'):
            password = os.getenv(f'DEMO_{role.upper()}_PASSWORD')
            if password:
                self.create_user(os.getenv(f'DEMO_{role.upper()}_USERNAME', role), password, role)

    def create_user(self, username, password, role):
        if role not in ('student', 'staff'):
            raise ValueError('역할은 student 또는 staff입니다.')
        with self.connect() as db:
            existing = db.execute('SELECT id, role FROM users WHERE username=?', (username,)).fetchone()
            if existing:
                if existing[1] != role:
                    raise ValueError('같은 아이디에 다른 역할이 이미 등록되어 있습니다.')
                return existing[0]
            user_id = str(uuid4())
            db.execute('INSERT INTO users VALUES (?,?,?,?)', (user_id, username, password_hash(password), role))
            return user_id

    def user_by_username(self, username):
        with self.connect() as db:
            row = db.execute('SELECT id,username,role FROM users WHERE username=?', (username,)).fetchone()
        return dict(zip(('id', 'username', 'role'), row)) if row else None

    def current_user(self, token: str | None = Depends(session_cookie)):
        if token:
            with self.connect() as db:
                row = db.execute('SELECT u.id,u.username,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?',
                                 (token_hash(token), time.time())).fetchone()
            if row:
                return dict(zip(('id', 'username', 'role'), row))
        raise HTTPException(401, '로그인이 필요합니다.')

    def require_student(self, request: Request):
        user = self.current_user(request.cookies.get(COOKIE))
        if user['role'] != 'student':
            raise HTTPException(403, '학생 계정으로 이용해 주세요.')
        return user

    def require_staff(self, request: Request):
        user = self.current_user(request.cookies.get(COOKIE))
        if user['role'] != 'staff':
            raise HTTPException(403, '담당자만 사용할 수 있습니다.')
        return user

    def revoke(self, token):
        if token:
            with self.connect() as db:
                db.execute('DELETE FROM sessions WHERE token_hash=?', (token_hash(token),))

    def router(self):
        router = APIRouter(prefix='/auth', tags=['로그인'])

        @router.post('/login', summary='아이디·비밀번호로 로그인')
        def login(payload: Login, request: Request, response: Response):
            with self.connect() as db:
                row = db.execute('SELECT id,username,password_hash,role FROM users WHERE username=?', (payload.username,)).fetchone()
            # 존재하지 않는 아이디도 같은 해시 계산을 수행한다.
            dummy = 'scrypt$' + ('00' * 16) + '$' + ('00' * 32)
            valid = verify_password(payload.password, row[2] if row else dummy)
            if not row or not valid:
                raise HTTPException(401, '아이디 또는 비밀번호가 올바르지 않습니다.')
            self.revoke(request.cookies.get(COOKIE))
            token = secrets.token_urlsafe(32)
            with self.connect() as db:
                db.execute('DELETE FROM sessions WHERE expires_at <= ?', (time.time(),))
                db.execute('INSERT INTO sessions VALUES (?,?,?)', (token_hash(token), row[0], time.time() + SESSION_SECONDS))
            response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, secure=self.secure, samesite=self.same_site, path='/')
            response.headers['Cache-Control'] = 'no-store'
            return {'id': row[0], 'username': row[1], 'role': row[3]}

        @router.post('/logout', summary='로그아웃')
        def logout(request: Request, response: Response):
            self.revoke(request.cookies.get(COOKIE))
            response.delete_cookie(COOKIE, path='/', secure=self.secure, httponly=True, samesite=self.same_site)
            return {'message': '로그아웃했습니다.'}

        @router.get('/me', summary='로그인한 계정·역할 조회')
        def me(response: Response, user=Depends(self.current_user)):
            response.headers['Cache-Control'] = 'no-store'
            return user

        return router

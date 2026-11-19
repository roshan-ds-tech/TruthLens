"""Accounts: sign-up, log-in, log-out and the current-user dependency.

* Passwords: scrypt (n=2^14, r=8, p=1, 16-byte salt) from the standard library; compared in constant time.
* Sessions: a random 256-bit bearer token handed to the client once; only its SHA-256 is stored, and it
  expires after ``config.SESSION_DAYS``.
* Log-in attempts: at most ``LOGIN_MAX_FAILURES`` failures per email in ``LOGIN_WINDOW_S``, then 429.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, delete, select

from . import config, db
from .models import AuthSession, Case, User, utcnow

router = APIRouter(prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **SCRYPT)
    return f"scrypt${SCRYPT['n']}${SCRYPT['r']}${SCRYPT['p']}${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, want = stored.split("$")
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(got.hex(), want)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class _Limiter:
    def __init__(self) -> None:
        self.fails: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key: str) -> None:
        with self.lock:
            q = self.fails[key]
            while q and q[0] < time.monotonic() - config.LOGIN_WINDOW_S:
                q.popleft()
            if len(q) >= config.LOGIN_MAX_FAILURES:
                raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")

    def fail(self, key: str) -> None:
        with self.lock:
            self.fails[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self.lock:
            self.fails.pop(key, None)


limiter = _Limiter()


def get_session():
    with db.session() as s:
        yield s


def current_user(authorization: Optional[str] = Header(default=None), s: Session = Depends(get_session)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Log in to continue.")
    sess = s.exec(select(AuthSession).where(AuthSession.token_hash == _token_hash(authorization[7:].strip()))).first()
    if sess is None or sess.expires_at.replace(tzinfo=None) < utcnow().replace(tzinfo=None):
        raise HTTPException(401, "Your session has expired. Log in again.")
    user = s.get(User, sess.user_id)
    if user is None:
        raise HTTPException(401, "Account not found.")
    return user


def can_see(case: Case, user: User) -> bool:
    """Owners see their cases; unowned (CLI) cases are shared only on a local install."""
    return case.owner_id == user.id or (case.owner_id is None and config.MODE == "local")


def _issue(s: Session, user: User) -> dict:
    token = secrets.token_urlsafe(32)
    s.add(AuthSession(user_id=user.id, token_hash=_token_hash(token), expires_at=utcnow() + timedelta(days=config.SESSION_DAYS)))
    # drop this user's expired sessions while we are here
    s.exec(delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at < utcnow()))
    s.commit()
    return {"token": token, "user": public(user), "expires_in_days": config.SESSION_DAYS}


def public(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name}


class SignupIn(BaseModel):
    name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/signup")
def signup(body: SignupIn, s: Session = Depends(get_session)) -> dict:
    if not config.ALLOW_SIGNUP:
        raise HTTPException(403, "Sign-up is closed on this server.")
    email, name = body.email.strip().lower(), body.name.strip()
    if not name or len(name) > 80:
        raise HTTPException(400, "Enter your name (up to 80 characters).")
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(400, "Enter a valid email address.")
    if len(body.password) < 8 or len(body.password) > 200:
        raise HTTPException(400, "Use a password of at least 8 characters.")
    if s.exec(select(User).where(User.email == email)).first():
        raise HTTPException(409, "An account with this email already exists. Log in instead.")
    user = User(email=email, name=name, password_hash=hash_password(body.password))
    s.add(user)
    s.commit()
    s.refresh(user)
    return _issue(s, user)


@router.post("/login")
def login(body: LoginIn, request: Request, s: Session = Depends(get_session)) -> dict:
    email = body.email.strip().lower()
    limiter.check(email)
    user = s.exec(select(User).where(User.email == email)).first()
    # hash even when the account does not exist, so response time does not reveal which emails are registered
    ok = verify_password(body.password, user.password_hash if user else hash_password("x" * 12))
    if not user or not ok:
        limiter.fail(email)
        raise HTTPException(401, "Email or password is incorrect.")
    limiter.reset(email)
    return _issue(s, user)


@router.post("/logout")
def logout(authorization: Optional[str] = Header(default=None), s: Session = Depends(get_session)) -> dict:
    if authorization and authorization.lower().startswith("bearer "):
        s.exec(delete(AuthSession).where(AuthSession.token_hash == _token_hash(authorization[7:].strip())))
        s.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return public(user)

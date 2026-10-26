# Technical Specification: Step 1.3a — FastAPI Supabase JWT Auth Dependency & Protected Current User Route

> **Milestone**: 1.3 Authentication  
> **Feature Branch**: `feat/step-1-3a-fastapi-supabase-jwt-auth`  
> **Status**: Ready for Implementation  
> **Parent Documents**: [Gemini.md](file:///d:/RepoDefense/GEMINI.md), [implementation_plan.md](file:///d:/RepoDefense/implementation_plan.md), [.agents/memory/flashback.md](file:///d:/RepoDefense/.agents/memory/flashback.md)

---

## 1. Overview & Architectural Goal

The objective of Step 1.3a is to establish backend authentication in FastAPI by validating Supabase-issued JSON Web Tokens (JWTs). This introduces a cryptographically verified, stateless security layer that:
1. Validates incoming HTTP Bearer tokens against the configured `SUPABASE_JWT_SECRET`.
2. Verifies token expiration (`exp`), audience claims (`aud="authenticated"`), and cryptographic signature (`HS256`).
3. Extracts the subject claim (`sub` as user UUID) and `email`.
4. Implements a FastAPI dependency (`get_current_user`) that retrieves or idempotently provisions the local database `User` record in PostgreSQL 17.
5. Exposes a protected `GET /api/v1/auth/me` endpoint returning the authenticated user's profile.

---

## 2. Invariants & Security Guardrails

1. **Zero Code Execution**: Repository code is not executed. All logic is pure cryptographic verification and database queries.
2. **Stateless JWT Validation**: Tokens are verified using local signature verification (`PyJWT`), preventing outbound network bottlenecks on every API call.
3. **Idempotent User Tenancy Synchronization**: When a user authenticated by Supabase accesses the API for the first time, our backend automatically ensures a corresponding record in the local `users` table exists.
4. **Strict HTTP 401 Responses**: Missing, malformed, invalid signature, or expired tokens return HTTP 401 with `WWW-Authenticate: Bearer` headers and distinct, sanitized error descriptions.
5. **No Secrets in Source Control**: `SUPABASE_JWT_SECRET` is managed via Pydantic `Settings` and environment variables.

---

## 3. Target Files & Component Specifications

### 1. `backend/app/core/config.py` (Update)
- Add `SUPABASE_JWT_SECRET: str = Field(default="test-supabase-jwt-secret-for-development-32-chars-minimum")`.
- Add `JWT_ALGORITHM: str = Field(default="HS256")`.

### 2. `backend/app/schemas/auth.py` (New File, $\le 50$ LOC)
- `TokenPayload(BaseModel)`:
  - `sub: uuid.UUID`
  - `email: str`
  - `exp: int`
  - `aud: Optional[Union[str, list[str]]] = None`
  - `role: Optional[str] = None`
- `UserResponse(BaseModel)`:
  - `id: uuid.UUID`
  - `email: str`
  - `created_at: datetime`
  - `updated_at: datetime`
  - `model_config = ConfigDict(from_attributes=True)`

### 3. `backend/app/core/security.py` (New File, $\le 120$ LOC)
- `decode_access_token(token: str) -> TokenPayload`:
  - Decodes token via `jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], audience="authenticated")`.
  - Catches `jwt.ExpiredSignatureError` and raises `HTTPException(status_code=401, detail="Token has expired")`.
  - Catches `jwt.PyJWTError` and raises `HTTPException(status_code=401, detail="Could not validate credentials")`.
- `security_scheme = HTTPBearer(auto_error=True)`
- `async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme), db: AsyncSession = Depends(get_db)) -> User`:
  - Calls `decode_access_token(credentials.credentials)`.
  - Queries `User` by `id == token_payload.sub`.
  - If not found, provisions new `User(id=token_payload.sub, email=token_payload.email)` and commits to `db`.
  - Returns `User` ORM instance.

### 4. `backend/app/api/v1/auth.py` (New File, $\le 50$ LOC)
- Router prefix: `/auth`, tags: `["Authentication"]`
- `GET /me`:
  - Injects `current_user: User = Depends(get_current_user)`.
  - Returns `UserResponse.model_validate(current_user)`.

### 5. `backend/app/main.py` (Update)
- Include `/api/v1/auth` router under `prefix=f"{settings.API_V1_STR}/v1"`.

### 6. `backend/tests/test_auth.py` (New File, $\le 150$ LOC)
- Helper: `create_test_jwt(user_id: uuid.UUID, email: str, expires_in_sec: int = 3600, secret: str = ..., aud: str = "authenticated") -> str`.
- Test cases:
  1. `test_unauthenticated_request_rejected`: `GET /api/v1/auth/me` without Bearer token -> 401.
  2. `test_invalid_token_rejected`: `GET /api/v1/auth/me` with invalid string -> 401.
  3. `test_expired_token_rejected`: `GET /api/v1/auth/me` with expired JWT -> 401.
  4. `test_valid_token_authenticates_and_provisions_user`: valid token -> 200, returns user ID and email, verifies record created in DB, tests cascade cleanup.
  5. `test_valid_token_existing_user`: subsequent request with same token returns 200 without duplicate creation.

---

## 4. Acceptance Criteria

1. `GET /api/v1/auth/me` successfully protects against unauthenticated and invalid requests with HTTP 401.
2. Valid Supabase JWTs successfully resolve to local database `User` records.
3. All unit and integration tests in `backend/tests/test_auth.py` pass (100%).
4. Full backend test suite passes without regressions.
5. All source files conform to $\le 300$ LOC limit and 0 `ruff` errors.

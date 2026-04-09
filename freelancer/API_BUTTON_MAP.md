# Unitary X Frontend Button -> Backend API Map

This backend now supports JSON and form payloads for auth, so a new Figma frontend can integrate directly.

Scope: Main page only. Admin and superadmin backend actions are intentionally excluded from this map.

## Base URL

- Local: `http://localhost:10184`

## Quick Rules

- Send `Content-Type: application/json` for modern frontend calls.
- Include `credentials: "include"` in `fetch` to keep login session cookies.
- Read current user state with `GET /api/auth/session` on app load.

## Core Button Actions

1. Sign In button
- Method: `POST`
- Path: `/login`
- Body:
```json
{
  "login_type": "user",
  "email": "you@example.com",
  "password": "Secret123!",
  "remember": true
}
```

2. Sign Up button
- Method: `POST`
- Path: `/register`
- Body:
```json
{
  "name": "Your Name",
  "email": "you@example.com",
  "password": "Secret123!",
  "confirm": "Secret123!"
}
```

3. Forgot Password Send OTP button
- Method: `POST`
- Path: `/forgot-password/send-otp`
- Body:
```json
{
  "email": "you@example.com"
}
```

4. Verify OTP button
- Method: `POST`
- Path: `/verify-otp`
- Body:
```json
{
  "email": "you@example.com",
  "otp": "123456"
}
```

5. Reset Password button
- Method: `POST`
- Path: `/forgot-password/reset`
- Body:
```json
{
  "email": "you@example.com",
  "otp": "123456",
  "new_password": "NewPass123!"
}
```

6. Logout button
- Method: `POST`
- Path: `/api/auth/logout`
- Body: none

7. Project/Contact Submit button
- Method: `POST`
- Path: `/api/contact`
- Auth: login required
- Body:
```json
{
  "name": "Your Name",
  "email": "you@example.com",
  "phone": "1234567890",
  "service": "web development",
  "deadline": "2026-05-10",
  "message": "Detailed project requirement..."
}
```

8. Feedback Submit button
- Method: `POST`
- Path: `/feedback/submit`
- Auth: login required
- Body:
```json
{
  "message": "Great service",
  "rating": 5
}
```

9. Projects filter/load button
- Method: `GET`
- Path: `/api/projects?category=all`

10. Track page view
- Method: `POST`
- Path: `/api/traffic/page-view`

11. Track scroll
- Method: `POST`
- Path: `/api/traffic/scroll`

## Frontend Integration Manifest Endpoint

Use this to auto-wire buttons dynamically:

- Method: `GET`
- Path: `/api/frontend/actions/main-page`

Legacy alias (same result):

- Method: `GET`
- Path: `/api/frontend/actions`

## Session Check Endpoint

Use this on initial app load:

- Method: `GET`
- Path: `/api/auth/session`

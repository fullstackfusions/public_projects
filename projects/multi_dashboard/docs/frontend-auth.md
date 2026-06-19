# Frontend: Authentication

The auth feature covers login, token storage, protected routes, and Google OAuth. It's how the React frontend gets and manages JWTs from `auth-py`.

---

## What You'll Learn

- JWT storage strategy — why `localStorage` and what the tradeoffs are
- Auto-refreshing tokens before they expire
- `ProtectedRoute` — how to redirect unauthenticated users in React Router
- React Context for sharing auth state across the app

---

## How It Works

```
User fills login form
  → LoginPage calls POST /auth/token on auth-py
  → Gets back access_token + refresh_token
  → Stored in localStorage
  → AuthContext updates to "logged in"

Every API call
  → Reads localStorage.access_token
  → Sends as "Authorization: Bearer <token>"

Token expires (30 min)
  → Auto-refresh hook calls POST /auth/refresh
  → Swaps in new access_token silently

User visits protected page without a token
  → ProtectedRoute redirects to /login
```

---

## File Structure

```
src/features/auth/
├── LoginPage.tsx        # Login form + Google OAuth button
├── ProtectedRoute.tsx   # Route guard — redirects to /login if no token

src/context/
└── AuthContext.tsx      # Shared auth state + login/logout functions

src/api/
└── auth.ts              # API calls to auth-py
```

---

## Key Code Patterns

**Using the auth context anywhere in the app:**
```tsx
const { user, logout } = useAuth();
```

**Protecting a route:**
```tsx
<Route path="/todos" element={
  <ProtectedRoute>
    <TodosPage />
  </ProtectedRoute>
} />
```

**Making an authenticated API call:**
```typescript
const token = localStorage.getItem("access_token");
const response = await fetch("/api/resource", {
  headers: { "Authorization": `Bearer ${token}` }
});
```

---

## Google OAuth Flow

1. User clicks "Sign in with Google"
2. Browser redirects to Google's login page
3. Google redirects back to `/auth/callback` with a code
4. `auth-py` exchanges the code for user info and issues a JWT
5. `AuthCallbackPage.tsx` reads the token from the URL fragment and stores it

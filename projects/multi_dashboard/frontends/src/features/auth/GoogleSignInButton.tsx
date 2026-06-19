import { Button } from "@mui/material";

const AUTH_API_URL = import.meta.env.VITE_AUTH_API_URL || "http://localhost:8005";

interface Props {
  returnTo?: string;
}

/**
 * Redirects the browser to auth-py's Google OAuth initiation endpoint.
 * Auth-py handles PKCE, state, and ultimately delivers tokens via hash fragment
 * to /auth/callback (handled by AuthCallbackPage).
 */
export function GoogleSignInButton({ returnTo = "/" }: Props) {
  const href = `${AUTH_API_URL}/auth/google/login?return_to=${encodeURIComponent(returnTo)}`;

  return (
    <Button
      component="a"
      href={href}
      variant="outlined"
      fullWidth
      sx={{ mt: 1, textTransform: "none", gap: 1 }}
    >
      <img
        src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
        alt="Google"
        width={20}
        height={20}
      />
      Sign in with Google
    </Button>
  );
}

import { Box, CircularProgress, Typography } from "@mui/material";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

/**
 * Handles the OAuth redirect from auth-py.
 *
 * Auth-py delivers tokens via the URL hash fragment:
 *   /auth/callback#access_token=...&refresh_token=...&return_to=/dashboard
 *
 * This page:
 *  1. Parses the hash fragment.
 *  2. Stores tokens in localStorage.
 *  3. Calls checkAuth() so AuthContext picks up the new token.
 *  4. Scrubs the hash from the URL bar (history.replaceState).
 *  5. Navigates to return_to (or / if absent).
 */
export function AuthCallbackPage() {
  const navigate = useNavigate();
  const { checkAuth } = useAuth();

  useEffect(() => {
    const hash = window.location.hash.slice(1); // strip leading '#'
    const params = new URLSearchParams(hash);

    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const returnTo = params.get("return_to") || "/";

    if (accessToken) {
      localStorage.setItem("access_token", accessToken);
    }
    if (refreshToken) {
      localStorage.setItem("refresh_token", refreshToken);
    }

    // Wipe the hash from the URL bar so tokens don't linger in history
    history.replaceState(null, "", window.location.pathname);

    if (!accessToken) {
      // No token in hash — likely a direct navigation; send to login
      navigate("/login", { replace: true });
      return;
    }

    // Re-hydrate auth context with the newly stored token, then navigate
    checkAuth().then(() => {
      navigate(returnTo, { replace: true });
    });
  }, [navigate, checkAuth]);

  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="100vh"
      gap={2}
    >
      <CircularProgress />
      <Typography variant="body2" color="text.secondary">
        Completing sign-in…
      </Typography>
    </Box>
  );
}

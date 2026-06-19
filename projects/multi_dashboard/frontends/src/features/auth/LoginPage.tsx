import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Container,
  IconButton,
  InputAdornment,
  Link,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authService, type DevUser } from "../../api/auth";
import { useAuth } from "../../context/AuthContext";
import { GoogleSignInButton } from "./GoogleSignInButton";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [devUsers, setDevUsers] = useState<DevUser[]>([]);
  const [showDevUsers, setShowDevUsers] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      navigate("/", { replace: true });
    }
  }, [isAuthenticated, authLoading, navigate]);

  useEffect(() => {
    // Fetch dev users for quick login
    authService
      .getDevUsers()
      .then((data) => {
        setDevUsers(data.users);
      })
      .catch(() => {
        // Dev users endpoint not available, that's fine
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Login failed. Please check your credentials.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = (user: DevUser) => {
    setUsername(user.email);
    const defaultPasswords: Record<string, string> = {
      admin: "admin123",
      user: "user123",
      demo: "demo123",
    };
    setPassword(defaultPasswords[user.username] || "");
  };

  if (authLoading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "100vh",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Card elevation={3} sx={{ width: "100%", borderRadius: 2 }}>
          <CardContent sx={{ p: 4 }}>
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                mb: 3,
              }}
            >
              <Avatar
                sx={{ m: 1, bgcolor: "primary.main", width: 56, height: 56 }}
              >
                <LockOutlinedIcon fontSize="large" />
              </Avatar>
              <Typography component="h1" variant="h5" fontWeight={600}>
                Sign In
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Welcome to the App Portal
              </Typography>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit} noValidate>
              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email"
                name="email"
                autoComplete="email"
                autoFocus
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isLoading}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type={showPassword ? "text" : "password"}
                id="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2, py: 1.5 }}
                disabled={isLoading || !username || !password}
              >
                {isLoading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  "Sign In"
                )}
              </Button>
            </Box>

            <GoogleSignInButton returnTo="/" />

            {devUsers.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Link
                  component="button"
                  variant="body2"
                  onClick={() => setShowDevUsers(!showDevUsers)}
                  sx={{ cursor: "pointer" }}
                >
                  {showDevUsers ? "Hide" : "Show"} dev users (quick login)
                </Link>
                <Collapse in={showDevUsers}>
                  <Box sx={{ mt: 2 }}>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      display="block"
                      sx={{ mb: 1 }}
                    >
                      Click to auto-fill credentials:
                    </Typography>
                    <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                      {devUsers.map((user) => (
                        <Chip
                          key={user.username}
                          label={`${user.username} (${user.role})`}
                          onClick={() => handleQuickLogin(user)}
                          color={user.role === "admin" ? "primary" : "default"}
                          variant="outlined"
                          size="small"
                          sx={{ cursor: "pointer" }}
                        />
                      ))}
                    </Box>
                  </Box>
                </Collapse>
              </Box>
            )}
          </CardContent>
        </Card>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
          Development Mode - No database required
        </Typography>
      </Box>
    </Container>
  );
}

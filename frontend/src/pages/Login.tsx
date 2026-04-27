import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";

import { useAuth } from "@/auth/store";

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
      navigate("/");
    } catch (err: any) {
      if (err?.status === 423) setError(t("login.locked"));
      else setError(t("login.invalid"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Paper component="form" onSubmit={onSubmit} sx={{ p: 3, width: 360 }}>
        <Stack spacing={2}>
          <Typography variant="h2" color="primary">
            {t("login.title")}
          </Typography>
          <TextField
            label={t("login.username")}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            size="small"
            fullWidth
          />
          <TextField
            label={t("login.password")}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            size="small"
            fullWidth
          />
          {error && <Alert severity="error">{error}</Alert>}
          <Button type="submit" variant="contained" disabled={busy} fullWidth>
            {t("login.submit")}
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}

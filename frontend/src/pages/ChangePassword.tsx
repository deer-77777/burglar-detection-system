import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";

import { api } from "@/api/client";
import { useAuth } from "@/auth/store";

export default function ChangePassword() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const refresh = useAuth((s) => s.refresh);
  const [current, setCurrent] = useState("");
  const [pw1, setPw1] = useState("");
  const [pw2, setPw2] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    if (pw1.length < 8) return setErr(t("change_password.too_short"));
    if (pw1 !== pw2) return setErr(t("change_password.mismatch"));
    setBusy(true);
    try {
      await api.post("/api/auth/change-password", { current_password: current, new_password: pw1 });
      await refresh();
      navigate("/");
    } catch (e: any) {
      setErr(e.message ?? t("common.error_generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Paper component="form" onSubmit={onSubmit} sx={{ p: 3, width: 360 }}>
        <Stack spacing={2}>
          <Typography variant="h2" color="primary">
            {t("change_password.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("login.must_change")}
          </Typography>
          <TextField
            label={t("change_password.current")}
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            size="small"
            fullWidth
          />
          <TextField
            label={t("change_password.new")}
            type="password"
            value={pw1}
            onChange={(e) => setPw1(e.target.value)}
            size="small"
            fullWidth
          />
          <TextField
            label={t("change_password.confirm")}
            type="password"
            value={pw2}
            onChange={(e) => setPw2(e.target.value)}
            size="small"
            fullWidth
          />
          {err && <Alert severity="error">{err}</Alert>}
          <Button type="submit" variant="contained" disabled={busy} fullWidth>
            {t("change_password.submit")}
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}

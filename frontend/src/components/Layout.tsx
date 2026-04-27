import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  AppBar,
  Box,
  Button,
  Container,
  MenuItem,
  Select,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";

import { useAuth } from "@/auth/store";

export default function Layout() {
  const { t, i18n } = useTranslation();
  const { me, logout } = useAuth();
  const navigate = useNavigate();

  const navItem = (to: string, label: string, show = true) =>
    show ? (
      <Button
        key={to}
        component={NavLink}
        to={to}
        end={to === "/"}
        sx={{
          color: "text.primary",
          textTransform: "none",
          "&.active": { bgcolor: "primary.main", color: "primary.contrastText" },
        }}
      >
        {label}
      </Button>
    ) : null;

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <AppBar
        position="static"
        color="inherit"
        sx={{ borderBottom: "1px solid", borderColor: "divider", bgcolor: "background.paper" }}
      >
        <Toolbar variant="dense" sx={{ gap: 1 }}>
          <Typography variant="h4" sx={{ color: "primary.main", mr: 3 }}>
            {t("app.title")}
          </Typography>
          <Stack direction="row" spacing={0.5}>
            {navItem("/", t("nav.dashboard"))}
            {navItem("/cameras", t("nav.cameras"), me?.permissions.manage_cameras)}
            {navItem("/groups", t("nav.groups"), me?.permissions.manage_groups)}
            {navItem("/history", t("nav.history"))}
            {navItem("/users", t("nav.users"), me?.permissions.manage_users)}
          </Stack>
          <Box sx={{ flexGrow: 1 }} />
          <Select
            size="small"
            value={i18n.language.startsWith("ja") ? "ja" : "en"}
            onChange={(e) => i18n.changeLanguage(e.target.value)}
            sx={{ minWidth: 64 }}
          >
            <MenuItem value="en">EN</MenuItem>
            <MenuItem value="ja">JA</MenuItem>
          </Select>
          <Typography variant="body2" color="text.secondary">
            {me?.username}
          </Typography>
          <Button
            size="small"
            variant="outlined"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            {t("nav.logout")}
          </Button>
        </Toolbar>
      </AppBar>
      <Container maxWidth={false} sx={{ flex: 1, py: 2 }}>
        <Outlet />
      </Container>
    </Box>
  );
}

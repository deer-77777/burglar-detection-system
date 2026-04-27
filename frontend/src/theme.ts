import { createTheme } from "@mui/material/styles";

// Tokens come from §6.6 of the spec.
const theme = createTheme({
  palette: {
    primary: { main: "#1F3864" },
    error: { main: "#C0392B" },
    success: { main: "#1E8449" },
    background: { default: "#F5F7FB", paper: "#FFFFFF" },
    text: { primary: "#1A1A1A", secondary: "#595959" },
  },
  typography: {
    fontFamily: ['Inter', 'system-ui', 'sans-serif'].join(","),
    fontSize: 16,
    h1: { fontSize: 24, fontWeight: 600 },
    h2: { fontSize: 20, fontWeight: 600 },
    h3: { fontSize: 18, fontWeight: 600 },
    h4: { fontSize: 16, fontWeight: 600 },
    body2: { fontSize: 14 },
  },
  shape: { borderRadius: 6 },
  components: {
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiPaper: { defaultProps: { elevation: 0 }, styleOverrides: { root: { border: "1px solid #E5E7EB" } } },
  },
});

export default theme;

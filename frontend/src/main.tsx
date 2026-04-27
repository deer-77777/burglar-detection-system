import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, CssBaseline } from "@mui/material";

import "./index.css";
import i18n from "./i18n";
import App from "./App";
import theme from "./theme";
import { useToast } from "./hooks/useToast";

const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onError: (err) => {
      const raw = err instanceof Error ? err.message : String(err);
      // Skip 401 — api client + auth store already navigate to /login.
      if (raw === "unauthenticated") return;
      // Translate ERR_* codes via i18next; unknown keys pass through.
      const msg = /^ERR_[A-Z_]+$/.test(raw) ? i18n.t(raw) : raw;
      useToast.getState().error(msg);
    },
  }),
  defaultOptions: { queries: { staleTime: 5_000, refetchOnWindowFocus: false } },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>,
);

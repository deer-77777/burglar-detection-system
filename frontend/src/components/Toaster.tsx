import { Alert, Snackbar, Stack } from "@mui/material";

import { useToast } from "@/hooks/useToast";

export default function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <Stack
      sx={{
        position: "fixed",
        bottom: 16,
        right: 16,
        zIndex: (theme) => theme.zIndex.snackbar,
      }}
      spacing={1}
    >
      {toasts.map((t) => (
        <Snackbar
          key={t.id}
          open
          autoHideDuration={5000}
          onClose={(_, reason) => {
            if (reason === "clickaway") return;
            dismiss(t.id);
          }}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
          sx={{ position: "static", transform: "none" }}
        >
          <Alert severity={t.severity} variant="filled" onClose={() => dismiss(t.id)}>
            {t.message}
          </Alert>
        </Snackbar>
      ))}
    </Stack>
  );
}

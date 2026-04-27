import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Pagination,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { api } from "@/api/client";

type EventRow = {
  id: number;
  camera_id: number;
  group_path: string;
  person_global_id: string;
  event_type: "DWELL" | "REVISIT";
  start_time: string;
  end_time: string;
  duration_sec: number | null;
  appearance_count: number | null;
  snapshot_path: string | null;
  clip_path: string | null;
  review_status: "NEW" | "REVIEWED" | "FALSE_POSITIVE" | "ESCALATED";
  review_notes: string | null;
};

type Page = { total: number; items: EventRow[] };
const STATUSES = ["NEW", "REVIEWED", "FALSE_POSITIVE", "ESCALATED"] as const;

export default function History() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [filters, setFilters] = useState({
    event_type: "",
    review_status: "",
    person_global_id: "",
    notes_q: "",
    start: "",
    end: "",
    page: 1,
    page_size: 50,
  });
  const [selected, setSelected] = useState<EventRow | null>(null);
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState<EventRow["review_status"]>("NEW");

  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => v !== "" && v != null && params.set(k, String(v)));

  const events = useQuery({
    queryKey: ["events", filters],
    queryFn: () => api.get<Page>(`/api/events?${params.toString()}`),
  });

  const review = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { review_status: EventRow["review_status"]; review_notes: string } }) =>
      api.patch<EventRow>(`/api/events/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["events"] }),
  });

  const totalPages = Math.max(1, Math.ceil((events.data?.total ?? 0) / filters.page_size));

  return (
    <Box>
      <Typography variant="h2" sx={{ mb: 2 }}>
        {t("history.title")}
      </Typography>

      <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 2 }}>
        <TextField
          type="datetime-local"
          size="small"
          label={t("history.filter_date") + " (start)"}
          value={filters.start}
          onChange={(e) => setFilters({ ...filters, start: e.target.value, page: 1 })}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          type="datetime-local"
          size="small"
          label={t("history.filter_date") + " (end)"}
          value={filters.end}
          onChange={(e) => setFilters({ ...filters, end: e.target.value, page: 1 })}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          select
          size="small"
          label={t("history.filter_type")}
          value={filters.event_type}
          onChange={(e) => setFilters({ ...filters, event_type: e.target.value, page: 1 })}
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="">*</MenuItem>
          <MenuItem value="DWELL">{t("history.type.DWELL")}</MenuItem>
          <MenuItem value="REVISIT">{t("history.type.REVISIT")}</MenuItem>
        </TextField>
        <TextField
          select
          size="small"
          label={t("history.filter_status")}
          value={filters.review_status}
          onChange={(e) => setFilters({ ...filters, review_status: e.target.value, page: 1 })}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">*</MenuItem>
          {STATUSES.map((s) => (
            <MenuItem key={s} value={s}>
              {t(`history.status.${s}`)}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          size="small"
          label={t("history.search_pgid")}
          value={filters.person_global_id}
          onChange={(e) => setFilters({ ...filters, person_global_id: e.target.value, page: 1 })}
        />
        <TextField
          size="small"
          label={t("history.search_notes")}
          value={filters.notes_q}
          onChange={(e) => setFilters({ ...filters, notes_q: e.target.value, page: 1 })}
        />
      </Stack>

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "background.default" }}>
              <TableCell>Time</TableCell>
              <TableCell>Camera</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Person</TableCell>
              <TableCell>Detail</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(events.data?.items ?? []).map((e) => (
              <TableRow
                key={e.id}
                hover
                sx={{ cursor: "pointer" }}
                onClick={() => {
                  setSelected(e);
                  setNotes(e.review_notes ?? "");
                  setStatus(e.review_status);
                }}
              >
                <TableCell>{e.start_time}</TableCell>
                <TableCell>{e.group_path || `#${e.camera_id}`}</TableCell>
                <TableCell>{t(`history.type.${e.event_type}`)}</TableCell>
                <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{e.person_global_id}</TableCell>
                <TableCell>
                  {e.event_type === "DWELL" ? `${e.duration_sec ?? 0}s` : `×${e.appearance_count ?? 0}`}
                </TableCell>
                <TableCell>{t(`history.status.${e.review_status}`)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Stack direction="row" sx={{ mt: 2 }} justifyContent="center">
        <Pagination
          count={totalPages}
          page={filters.page}
          onChange={(_, p) => setFilters({ ...filters, page: p })}
        />
      </Stack>

      <Dialog open={!!selected} onClose={() => setSelected(null)} maxWidth="md" fullWidth>
        {selected && (
          <>
            <DialogTitle>
              {t(`history.type.${selected.event_type}`)} — {selected.start_time}
            </DialogTitle>
            <DialogContent dividers>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                {selected.snapshot_path && (
                  <Box
                    component="img"
                    src={`/api/events/${selected.id}/snapshot`}
                    alt="snapshot"
                    sx={{ width: "100%", maxWidth: 480, borderRadius: 1, border: 1, borderColor: "divider" }}
                  />
                )}
                {selected.clip_path && (
                  <Box
                    component="video"
                    src={`/api/events/${selected.id}/clip`}
                    controls
                    sx={{ width: "100%", maxWidth: 480, borderRadius: 1, border: 1, borderColor: "divider" }}
                  />
                )}
              </Stack>
              <Stack spacing={2} sx={{ mt: 2 }}>
                <TextField
                  select
                  size="small"
                  label={t("history.review_status")}
                  value={status}
                  onChange={(e) => setStatus(e.target.value as EventRow["review_status"])}
                  sx={{ maxWidth: 240 }}
                >
                  {STATUSES.map((s) => (
                    <MenuItem key={s} value={s}>
                      {t(`history.status.${s}`)}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  label={t("history.review_notes")}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  multiline
                  rows={3}
                  fullWidth
                />
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelected(null)}>{t("common.cancel")}</Button>
              <Button
                variant="contained"
                onClick={() =>
                  review.mutate(
                    { id: selected.id, body: { review_status: status, review_notes: notes } },
                    { onSuccess: () => setSelected(null) },
                  )
                }
              >
                {t("history.save")}
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
}

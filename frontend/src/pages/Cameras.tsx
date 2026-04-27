import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  FormControlLabel,
  Grid2 as Grid,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";

import { api } from "@/api/client";
import { buildGroupPaths, type Group } from "@/api/groups";

type Camera = {
  id: number;
  name: string;
  resolution_w: number;
  resolution_h: number;
  group_id: number | null;
  display_enabled: boolean;
  dwell_limit_sec: number;
  count_limit: number;
  count_window_sec: number;
  status: string;
};

type TestResult = {
  success: boolean;
  error_code?: string | null;
  width?: number | null;
  height?: number | null;
};

const empty = {
  name: "Camera",
  rtsp_url: "",
  resolution_w: 1920,
  resolution_h: 1080,
  group_id: null as number | null,
  display_enabled: true,
  dwell_limit_sec: 180,
  count_limit: 3,
  count_window_sec: 86400,
};

export default function Cameras() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const cameras = useQuery({ queryKey: ["cameras"], queryFn: () => api.get<Camera[]>("/api/cameras") });
  const groups = useQuery({ queryKey: ["groups"], queryFn: () => api.get<Group[]>("/api/groups").catch(() => []) });
  const groupPath = useMemo(() => buildGroupPaths(groups.data), [groups.data]);
  const [draft, setDraft] = useState(empty);
  const [test, setTest] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const create = useMutation({
    mutationFn: (body: typeof empty) => api.post<Camera>("/api/cameras", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cameras"] });
      setDraft(empty);
      setTest(null);
    },
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<typeof empty> }) =>
      api.patch<Camera>(`/api/cameras/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cameras"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/api/cameras/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cameras"] }),
  });

  type FieldErrors = {
    name?: string;
    rtsp_url?: string;
    resolution_w?: string;
    resolution_h?: string;
    dwell_limit_sec?: string;
    count_limit?: string;
    count_window_sec?: string;
  };
  const [errors, setErrors] = useState<FieldErrors>({});

  function validate(): boolean {
    const next: FieldErrors = {};
    if (!draft.name.trim()) next.name = t("validation.required");
    if (editingId == null && !/^rtsps?:\/\//i.test(draft.rtsp_url.trim())) {
      next.rtsp_url = t("validation.rtsp_format");
    }
    if (draft.rtsp_url && !/^rtsps?:\/\//i.test(draft.rtsp_url.trim())) {
      next.rtsp_url = t("validation.rtsp_format");
    }
    if (draft.resolution_w < 16 || draft.resolution_w > 7680) next.resolution_w = t("validation.resolution_range");
    if (draft.resolution_h < 16 || draft.resolution_h > 7680) next.resolution_h = t("validation.resolution_range");
    if (!Number.isInteger(draft.dwell_limit_sec) || draft.dwell_limit_sec < 1)
      next.dwell_limit_sec = t("validation.positive_int");
    if (!Number.isInteger(draft.count_limit) || draft.count_limit < 1)
      next.count_limit = t("validation.positive_int");
    if (!Number.isInteger(draft.count_window_sec) || draft.count_window_sec < 1)
      next.count_window_sec = t("validation.positive_int");
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function runTest() {
    if (!/^rtsps?:\/\//i.test(draft.rtsp_url.trim())) {
      setErrors({ ...errors, rtsp_url: t("validation.rtsp_format") });
      return;
    }
    setTesting(true);
    try {
      const res = await api.post<TestResult>("/api/cameras/test", { rtsp_url: draft.rtsp_url });
      setTest(res);
    } catch (e: any) {
      setTest({ success: false, error_code: e?.message ?? "ERR_UNKNOWN" });
    } finally {
      setTesting(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    if (editingId != null) {
      const body: any = { ...draft };
      if (!body.rtsp_url) delete body.rtsp_url;
      update.mutate({ id: editingId, body });
      setEditingId(null);
      setDraft(empty);
      setTest(null);
      setErrors({});
    } else {
      create.mutate(draft);
    }
  }

  return (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Typography variant="h2" sx={{ mb: 2 }}>
          {t("cameras.title")}
        </Typography>
        <Paper>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: "background.default" }}>
                <TableCell>{t("cameras.name")}</TableCell>
                <TableCell>{t("cameras.resolution")}</TableCell>
                <TableCell>{t("cameras.group")}</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {(cameras.data ?? []).map((c) => (
                <TableRow key={c.id} hover>
                  <TableCell>{c.name}</TableCell>
                  <TableCell>{c.resolution_w}×{c.resolution_h}</TableCell>
                  <TableCell>{c.group_id != null ? groupPath[c.group_id] ?? "—" : "—"}</TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => {
                        setEditingId(c.id);
                        setDraft({
                          name: c.name,
                          rtsp_url: "",
                          resolution_w: c.resolution_w,
                          resolution_h: c.resolution_h,
                          group_id: c.group_id,
                          display_enabled: c.display_enabled,
                          dwell_limit_sec: c.dwell_limit_sec,
                          count_limit: c.count_limit,
                          count_window_sec: c.count_window_sec,
                        });
                      }}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => {
                        if (confirm(t("cameras.delete_confirm") ?? "")) remove.mutate(c.id);
                      }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      </Grid>

      <Grid size={{ xs: 12, lg: 6 }}>
        <Paper component="form" onSubmit={onSubmit} sx={{ p: 2 }}>
          <Stack spacing={2}>
            <Typography variant="h3">{editingId == null ? t("cameras.add") : t("common.edit")}</Typography>

            <TextField
              label={t("cameras.name")}
              value={draft.name}
              onChange={(e) => {
                setDraft({ ...draft, name: e.target.value });
                if (errors.name) setErrors({ ...errors, name: undefined });
              }}
              size="small"
              fullWidth
              required
              inputProps={{ maxLength: 128 }}
              error={!!errors.name}
              helperText={errors.name}
            />
            <TextField
              label={t("cameras.rtsp_url")}
              value={draft.rtsp_url}
              onChange={(e) => {
                setDraft({ ...draft, rtsp_url: e.target.value });
                if (errors.rtsp_url) setErrors({ ...errors, rtsp_url: undefined });
              }}
              placeholder="rtsp://user:pass@host:554/stream"
              size="small"
              fullWidth
              error={!!errors.rtsp_url}
              helperText={errors.rtsp_url}
            />

            <Stack direction="row" spacing={1}>
              <TextField
                label="W"
                type="number"
                size="small"
                value={draft.resolution_w}
                onChange={(e) => {
                  setDraft({ ...draft, resolution_w: Number(e.target.value) });
                  if (errors.resolution_w) setErrors({ ...errors, resolution_w: undefined });
                }}
                inputProps={{ min: 16, max: 7680 }}
                error={!!errors.resolution_w}
                helperText={errors.resolution_w}
                sx={{ width: 130 }}
              />
              <TextField
                label="H"
                type="number"
                size="small"
                value={draft.resolution_h}
                onChange={(e) => {
                  setDraft({ ...draft, resolution_h: Number(e.target.value) });
                  if (errors.resolution_h) setErrors({ ...errors, resolution_h: undefined });
                }}
                inputProps={{ min: 16, max: 7680 }}
                error={!!errors.resolution_h}
                helperText={errors.resolution_h}
                sx={{ width: 130 }}
              />
              <TextField
                select
                label={t("cameras.group")}
                size="small"
                value={draft.group_id ?? ""}
                onChange={(e) =>
                  setDraft({ ...draft, group_id: e.target.value ? Number(e.target.value) : null })
                }
                sx={{ flex: 1 }}
              >
                <MenuItem value="">—</MenuItem>
                {(groups.data ?? []).map((g) => (
                  <MenuItem key={g.id} value={g.id}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip
                        size="small"
                        variant="outlined"
                        label={t(`groups.level.${g.level}`)}
                        sx={{ height: 20, fontSize: 11 }}
                      />
                      <Typography variant="body2">{groupPath[g.id]}</Typography>
                    </Stack>
                  </MenuItem>
                ))}
              </TextField>
            </Stack>

            <Stack direction="row" spacing={1}>
              <TextField
                label={t("cameras.dwell")}
                type="number"
                size="small"
                value={draft.dwell_limit_sec}
                onChange={(e) => {
                  setDraft({ ...draft, dwell_limit_sec: Number(e.target.value) });
                  if (errors.dwell_limit_sec) setErrors({ ...errors, dwell_limit_sec: undefined });
                }}
                inputProps={{ min: 1 }}
                error={!!errors.dwell_limit_sec}
                helperText={errors.dwell_limit_sec}
                sx={{ flex: 1 }}
              />
              <TextField
                label={t("cameras.count_limit")}
                type="number"
                size="small"
                value={draft.count_limit}
                onChange={(e) => {
                  setDraft({ ...draft, count_limit: Number(e.target.value) });
                  if (errors.count_limit) setErrors({ ...errors, count_limit: undefined });
                }}
                inputProps={{ min: 1 }}
                error={!!errors.count_limit}
                helperText={errors.count_limit}
                sx={{ width: 150 }}
              />
              <TextField
                label={t("cameras.count_window")}
                type="number"
                size="small"
                value={draft.count_window_sec}
                onChange={(e) => {
                  setDraft({ ...draft, count_window_sec: Number(e.target.value) });
                  if (errors.count_window_sec) setErrors({ ...errors, count_window_sec: undefined });
                }}
                inputProps={{ min: 1 }}
                error={!!errors.count_window_sec}
                helperText={errors.count_window_sec}
                sx={{ width: 170 }}
              />
            </Stack>

            <FormControlLabel
              control={
                <Switch
                  checked={draft.display_enabled}
                  onChange={(e) => setDraft({ ...draft, display_enabled: e.target.checked })}
                />
              }
              label={t("cameras.display")}
            />

            <Stack direction="row" alignItems="center" spacing={2}>
              <Button
                type="button"
                variant="outlined"
                disabled={!draft.rtsp_url || testing}
                onClick={runTest}
              >
                {testing ? t("cameras.testing") : t("cameras.test_connection")}
              </Button>
              {test && (
                <Box sx={{ flex: 1 }}>
                  {test.success ? (
                    <Alert severity="success" sx={{ py: 0 }}>
                      {t("cameras.test_ok", { w: test.width, h: test.height })}
                    </Alert>
                  ) : (
                    <Alert severity="error" sx={{ py: 0 }}>
                      {t(test.error_code ?? "ERR_UNKNOWN")}
                    </Alert>
                  )}
                </Box>
              )}
            </Stack>

            <Stack direction="row" spacing={1}>
              <Button
                type="submit"
                variant="contained"
                disabled={editingId == null && !test?.success}
              >
                {t("cameras.save")}
              </Button>
              {editingId != null && (
                <Button
                  variant="text"
                  color="inherit"
                  onClick={() => {
                    setEditingId(null);
                    setDraft(empty);
                    setTest(null);
                  }}
                >
                  {t("common.cancel")}
                </Button>
              )}
            </Stack>
          </Stack>
        </Paper>
      </Grid>
    </Grid>
  );
}

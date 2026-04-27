import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Checkbox,
  Chip,
  FormControlLabel,
  Grid2 as Grid,
  IconButton,
  MenuItem,
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
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { api } from "@/api/client";
import { buildGroupPaths, type Group } from "@/api/groups";

type User = {
  id: number;
  username: string;
  language: string;
  can_manage_users: boolean;
  can_manage_groups: boolean;
  can_manage_cameras: boolean;
  must_change_password: boolean;
};

type Camera = { id: number; name: string };

const empty = {
  username: "",
  password: "",
  language: "en",
  can_manage_users: false,
  can_manage_groups: false,
  can_manage_cameras: false,
};

export default function Users() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["users"], queryFn: () => api.get<User[]>("/api/users") });
  const groups = useQuery({ queryKey: ["groups"], queryFn: () => api.get<Group[]>("/api/groups").catch(() => []) });
  const cameras = useQuery({ queryKey: ["cameras"], queryFn: () => api.get<Camera[]>("/api/cameras").catch(() => []) });
  const groupPath = useMemo(() => buildGroupPaths(groups.data), [groups.data]);
  const [draft, setDraft] = useState(empty);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [visGroups, setVisGroups] = useState<number[]>([]);
  const [visCameras, setVisCameras] = useState<number[]>([]);

  const create = useMutation({
    mutationFn: (b: typeof empty) => api.post<User>("/api/users", b),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<typeof empty> }) =>
      api.patch<User>(`/api/users/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/api/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const setVis = useMutation({
    mutationFn: (id: number) =>
      api.put(`/api/users/${id}/visibility`, { group_ids: visGroups, camera_ids: visCameras }),
  });

  function reset() {
    setEditingId(null);
    setDraft(empty);
    setVisGroups([]);
    setVisCameras([]);
    setErrors({});
  }

  const [errors, setErrors] = useState<{ username?: string; password?: string }>({});

  function validate(): boolean {
    const next: typeof errors = {};
    if (editingId == null) {
      if (draft.username.length < 3 || draft.username.length > 64) {
        next.username = t("validation.username_len");
      }
    }
    if (draft.password.length > 0 && (draft.password.length < 8 || draft.password.length > 128)) {
      next.password = t("validation.password_len");
    }
    if (editingId == null && draft.password.length === 0) {
      next.password = t("validation.required");
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    if (editingId != null) {
      const body: Partial<typeof empty> = { ...draft };
      if (!body.password) delete body.password;
      update.mutate({ id: editingId, body });
      setVis.mutate(editingId);
    } else {
      create.mutate(draft, {
        onSuccess: (u) => {
          if (visGroups.length || visCameras.length) {
            setVis.mutate(u.id);
          }
        },
      });
    }
    reset();
  }

  return (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Typography variant="h2" sx={{ mb: 2 }}>
          {t("users.title")}
        </Typography>
        <Paper>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: "background.default" }}>
                <TableCell>{t("users.username")}</TableCell>
                <TableCell>{t("users.permissions")}</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {(users.data ?? []).map((u) => (
                <TableRow key={u.id} hover>
                  <TableCell>{u.username}</TableCell>
                  <TableCell sx={{ fontSize: 12, color: "text.secondary" }}>
                    {u.can_manage_users && "U "}
                    {u.can_manage_groups && "G "}
                    {u.can_manage_cameras && "C"}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => {
                        setEditingId(u.id);
                        setDraft({
                          username: u.username,
                          password: "",
                          language: u.language,
                          can_manage_users: u.can_manage_users,
                          can_manage_groups: u.can_manage_groups,
                          can_manage_cameras: u.can_manage_cameras,
                        });
                      }}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => {
                        if (confirm(t("users.delete_confirm") ?? "")) remove.mutate(u.id);
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
            <Typography variant="h3">{editingId == null ? t("users.add") : t("common.edit")}</Typography>

            <TextField
              label={t("users.username")}
              size="small"
              value={draft.username}
              onChange={(e) => {
                setDraft({ ...draft, username: e.target.value });
                if (errors.username) setErrors({ ...errors, username: undefined });
              }}
              disabled={editingId != null}
              required
              fullWidth
              inputProps={{ minLength: 3, maxLength: 64 }}
              error={!!errors.username}
              helperText={errors.username}
            />
            <TextField
              label={t("users.password")}
              type="password"
              size="small"
              value={draft.password}
              onChange={(e) => {
                setDraft({ ...draft, password: e.target.value });
                if (errors.password) setErrors({ ...errors, password: undefined });
              }}
              required={editingId == null}
              fullWidth
              inputProps={{ minLength: 8, maxLength: 128 }}
              error={!!errors.password}
              helperText={errors.password ?? (editingId != null ? t("validation.password_len") + " (optional)" : undefined)}
            />
            <TextField
              select
              size="small"
              label={t("users.language")}
              value={draft.language}
              onChange={(e) => setDraft({ ...draft, language: e.target.value })}
              sx={{ maxWidth: 160 }}
            >
              <MenuItem value="en">EN</MenuItem>
              <MenuItem value="ja">JA</MenuItem>
            </TextField>

            <Box>
              <Typography variant="body2" fontWeight={500} gutterBottom>
                {t("users.permissions")}
              </Typography>
              <Stack>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={draft.can_manage_users}
                      onChange={(e) => setDraft({ ...draft, can_manage_users: e.target.checked })}
                    />
                  }
                  label={t("users.perm_users")}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={draft.can_manage_groups}
                      onChange={(e) => setDraft({ ...draft, can_manage_groups: e.target.checked })}
                    />
                  }
                  label={t("users.perm_groups")}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={draft.can_manage_cameras}
                      onChange={(e) => setDraft({ ...draft, can_manage_cameras: e.target.checked })}
                    />
                  }
                  label={t("users.perm_cameras")}
                />
              </Stack>
            </Box>

            <Accordion variant="outlined">
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2">{t("users.visibility")}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="body2" fontWeight={500} gutterBottom>
                      {t("nav.groups")}
                    </Typography>
                    <Stack>
                      {(groups.data ?? []).map((g) => (
                        <FormControlLabel
                          key={g.id}
                          control={
                            <Checkbox
                              size="small"
                              checked={visGroups.includes(g.id)}
                              onChange={(e) =>
                                setVisGroups((p) =>
                                  e.target.checked ? [...p, g.id] : p.filter((x) => x !== g.id),
                                )
                              }
                            />
                          }
                          label={
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Chip
                                size="small"
                                variant="outlined"
                                label={t(`groups.level.${g.level}`)}
                                sx={{ height: 18, fontSize: 10 }}
                              />
                              <Typography variant="body2">{groupPath[g.id]}</Typography>
                            </Stack>
                          }
                        />
                      ))}
                    </Stack>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="body2" fontWeight={500} gutterBottom>
                      {t("nav.cameras")}
                    </Typography>
                    <Stack>
                      {(cameras.data ?? []).map((c) => (
                        <FormControlLabel
                          key={c.id}
                          control={
                            <Checkbox
                              size="small"
                              checked={visCameras.includes(c.id)}
                              onChange={(e) =>
                                setVisCameras((p) =>
                                  e.target.checked ? [...p, c.id] : p.filter((x) => x !== c.id),
                                )
                              }
                            />
                          }
                          label={<Typography variant="body2">{c.name}</Typography>}
                        />
                      ))}
                    </Stack>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            <Stack direction="row" spacing={1}>
              <Button type="submit" variant="contained">
                {t("users.save")}
              </Button>
              {editingId != null && (
                <Button variant="text" color="inherit" onClick={reset}>
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

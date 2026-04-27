import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Chip,
  Grid2 as Grid,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import VideocamIcon from "@mui/icons-material/Videocam";
import LinkOffIcon from "@mui/icons-material/LinkOff";

import { api } from "@/api/client";
import { buildGroupPaths, type Group as GroupT } from "@/api/groups";
import { useAuth } from "@/auth/store";

type Group = GroupT & { sort_order: number };

type Camera = {
  id: number;
  name: string;
  group_id: number | null;
};

export default function Groups() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const me = useAuth((s) => s.me);
  const canManageCameras = !!me?.permissions.manage_cameras;

  const groups = useQuery({ queryKey: ["groups"], queryFn: () => api.get<Group[]>("/api/groups") });
  const cameras = useQuery({
    queryKey: ["cameras"],
    queryFn: () => api.get<Camera[]>("/api/cameras").catch(() => [] as Camera[]),
  });

  const [editing, setEditing] = useState<Group | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftParent, setDraftParent] = useState<number | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (b: { name: string; parent_id: number | null }) =>
      api.post<Group>("/api/groups", { ...b, sort_order: 0 }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }),
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { name: string; parent_id: number | null; sort_order: number } }) =>
      api.patch<Group>(`/api/groups/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/api/groups/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }),
  });
  const setCameraGroup = useMutation({
    mutationFn: ({ id, group_id }: { id: number; group_id: number | null }) =>
      api.patch<Camera>(`/api/cameras/${id}`, { group_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cameras"] }),
  });

  const tree = useMemo(() => {
    const list = groups.data ?? [];
    const byParent: Record<string, Group[]> = {};
    for (const g of list) {
      const k = String(g.parent_id ?? "root");
      (byParent[k] ??= []).push(g);
    }
    Object.values(byParent).forEach((arr) =>
      arr.sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)),
    );
    return byParent;
  }, [groups.data]);

  const groupPath = useMemo(() => buildGroupPaths(groups.data), [groups.data]);

  const camerasByGroup = useMemo(() => {
    const map: Record<string, Camera[]> = {};
    for (const c of cameras.data ?? []) {
      const k = c.group_id != null ? String(c.group_id) : "unassigned";
      (map[k] ??= []).push(c);
    }
    Object.values(map).forEach((arr) => arr.sort((a, b) => a.name.localeCompare(b.name)));
    return map;
  }, [cameras.data]);
  const unassigned = camerasByGroup["unassigned"] ?? [];

  const parentLevel = useMemo(() => {
    if (draftParent == null) return 0;
    const p = (groups.data ?? []).find((g) => g.id === draftParent);
    return p?.level ?? 0;
  }, [draftParent, groups.data]);
  const draftLevel = parentLevel + 1;

  const headingKey = editing
    ? "groups.rename"
    : draftLevel === 1
    ? "groups.add_store"
    : draftLevel === 2
    ? "groups.add_floor"
    : "groups.add_section";

  function renderCameraRow(c: Camera, currentGroupId: number | null) {
    const moveOptions = (groups.data ?? []).filter((g) => g.id !== currentGroupId);
    return (
      <Stack
        key={c.id}
        direction="row"
        alignItems="center"
        spacing={1}
        sx={{ py: 0.25, pl: 1, borderLeft: "2px solid", borderColor: "divider" }}
      >
        <VideocamIcon fontSize="small" sx={{ color: "text.secondary" }} />
        <Typography variant="body2">{c.name}</Typography>
        <Box sx={{ flex: 1 }} />
        {canManageCameras && (
          <>
            <TextField
              select
              size="small"
              value=""
              onChange={(e) => {
                const next = e.target.value === "" ? null : Number(e.target.value);
                setCameraGroup.mutate({ id: c.id, group_id: next });
              }}
              SelectProps={{ displayEmpty: true, renderValue: () => t("groups.move_to") }}
              sx={{ width: 140 }}
            >
              {moveOptions.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  <Typography variant="body2">
                    [{t(`groups.level.${g.level}`)}] {groupPath[g.id]}
                  </Typography>
                </MenuItem>
              ))}
            </TextField>
            {currentGroupId != null && (
              <Tooltip title={t("groups.detach") ?? ""}>
                <IconButton
                  size="small"
                  onClick={() => setCameraGroup.mutate({ id: c.id, group_id: null })}
                >
                  <LinkOffIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </>
        )}
      </Stack>
    );
  }

  function renderNode(g: Group): JSX.Element {
    const children = tree[String(g.id)] ?? [];
    const groupCameras = camerasByGroup[String(g.id)] ?? [];
    return (
      <Box key={g.id}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ py: 0.5 }}>
          <Chip
            size="small"
            variant="outlined"
            label={t(`groups.level.${g.level}`)}
            sx={{ fontSize: 11 }}
          />
          <Typography variant="body2" fontWeight={500}>
            {g.name}
          </Typography>
          {groupCameras.length > 0 && (
            <Chip
              size="small"
              icon={<VideocamIcon />}
              label={groupCameras.length}
              variant="outlined"
              sx={{ height: 20, fontSize: 11 }}
            />
          )}
          <Box sx={{ flex: 1 }} />
          <IconButton
            size="small"
            onClick={() => {
              setEditing(g);
              setDraftName(g.name);
              setDraftParent(g.parent_id);
            }}
          >
            <EditIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            color="error"
            onClick={() => {
              if (confirm(t("groups.delete_confirm") ?? "")) remove.mutate(g.id);
            }}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Stack>
        {(groupCameras.length > 0 || children.length > 0) && (
          <Box sx={{ ml: 3, borderLeft: "1px solid", borderColor: "divider", pl: 2 }}>
            {groupCameras.map((c) => renderCameraRow(c, g.id))}
            {children.map(renderNode)}
          </Box>
        )}
      </Box>
    );
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = draftName.trim();
    if (trimmed.length < 1 || trimmed.length > 128) {
      setNameError(t("validation.name_len"));
      return;
    }
    setNameError(null);
    if (editing) {
      update.mutate({
        id: editing.id,
        body: { name: trimmed, parent_id: draftParent, sort_order: editing.sort_order },
      });
      setEditing(null);
    } else {
      create.mutate({ name: trimmed, parent_id: draftParent });
    }
    setDraftName("");
    setDraftParent(null);
  }

  return (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Typography variant="h2" sx={{ mb: 2 }}>
          {t("groups.title")}
        </Typography>
        <Paper sx={{ p: 2 }}>
          {(tree["root"] ?? []).length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              —
            </Typography>
          ) : (
            (tree["root"] ?? []).map(renderNode)
          )}
        </Paper>
      </Grid>

      <Grid size={{ xs: 12, lg: 6 }}>
        <Stack spacing={3}>
          <Paper component="form" onSubmit={onSubmit} sx={{ p: 2 }}>
            <Stack spacing={2}>
              <Typography variant="h3">{t(headingKey)}</Typography>
              <TextField
                label={t("groups.title")}
                value={draftName}
                onChange={(e) => {
                  setDraftName(e.target.value);
                  if (nameError) setNameError(null);
                }}
                size="small"
                required
                fullWidth
                inputProps={{ minLength: 1, maxLength: 128 }}
                error={!!nameError}
                helperText={nameError}
              />
              <TextField
                select
                size="small"
                label={t("groups.parent")}
                value={draftParent ?? ""}
                onChange={(e) => setDraftParent(e.target.value ? Number(e.target.value) : null)}
                fullWidth
                disabled={!!editing}
              >
                <MenuItem value="">{t("groups.no_parent")}</MenuItem>
                {(groups.data ?? [])
                  .filter((g) => g.level < 3)
                  .map((g) => (
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
              <Stack direction="row" spacing={1}>
                <Button type="submit" variant="contained">
                  {t("common.save")}
                </Button>
                {editing && (
                  <Button
                    variant="text"
                    color="inherit"
                    onClick={() => {
                      setEditing(null);
                      setDraftName("");
                      setDraftParent(null);
                    }}
                  >
                    {t("common.cancel")}
                  </Button>
                )}
              </Stack>
            </Stack>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Stack spacing={1}>
              <Typography variant="h3">{t("groups.unassigned_cameras")}</Typography>
              {unassigned.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("groups.no_unassigned")}
                </Typography>
              ) : (
                unassigned.map((c) => (
                  <Stack
                    key={c.id}
                    direction="row"
                    alignItems="center"
                    spacing={1}
                    sx={{ py: 0.25 }}
                  >
                    <VideocamIcon fontSize="small" sx={{ color: "text.secondary" }} />
                    <Typography variant="body2">{c.name}</Typography>
                    <Box sx={{ flex: 1 }} />
                    {canManageCameras && (
                      <TextField
                        select
                        size="small"
                        value=""
                        onChange={(e) => {
                          const gid = Number(e.target.value);
                          if (gid) setCameraGroup.mutate({ id: c.id, group_id: gid });
                        }}
                        SelectProps={{
                          displayEmpty: true,
                          renderValue: () => t("groups.attach_to"),
                        }}
                        sx={{ width: 200 }}
                      >
                        {(groups.data ?? []).map((g) => (
                          <MenuItem key={g.id} value={g.id}>
                            <Typography variant="body2">
                              [{t(`groups.level.${g.level}`)}] {groupPath[g.id]}
                            </Typography>
                          </MenuItem>
                        ))}
                      </TextField>
                    )}
                  </Stack>
                ))
              )}
            </Stack>
          </Paper>
        </Stack>
      </Grid>
    </Grid>
  );
}

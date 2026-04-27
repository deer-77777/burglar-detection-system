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
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";

import { api } from "@/api/client";
import { buildGroupPaths, type Group as GroupT } from "@/api/groups";

type Group = GroupT & { sort_order: number };

export default function Groups() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const groups = useQuery({ queryKey: ["groups"], queryFn: () => api.get<Group[]>("/api/groups") });
  const [editing, setEditing] = useState<Group | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftParent, setDraftParent] = useState<number | null>(null);

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

  // Draft level = parent.level + 1, or 1 if no parent.
  const parentLevel = useMemo(() => {
    if (draftParent == null) return 0; // → adding L1 (Store)
    const p = (groups.data ?? []).find((g) => g.id === draftParent);
    return p?.level ?? 0;
  }, [draftParent, groups.data]);
  const draftLevel = parentLevel + 1; // 1 / 2 / 3

  const headingKey = editing
    ? "groups.rename"
    : draftLevel === 1
    ? "groups.add_store"
    : draftLevel === 2
    ? "groups.add_floor"
    : "groups.add_section";

  function renderNode(g: Group): JSX.Element {
    const children = tree[String(g.id)] ?? [];
    return (
      <Box key={g.id} sx={{ ml: g.level === 1 ? 0 : 0 }}>
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
        {children.length > 0 && (
          <Box sx={{ ml: 3, borderLeft: "1px solid", borderColor: "divider", pl: 2 }}>
            {children.map(renderNode)}
          </Box>
        )}
      </Box>
    );
  }

  const [nameError, setNameError] = useState<string | null>(null);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = draftName.trim();
    if (trimmed.length < 1 || trimmed.length > 128) {
      setNameError(t("validation.name_len"));
      return;
    }
    setNameError(null);
    if (editing) {
      update.mutate({ id: editing.id, body: { name: trimmed, parent_id: draftParent, sort_order: editing.sort_order } });
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
        <Paper sx={{ p: 2 }}>{(tree["root"] ?? []).map(renderNode)}</Paper>
      </Grid>
      <Grid size={{ xs: 12, lg: 6 }}>
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
      </Grid>
    </Grid>
  );
}

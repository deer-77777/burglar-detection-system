import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Box,
  Checkbox,
  Chip,
  FormControlLabel,
  Grid2 as Grid,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import ViewModuleIcon from "@mui/icons-material/ViewModule";
import AccountTreeIcon from "@mui/icons-material/AccountTree";

import { api } from "@/api/client";
import { buildGroupPaths, type Group } from "@/api/groups";
import CameraCard from "@/components/CameraCard";
import { useDashboardEvents } from "@/hooks/useDashboardEvents";

type Camera = {
  id: number;
  name: string;
  group_id: number | null;
  display_enabled: boolean;
  status: "live" | "disabled" | "reconnecting" | "error" | "pending";
  last_status_at: string | null;
};

type ViewMode = "grouped" | "flat";
const VIEW_KEY = "dashboard.viewMode";

function readSavedView(): ViewMode {
  try {
    const v = localStorage.getItem(VIEW_KEY);
    if (v === "grouped" || v === "flat") return v;
  } catch {
    /* ignore (private mode etc.) */
  }
  return "grouped";
}

export default function Dashboard() {
  const { t } = useTranslation();
  const cameras = useQuery({ queryKey: ["cameras"], queryFn: () => api.get<Camera[]>("/api/cameras") });
  const groups = useQuery({ queryKey: ["groups"], queryFn: () => api.get<Group[]>("/api/groups").catch(() => []) });
  const { alertsByCam } = useDashboardEvents();

  const [storeFilter, setStoreFilter] = useState<string>("");
  const [stateFilter, setStateFilter] = useState<string>("");
  const [recentOnly, setRecentOnly] = useState(false);
  const [sort, setSort] = useState<"name" | "path" | "last_event" | "alerts">("name");
  const [view, setView] = useState<ViewMode>(readSavedView);

  useEffect(() => {
    try {
      localStorage.setItem(VIEW_KEY, view);
    } catch {
      /* ignore */
    }
  }, [view]);

  const groupPath = useMemo(() => buildGroupPaths(groups.data), [groups.data]);
  const stores = useMemo(() => (groups.data ?? []).filter((g) => g.level === 1), [groups.data]);

  const filtered = useMemo(() => {
    const list = (cameras.data ?? []).filter((c) => {
      if (storeFilter) {
        const path = c.group_id ? groupPath[c.group_id] ?? "" : "";
        if (!path.startsWith(storeFilter)) return false;
      }
      if (stateFilter && c.status !== stateFilter) return false;
      if (recentOnly && !alertsByCam[c.id]) return false;
      return true;
    });
    list.sort((a, b) => {
      switch (sort) {
        case "alerts":
          return (alertsByCam[b.id] ?? 0) - (alertsByCam[a.id] ?? 0);
        case "path":
          return (groupPath[a.group_id ?? 0] ?? "").localeCompare(groupPath[b.group_id ?? 0] ?? "");
        case "last_event":
          return (b.last_status_at ?? "").localeCompare(a.last_status_at ?? "");
        default:
          return a.name.localeCompare(b.name);
      }
    });
    return list;
  }, [cameras.data, groupPath, storeFilter, stateFilter, recentOnly, sort, alertsByCam]);

  // For grouped view: bucket cameras by their full group path. Unassigned in their own bucket.
  const sections = useMemo(() => {
    const buckets = new Map<string, { key: string; label: string; cameras: Camera[] }>();
    for (const c of filtered) {
      const key = c.group_id != null ? String(c.group_id) : "__unassigned__";
      const label =
        c.group_id != null ? groupPath[c.group_id] ?? `#${c.group_id}` : t("dashboard.unassigned");
      if (!buckets.has(key)) buckets.set(key, { key, label, cameras: [] });
      buckets.get(key)!.cameras.push(c);
    }
    const out = Array.from(buckets.values());
    out.sort((a, b) => {
      // Unassigned always last.
      if (a.key === "__unassigned__") return 1;
      if (b.key === "__unassigned__") return -1;
      return a.label.localeCompare(b.label);
    });
    return out;
  }, [filtered, groupPath, t]);

  if (cameras.isLoading) return <Typography>{t("common.loading")}</Typography>;
  if (!filtered.length)
    return <Typography color="text.secondary">{t("dashboard.no_cameras")}</Typography>;

  return (
    <Box>
      <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" sx={{ mb: 2 }}>
        <TextField
          select
          size="small"
          label={t("dashboard.filter_store")}
          value={storeFilter}
          onChange={(e) => setStoreFilter(e.target.value)}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">*</MenuItem>
          {stores.map((s) => (
            <MenuItem key={s.id} value={s.name}>
              {s.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          size="small"
          label={t("dashboard.filter_state")}
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">*</MenuItem>
          {(["live", "reconnecting", "error", "disabled"] as const).map((s) => (
            <MenuItem key={s} value={s}>
              {t(`dashboard.state.${s}`)}
            </MenuItem>
          ))}
        </TextField>
        <FormControlLabel
          control={<Checkbox checked={recentOnly} onChange={(e) => setRecentOnly(e.target.checked)} />}
          label={t("dashboard.filter_recent")}
        />
        <TextField
          select
          size="small"
          label={t("dashboard.sort_by")}
          value={sort}
          onChange={(e) => setSort(e.target.value as typeof sort)}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="name">{t("dashboard.sort_name")}</MenuItem>
          <MenuItem value="path">{t("dashboard.sort_path")}</MenuItem>
          <MenuItem value="last_event">{t("dashboard.sort_last_event")}</MenuItem>
          <MenuItem value="alerts">{t("dashboard.sort_alerts")}</MenuItem>
        </TextField>

        <Box sx={{ flex: 1 }} />

        <ToggleButtonGroup
          size="small"
          value={view}
          exclusive
          onChange={(_, v) => v && setView(v)}
          aria-label={t("dashboard.view") ?? "view"}
        >
          <ToggleButton value="grouped" aria-label="grouped">
            <AccountTreeIcon fontSize="small" sx={{ mr: 0.5 }} />
            {t("dashboard.view_grouped")}
          </ToggleButton>
          <ToggleButton value="flat" aria-label="flat">
            <ViewModuleIcon fontSize="small" sx={{ mr: 0.5 }} />
            {t("dashboard.view_flat")}
          </ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {view === "flat" ? (
        <Grid container spacing={2}>
          {filtered.map((c) => (
            <Grid key={c.id} size={{ xs: 12, sm: 6, md: 4, xl: 3 }}>
              <CameraCard
                cameraId={c.id}
                name={c.name}
                groupPath={c.group_id ? groupPath[c.group_id] : undefined}
                status={c.status}
                alert={!!alertsByCam[c.id]}
                displayEnabled={c.display_enabled}
              />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Stack spacing={3}>
          {sections.map((sec) => (
            <Box key={sec.key}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                <Typography variant="h3">{sec.label}</Typography>
                <Chip
                  size="small"
                  variant="outlined"
                  label={sec.cameras.length}
                  sx={{ height: 20, fontSize: 11 }}
                />
              </Stack>
              <Grid container spacing={2}>
                {sec.cameras.map((c) => (
                  <Grid key={c.id} size={{ xs: 12, sm: 6, md: 4, xl: 3 }}>
                    <CameraCard
                      cameraId={c.id}
                      name={c.name}
                      status={c.status}
                      alert={!!alertsByCam[c.id]}
                      displayEnabled={c.display_enabled}
                    />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ))}
        </Stack>
      )}
    </Box>
  );
}

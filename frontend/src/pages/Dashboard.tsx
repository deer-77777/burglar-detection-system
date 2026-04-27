import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Box,
  Checkbox,
  FormControlLabel,
  Grid2 as Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

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

export default function Dashboard() {
  const { t } = useTranslation();
  const cameras = useQuery({ queryKey: ["cameras"], queryFn: () => api.get<Camera[]>("/api/cameras") });
  const groups = useQuery({ queryKey: ["groups"], queryFn: () => api.get<Group[]>("/api/groups").catch(() => []) });
  const { alertsByCam } = useDashboardEvents();
  const [storeFilter, setStoreFilter] = useState<string>("");
  const [stateFilter, setStateFilter] = useState<string>("");
  const [recentOnly, setRecentOnly] = useState(false);
  const [sort, setSort] = useState<"name" | "path" | "last_event" | "alerts">("name");

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
      </Stack>

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
    </Box>
  );
}

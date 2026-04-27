import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import mpegts from "mpegts.js";
import { Box, Card, Chip, Stack, Typography } from "@mui/material";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";

export type CameraCardProps = {
  cameraId: number;
  name: string;
  groupPath?: string;
  status: "live" | "disabled" | "reconnecting" | "error" | "pending";
  alert?: boolean;
  displayEnabled: boolean;
};

const stateColor = {
  live: "success.main",
  error: "error.main",
  disabled: "grey.500",
  reconnecting: "warning.main",
  pending: "warning.main",
} as const;

export default function CameraCard({ cameraId, name, groupPath, status, alert, displayEnabled }: CameraCardProps) {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!displayEnabled || status !== "live" || !videoRef.current || !mpegts.getFeatureList().mseLivePlayback) {
      return;
    }
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const player = mpegts.createPlayer({
      type: "mse",
      isLive: true,
      url: `${proto}//${window.location.host}/ws/stream/${cameraId}`,
    });
    player.attachMediaElement(videoRef.current);
    player.load();
    Promise.resolve(player.play()).catch(() => {});
    return () => {
      player.unload();
      player.detachMediaElement();
      player.destroy();
    };
  }, [cameraId, status, displayEnabled]);

  return (
    <Card
      variant="outlined"
      sx={{
        overflow: "hidden",
        outline: alert ? "2px solid" : "none",
        outlineColor: "error.main",
      }}
    >
      <Box
        sx={{
          aspectRatio: "16 / 9",
          bgcolor: "common.black",
          color: "common.white",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {displayEnabled ? (
          <video ref={videoRef} style={{ width: "100%", height: "100%" }} muted playsInline />
        ) : (
          <Typography variant="body2">{t("dashboard.state.disabled")}</Typography>
        )}
      </Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ px: 1.5, py: 1 }}>
        <FiberManualRecordIcon sx={{ fontSize: 10, color: stateColor[status] }} />
        <Typography variant="body2" fontWeight={500}>
          {name}
        </Typography>
        {groupPath && (
          <Typography variant="caption" color="text.secondary">
            {groupPath}
          </Typography>
        )}
        <Box sx={{ flex: 1 }} />
        <Chip size="small" label={t(`dashboard.state.${status}`)} variant="outlined" />
      </Stack>
    </Card>
  );
}

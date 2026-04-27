import { useEffect, useRef } from "react";
import mpegts from "mpegts.js";
import { Box } from "@mui/material";

/**
 * Plays a History event's video clip. Workers write MPEG-TS (.ts) which most
 * browsers can't play natively in a <video> tag, so we route TS through
 * mpegts.js. .mp4 (legacy) plays via the <video> element directly.
 */
export default function ClipPlayer({ src }: { src: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const isTs = src.endsWith(".ts") || src.includes("/clip");

  useEffect(() => {
    if (!isTs || !videoRef.current || !mpegts.getFeatureList().mseLivePlayback) return;
    const player = mpegts.createPlayer({ type: "mse", isLive: false, url: src });
    player.attachMediaElement(videoRef.current);
    player.load();
    return () => {
      player.unload();
      player.detachMediaElement();
      player.destroy();
    };
  }, [src, isTs]);

  return (
    <Box
      component="video"
      ref={videoRef}
      controls
      src={isTs ? undefined : src}
      sx={{ width: "100%", maxWidth: 480, borderRadius: 1, border: 1, borderColor: "divider" }}
    />
  );
}

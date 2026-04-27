"""RTSP test-connection probe used by the Add-Camera dialog.

The probe attempts to open the stream with PyAV (FFmpeg) for a single frame
within a 5s budget. ONVIF resolution discovery is optional; failures there
do not mark the probe as failed.
"""
from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import av


@dataclass
class ProbeResult:
    success: bool
    error_code: str | None = None
    error_detail: str | None = None
    width: int | None = None
    height: int | None = None
    onvif_resolutions: list[tuple[int, int]] | None = None


_ERR_AUTH = "ERR_AUTH"
_ERR_HOST = "ERR_HOST_UNREACHABLE"
_ERR_TIMEOUT = "ERR_TIMEOUT"
_ERR_BAD_PATH = "ERR_BAD_PATH"
_ERR_CODEC = "ERR_CODEC_UNSUPPORTED"
_ERR_UNKNOWN = "ERR_UNKNOWN"


def _classify(exc: BaseException) -> tuple[str, str]:
    msg = str(exc).lower()
    if "401" in msg or "unauthorized" in msg or "auth" in msg:
        return _ERR_AUTH, str(exc)
    if "404" in msg or "not found" in msg:
        return _ERR_BAD_PATH, str(exc)
    if "timed out" in msg or "timeout" in msg:
        return _ERR_TIMEOUT, str(exc)
    if "refused" in msg or "unreachable" in msg or "no route" in msg or isinstance(exc, socket.gaierror):
        return _ERR_HOST, str(exc)
    if "codec" in msg or "decoder" in msg:
        return _ERR_CODEC, str(exc)
    return _ERR_UNKNOWN, str(exc)


def _probe_blocking(rtsp_url: str, timeout_sec: float = 5.0) -> ProbeResult:
    try:
        opts = {
            "rtsp_transport": "tcp",
            "stimeout": str(int(timeout_sec * 1_000_000)),  # microseconds
            "rw_timeout": str(int(timeout_sec * 1_000_000)),
        }
        with av.open(rtsp_url, options=opts, timeout=timeout_sec) as container:
            stream = next((s for s in container.streams if s.type == "video"), None)
            if stream is None:
                return ProbeResult(False, _ERR_CODEC, "No video stream in SDP")
            for packet in container.demux(stream):
                for frame in packet.decode():
                    return ProbeResult(
                        True,
                        width=frame.width,
                        height=frame.height,
                    )
            return ProbeResult(False, _ERR_CODEC, "No frames decoded")
    except av.AVError as exc:
        code, detail = _classify(exc)
        return ProbeResult(False, code, detail)
    except Exception as exc:  # pragma: no cover - safety net
        code, detail = _classify(exc)
        return ProbeResult(False, code, detail)


async def probe_rtsp(rtsp_url: str, timeout_sec: float = 5.0) -> ProbeResult:
    return await asyncio.to_thread(_probe_blocking, rtsp_url, timeout_sec)


async def onvif_discover(host: str, port: int, user: str, password: str) -> list[tuple[int, int]]:
    """Best-effort ONVIF resolution probe. Empty list on failure."""
    def _do() -> list[tuple[int, int]]:
        try:
            from onvif import ONVIFCamera  # type: ignore[import-not-found]

            cam = ONVIFCamera(host, port, user, password)
            media = cam.create_media_service()
            profiles = media.GetProfiles()
            seen: set[tuple[int, int]] = set()
            for p in profiles:
                vec = getattr(p.VideoEncoderConfiguration, "Resolution", None)
                if vec and vec.Width and vec.Height:
                    seen.add((int(vec.Width), int(vec.Height)))
            return sorted(seen)
        except Exception:
            return []

    return await asyncio.to_thread(_do)


def split_rtsp(url: str) -> tuple[str, int, str, str]:
    """Return (host, port, user, password) parsed from an RTSP URL."""
    p = urlparse(url)
    return p.hostname or "", p.port or 554, p.username or "", p.password or ""

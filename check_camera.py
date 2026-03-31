"""
Camera connectivity checker — fast failure with proper timeout.

Usage:
    python check_camera.py <rtsp_url> [timeout_seconds]

Examples:
    python check_camera.py rtsp://admin:mahindra%40123@10.5.12.161/streaming/channels/101
    python check_camera.py rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101/ 5
"""

import sys
import time
import socket
from urllib.parse import urlparse


def _masked(url: str) -> str:
    """Hide password in printed URL."""
    if "@" in url:
        scheme_user = url.split("@")[0]          # rtsp://user:pass
        rest = url.split("@")[1]                  # host/path
        user_part = scheme_user.split("//")[0] + "//" + scheme_user.split("//")[1].split(":")[0]
        return f"{user_part}:***@{rest}"
    return url


def check_tcp(host: str, port: int, timeout: int) -> bool:
    """Quick TCP handshake — confirms the host:port is reachable at all."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_camera(url: str, timeout_sec: int = 10) -> None:
    print(f"\n  Checking : {_masked(url)}")
    print(f"  Timeout  : {timeout_sec}s\n")

    # ── Step 1: parse the URL ──────────────────────────────────────────────
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 554          # RTSP default port is 554

    if not host:
        print("  [FAIL]  Could not parse host from URL.")
        sys.exit(1)

    print(f"  Host : {host}   Port : {port}")

    # ── Step 2: TCP reachability check (fast, no OpenCV needed) ───────────
    print(f"  Checking TCP connection to {host}:{port} ...")
    if not check_tcp(host, port, timeout=timeout_sec):
        print(f"\n  [FAIL]  Host {host}:{port} is NOT reachable.")
        print("  Possible reasons:")
        print("    - Camera is powered off or disconnected")
        print("    - Your machine is on a different network / VLAN")
        print("    - Firewall blocking port", port)
        print("    - Wrong IP address in the URL")
        sys.exit(1)

    print(f"  [OK]  TCP connection to {host}:{port} succeeded.\n")

    # ── Step 3: Open the RTSP stream via OpenCV ────────────────────────────
    # Use CAP_PROP_OPEN_TIMEOUT_MSEC — the correct way to set timeout in OpenCV
    import cv2

    cap = cv2.VideoCapture()
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_sec * 1000)   # works in OpenCV 4.x
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_sec * 1000)

    print("  Opening RTSP stream ...")
    opened = cap.open(url, cv2.CAP_FFMPEG)

    if not opened or not cap.isOpened():
        print("  [FAIL]  RTSP stream could not be opened.")
        print("  Possible reasons:")
        print("    - Wrong username or password in the URL")
        print("    - Wrong stream path  (try /streaming/channels/101  or  /live.sdp  or  /stream1)")
        print("    - Camera does not support RTSP or stream is disabled")
        cap.release()
        sys.exit(1)

    w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_prop = cap.get(cv2.CAP_PROP_FPS)
    print(f"  [OK]  Stream opened  —  {w}x{h}  @ {fps_prop:.0f} fps (reported)\n")

    # ── Step 4: Read actual frames ─────────────────────────────────────────
    frames_ok = 0
    start = time.time()

    for attempt in range(8):
        ret, frame = cap.read()
        if ret and frame is not None:
            frames_ok += 1
            fh, fw = frame.shape[:2]
            print(f"  [OK]  Frame {frames_ok} received  —  {fw}x{fh}")
            if frames_ok >= 3:
                break
        else:
            print(f"  [WARN] Attempt {attempt + 1}: no frame yet, retrying ...")
            time.sleep(0.4)

    elapsed = time.time() - start
    cap.release()

    print()
    if frames_ok > 0:
        print(f"  RESULT : Camera is ONLINE  ({frames_ok} frames in {elapsed:.1f}s)")
    else:
        print("  RESULT : Stream opened but NO frames received.")
        print("  Try a different stream path or check camera encoding settings.")
        sys.exit(1)


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    url = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) >= 3 else 10
    check_camera(url, timeout)

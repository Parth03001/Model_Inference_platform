"""
Camera connectivity checker.
Usage:
    python check_camera.py <rtsp_url>
    python check_camera.py rtsp://admin:password@192.168.1.100/streaming/channels/101
"""

import sys
import time
import cv2


def check_camera(url: str, timeout_sec: int = 10) -> None:
    print(f"\n  Checking camera...")
    print(f"  URL : {url.replace(url.split('@')[0].split('//')[1], '***') if '@' in url else url}")
    print(f"  Timeout : {timeout_sec}s\n")

    # OpenCV uses an environment variable for RTSP timeout (in microseconds)
    # Set before creating VideoCapture
    import os
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;tcp|timeout;{timeout_sec * 1_000_000}"

    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        print("  [FAIL]  Could not open stream — camera unreachable or wrong URL/credentials.")
        cap.release()
        sys.exit(1)

    print("  [OK]  Stream opened successfully.")

    # Try reading a few frames to confirm it is actually sending data
    frames_read = 0
    start = time.time()

    for attempt in range(5):
        ret, frame = cap.read()
        if ret and frame is not None:
            frames_read += 1
            h, w = frame.shape[:2]
            print(f"  [OK]  Frame {frames_read} received — resolution {w}x{h}")
            if frames_read >= 3:
                break
        else:
            print(f"  [WARN] Frame read attempt {attempt + 1} failed, retrying...")
            time.sleep(0.5)

    elapsed = time.time() - start
    cap.release()

    print()
    if frames_read > 0:
        print(f"  RESULT : Camera is ONLINE  ({frames_read} frames in {elapsed:.1f}s)")
    else:
        print("  RESULT : Camera opened but NO frames received — check stream path or encoding.")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_camera.py <rtsp_url>")
        print("Example:")
        print("  python check_camera.py rtsp://admin:password@10.5.12.161/streaming/channels/101")
        sys.exit(0)

    check_camera(sys.argv[1])

import cv2
import numpy as np

# Define RTSP Stream URL (Replace with your camera's RTSP URL)
rtsp_url = "2.jpg"

# Open the RTSP stream
cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
    print("Error: Unable to open RTSP stream.")
    exit()

# Retrieve original frame height
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

print(f"Original Frame Size: {frame_width}x{frame_height}")

# Store clicked points for ROI and threshold values
clicked_points = []

def get_pixel(event, x, y, flags, param):
    """Mouse callback function to capture pixel coordinates."""
    if event == cv2.EVENT_LBUTTONDOWN:
        clicked_points.append((x, y))
        print(f"Point Selected: {x}, {y}")

        # Draw the selected points
        frame_with_points = param.copy()
        for point in clicked_points:
            cv2.circle(frame_with_points, point, 5, (0, 0, 255), -1)

        cv2.imshow("Select Points (Press 'q' when done)", frame_with_points)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Unable to fetch frame from RTSP stream.")
        break

    # Resize for better visibility while maintaining aspect ratio
    target_height = 720  # Standard height for display
    aspect_ratio = frame_width / frame_height
    new_width = int(target_height * aspect_ratio)
    frame_resized = cv2.resize(frame, (new_width, target_height))

    # Show the video and set mouse callback for clicking points
    cv2.imshow("Select Points (Press 'q' when done)", frame_resized)
    cv2.setMouseCallback("Select Points (Press 'q' when done)", get_pixel, frame_resized)

    # Press 'q' to stop selecting points
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Output the selected points
print("\nFinal Selected Points:", clicked_points)

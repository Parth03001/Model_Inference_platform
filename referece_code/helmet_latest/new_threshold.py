import os
import time
import json
from datetime import datetime, timedelta
from collections import defaultdict
import cv2
import base64
import mysql.connector
from ultralytics import YOLO
import multiprocessing

# Set folder paths and database configurations
IMAGE_FOLDER = 'non_helmet_images'

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# Global variable to store recent detections
recent_detections = defaultdict(list)

# Global settings for alert flag
alert_flag = False

def connect_to_db():
    """Establish a MySQL database connection."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="helmet_detection"
    )


def compress_image_to_base64(image, quality=50):
    """
    Compresses an image and converts it to a base64 string.

    Args:
        image: The image to compress.
        quality: Compression quality for JPEG format (default is 50).

    Returns:
        Base64-encoded string of the compressed image.
    """
    _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buffer).decode('utf-8')


def insert_data_to_db(report_entry):
    """
    Inserts a detection report into the database.

    Args:
        report_entry: A dictionary containing report details.
    """
    connection = connect_to_db()
    try:
        cursor = connection.cursor()
        query = """
        INSERT INTO detection_reports (camera_name, timestamp, image_path, status)
        VALUES (%s, %s, %s, %s)
        """
        data = (
            report_entry['camera_name'],
            report_entry['timestamp'],
            report_entry['image_path'],
            report_entry['status']
        )
        cursor.execute(query, data)
        connection.commit()
        print(f"Report for {report_entry['camera_name']} inserted into the database.")
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
    finally:
        cursor.close()
        connection.close()


def save_image_and_generate_report(annotated_frame, camera, track_id):
    """
    Generates a report for a detection and saves it to the database.

    Args:
        annotated_frame: The frame containing the detection.
        camera: The name of the camera where detection occurred.
        track_id: The unique ID for the tracked object.
    """
    now = datetime.now()
    base64_image = compress_image_to_base64(annotated_frame)
    report_entry = {
        'camera_name': camera,
        'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
        'image_path': base64_image,
        'status': 'no helmet'  # Status can be dynamic if needed
    }
    insert_data_to_db(report_entry)

    # Set alert flag to true
    global alert_flag
    alert_flag = True


def yolo_detection(model_path, cam_name, cam_url):
    """
    Performs YOLO detection on a live camera feed and displays detection boxes.

    Args:
        model_path: Path to the YOLO model.
        cam_name: Name of the camera.
        cam_url: RTSP URL of the camera.
    """
    model = YOLO(model_path)
    cv2.namedWindow(cam_name, cv2.WINDOW_NORMAL)
    cap = cv2.VideoCapture(cam_url)

    if not cap.isOpened():
        print(f"Error: Unable to open RTSP stream for camera {cam_name}.")
        return

    person_last_report_time = {}
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Define thresholds
    low_threshold = int(0.80 * frame_height)  # Lower limit (20% of frame height)
    height_threshold = int(0.30 * frame_height)  # Upper limit (60% of frame height)

    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Error: Failed to read frame from camera {cam_name}. Retrying...")
            time.sleep(5)
            continue

        # Run YOLO detection
        results = model.track(frame, persist=True, conf=0.5, iou=0.5)
        if results[0].boxes.is_track:
            boxes = results[0].boxes.xyxy.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            cls_ids = results[0].boxes.cls.cpu()

            for box, track_id, cls_id in zip(boxes, track_ids, cls_ids):
                x, y, w, h = box
                if low_threshold > y > height_threshold:  # Ensure detection happens within thresholds

                    # Skip detection if detected recently in a nearby location
                    skip_detection = False
                    for past_x, past_y, past_time in recent_detections[cam_name]:
                        if abs(past_x - x) < 500 and abs(past_y - y) < 500 and datetime.now() - past_time < timedelta(seconds=300):
                            skip_detection = True
                            break
                    if skip_detection:
                        continue

                    if cls_id == 0:  # Helmet detected
                        cv2.rectangle(frame, (int(x), int(y)), (int(w), int(h)), (0, 255, 0), 2)
                        cv2.putText(frame, "Helmet", (int(x + 10), int(y - 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                        continue

                    # Non-helmet detection
                    cv2.rectangle(frame, (int(x), int(y)), (int(w), int(h)), (0, 0, 255), 2)
                    cv2.putText(frame, "Non-Helmet", (int(x + 10), int(y - 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

                    # Record detection time and coordinates
                    recent_detections[cam_name].append((x, y, datetime.now()))

                    # Check if enough time has passed for reporting
                    last_report_time = person_last_report_time.get(track_id, datetime.min)
                    if datetime.now() - last_report_time > timedelta(seconds=300):
                        save_image_and_generate_report(frame, cam_name, track_id)
                        person_last_report_time[track_id] = datetime.now()

        # Calculate FPS
        elapsed_time = time.time() - start_time
        fps = 1 / elapsed_time if elapsed_time > 0 else 0
        start_time = time.time()

        # Display FPS and detection region lines
        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.line(frame, (0, low_threshold), (frame.shape[1], low_threshold), (0, 255, 255), 2)  # Yellow Line (Low Threshold)
        cv2.line(frame, (0, height_threshold), (frame.shape[1], height_threshold), (255, 0, 0), 2)  # Blue Line (Upper Threshold)

        # Display the frame
        cv2.imshow(cam_name, cv2.resize(frame, (640, 480)))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyWindow(cam_name)

 
def start_detection():
    """
    Starts YOLO detection on multiple cameras.
    """
    # model_path = r'weights\\best_openvino_model'
    model_path = r'D:\\backend\\weights\\new_weights\\best.pt'
    cameras = [
        # {
        #     "camera": "CCTV NO. 118 MHAWK STORE 2",
        #     "cam_url": "rtsp://admin:mahindra%40123@10.5.12.161/streaming/channels/101"
        # },
        {
            "camera": "CCTV NO. 118 MHAWK STORE 2",
            "cam_url": "rtsp://admin:mahindra%40123@10.5.12.161/streaming/channels/101"
        },
        {
            "camera": "CCTV NO. 114 NEW STRONG ROOM 1",
            "cam_url":"rtsp://admin:12345@10.5.12.101/streaming/channels/101"
        },
        {
            "camera": "CCTV NO. 115 NEW STRONG ROOM 2",
            "cam_url":"rtsp://admin:12345@10.5.12.102/streaming/channels/101"
        },
        {
            "camera": "CCTV NO. 116 NEW STRONG ROOM 3 ",
            "cam_url": "rtsp://admin:12345@10.5.12.103/streaming/channels/101"
            
        },
        {
            "camera": "CCTV NO. 117 MHAWK STORE 3",
            "cam_url":"rtsp://admin:123456@10.5.12.162/streaming/channels/101"
        },
        {
            "camera": "CCTV NO. 21 MDI STORE 2",
            # "cam_url":"rtsp://root:admin123@10.5.12.164/streaming/channels/101"
            "cam_url":"rtsp://root:admin123@10.5.12.164/live.sdp"
        },
        {
            "camera": " CCTV NO. 22 MDI STORE 3 ",
            "cam_url":"rtsp://admin:123456@10.5.12.145/streaming/channels/101"
        },
        {
            "camera": "CCTV NO. 23 OLD STRONG ROOM ",
            # "cam_url":"rtsp://root:admin@10.5.28.64/streaming/channels/101"
            "cam_url":"rtsp://root:admin@10.5.28.64/live.sdp"
        },
         {
            "camera": "CCTV NO. 24 OLD STRONG ROOM TEM",
            "cam_url":"rtsp://admin:123456@10.5.28.63/streaming/channels/101"
        },
        {
            "camera": "NEW PLANT ",
            "cam_url":"rtsp://admin:mahindra%40123@10.5.28.145/streaming/channels/101"
        },
    ]
    processes = []
    for cam in cameras:
        process = multiprocessing.Process(
            target=yolo_detection, args=(model_path, cam['camera'], cam['cam_url']), daemon=True
        )
        processes.append(process)
        process.start()
 
    for process in processes:
        process.join()
 
 
if __name__ == "__main__":
    print("Starting YOLO detection...")
    start_detection()
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
from referece_code.camera import get_cameras  
from shapely.geometry import Polygon, Point
from referece_code.logger import logger

# Set folder paths and database configurations
IMAGE_FOLDER = 'non_helmet_images'

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# Global variable to store recent detections
recent_detections = defaultdict(list)

# Global settings for alert flag
alert_flag = False

# Dictionary to track detections for each person (track_id)
non_helmet_detections = defaultdict(lambda: defaultdict(int))

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

def is_inside_polygon(point, polygon):
    """
    Checks if a point (x, y) is inside the given polygon (ROI).
    
    Args:
        point: Tuple (x, y) representing the detection point.
        polygon: NumPy array of polygon vertices.
        
    Returns:
        Boolean indicating whether the point is inside the polygon.
    """
    poly = Polygon(polygon)
    return poly.contains(Point(point))

def yolo_detection(person_model_path, helmet_model_path, cam_name, cam_url, low_threshold_ratio, high_threshold_ratio, roi):
    """
    Performs two-stage detection:
    1. Person detection using COCO-pretrained model.
    2. Helmet detection on cropped person using custom-trained model.
    """
    person_model = YOLO(person_model_path)
    helmet_model = YOLO(helmet_model_path)

    cv2.namedWindow(cam_name, cv2.WINDOW_NORMAL)
    cap = cv2.VideoCapture(cam_url)

    if not cap.isOpened():
        print(f"Error: Unable to open RTSP stream for camera {cam_name}.")
        return

    person_last_report_time = {}
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    high_threshold = int(high_threshold_ratio * frame_height)
    low_threshold = int(low_threshold_ratio * frame_height)
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Error: Failed to read frame from camera {cam_name}. Retrying...")
            time.sleep(5)
            continue

        results = person_model(frame)
        boxes = results[0].boxes.xyxy.cpu()
        cls_ids = results[0].boxes.cls.cpu().tolist()

        for box, cls_id in zip(boxes, cls_ids):
            if int(cls_id) != 0:  # Only proceed if it's a 'person' class
                continue

            x1, y1, x2, y2 = map(int, box)
            detection_center_y = int((y1 + y2) / 2)

            if not (high_threshold < detection_center_y < low_threshold):
                continue

            center_point = (int((x1 + x2) / 2), detection_center_y)
            if not is_inside_polygon(center_point, roi):
                continue

            # Crop the person region
            person_crop = frame[y1:y2, x1:x2].copy()
            helmet_result = helmet_model.predict(person_crop, conf=0.4, iou=0.5)

            if helmet_result and helmet_result[0].boxes is not None:
                for hbox, hcls_id in zip(helmet_result[0].boxes.xyxy.cpu(), helmet_result[0].boxes.cls.cpu().tolist()):
                    hx1, hy1, hx2, hy2 = map(int, hbox)
                    helmet_label = "Helmet" if int(hcls_id) == 0 else "Non-Helmet"
                    color = (0, 255, 0) if int(hcls_id) == 0 else (0, 0, 255)

                    # You can add skip detection + DB logic here for Non-Helmet
                    if int(hcls_id) == 1:  # Non-helmet (head)
                        # Check skip logic
                        skip_detection = False
                        for past_x, past_y, past_time in recent_detections[cam_name]:
                            if abs(past_x - x1) < 500 and abs(past_y - y1) < 500 and datetime.now() - past_time < timedelta(seconds=300):
                                skip_detection = True
                                break
                        if skip_detection:
                            continue

                        track_key = f"{x1}_{y1}_{x2}_{y2}"  # use bounding box as pseudo track id
                        non_helmet_detections[cam_name][track_key] += 1
                        print(f"Camera {cam_name} - Track {track_key} detected {non_helmet_detections[cam_name][track_key]} times.")

                        if non_helmet_detections[cam_name][track_key] >= 4:
                            last_report_time = person_last_report_time.get(track_key, datetime.min)
                            if datetime.now() - last_report_time > timedelta(seconds=300):
                                save_image_and_generate_report(frame, cam_name, track_key)
                                person_last_report_time[track_key] = datetime.now()
                                recent_detections[cam_name].append((x1, y1, datetime.now()))
                                del non_helmet_detections[cam_name][track_key]

                    # Draw detection
                    cv2.rectangle(person_crop, (hx1, hy1), (hx2, hy2), color, 2)
                    cv2.putText(person_crop, helmet_label, (hx1, hy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Draw person bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(frame, "Person", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # FPS display
        elapsed_time = time.time() - start_time
        fps = 1 / elapsed_time if elapsed_time > 0 else 0
        start_time = time.time()

        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.line(frame, (0, high_threshold), (frame.shape[1], high_threshold), (0, 255, 255), 2)
        cv2.line(frame, (0, low_threshold), (frame.shape[1], low_threshold), (255, 0, 0), 2)
        cv2.polylines(frame, [roi], isClosed=True, color=(255, 255, 0), thickness=2)
        cv2.imshow(cam_name, cv2.resize(frame, (640, 480)))

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyWindow(cam_name)


def start_detection():
    person_model_path = "weights\\yolo11n.pt"
    helmet_model_path = "weights\\best.pt"
    cameras = get_cameras()

    processes = []
    for cam in cameras:
        process = multiprocessing.Process(
            target=yolo_detection,
            args=(person_model_path, helmet_model_path, cam['camera'], cam['cam_url'], cam['low_threshold'], cam['high_threshold'], cam['roi']),
            daemon=True
        )
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

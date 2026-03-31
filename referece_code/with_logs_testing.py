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
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="helmet_detection"
        )
        logger.info("Connected to MySQL database successfully.")
        return connection
    except mysql.connector.Error as err:
        logger.error(f"MySQL Connection Error: {err}")
        return None



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
    Inserts a detection report into the database and logs the operation, excluding the Base64 image.
    """
    connection = connect_to_db()
    if not connection:
        logger.error("Failed to connect to database. Skipping database insert.")
        return

    try:
        cursor = connection.cursor()
        query = """
        INSERT INTO detection_reports (camera_name, timestamp, image_path, status)
        VALUES (%s, %s, %s, %s)
        """
        data = (
            report_entry['camera_name'],
            report_entry['timestamp'],
            report_entry['image_path'],  # Still stored in DB, but NOT logged
            report_entry['status']
        )
        cursor.execute(query, data)
        connection.commit()
        
        # Log only relevant information (excluding Base64 image)
        log_entry = {
            'camera_name': report_entry['camera_name'],
            'timestamp': report_entry['timestamp'],
            'status': report_entry['status']
        }
        logger.info(f"Detection report inserted into database: {log_entry}")

    except mysql.connector.Error as err:
        logger.error(f"MySQL Error during insert: {err}")
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
    logger.info(f"Skip detection logic activated for Track ID {track_id} on camera {camera}. No duplicate detections for 5 minutes.")


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

def yolo_detection(model_path, cam_name, cam_url, low_threshold_ratio, high_threshold_ratio, roi):
    """
    Performs YOLO detection on a live camera feed and applies multi-stage verification
    before logging non-helmet detections to the database.

    Args:
        model_path: Path to the YOLO model.
        cam_name: Name of the camera.
        cam_url: RTSP URL of the camera.
        low_threshold_ratio: Percentage of frame height for lower detection limit.
        high_threshold_ratio: Percentage of frame height for upper detection limit.
        roi: NumPy array defining the trapezoidal ROI.
    """

    logger.info(f"Starting YOLO detection on camera: {cam_name} with RTSP URL: {cam_url}")
    model = YOLO(model_path)
    cv2.namedWindow(cam_name, cv2.WINDOW_NORMAL)
    cap = cv2.VideoCapture(cam_url)

    if not cap.isOpened():
        print(f"Error: Unable to open RTSP stream for camera {cam_name}.")
        logger.error(f"Error: Unable to open RTSP stream for camera {cam_name}.")
        return

    logger.info(f"Camera {cam_name} stream opened successfully.")
        

    person_last_report_time = {}  # Stores last report time per track ID
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Convert threshold ratios to pixel values
    high_threshold = int(high_threshold_ratio * frame_height)
    low_threshold = int(low_threshold_ratio * frame_height)

    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Error: Failed to read frame from camera {cam_name}. Retrying...")
            logger.warning(f"Failed to read frame from camera {cam_name}. Retrying in 5 seconds...")
            time.sleep(5)
            continue

        # Run YOLO detection

        logger.debug(f"Processing frame for camera {cam_name}.")
        results = model.track(frame, persist=True, conf=0.5, iou=0.5)
        if results[0].boxes.is_track:
            boxes = results[0].boxes.xyxy.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            cls_ids = results[0].boxes.cls.cpu()

            for box, track_id, cls_id in zip(boxes, track_ids, cls_ids):
                x, y, w, h = box

                # Ensure detection is within threshold limits
                if not (high_threshold < y < low_threshold):
                    continue

                # Check if detection is inside ROI
                detection_center = (int((x + w) / 2), int((y + h) / 2))
                if not is_inside_polygon(detection_center, roi):
                    continue

                # SKIP DETECTION LOGIC (Only after pushing to DB)
                skip_detection = False
                for past_x, past_y, past_time in recent_detections[cam_name]:
                    if abs(past_x - x) < 500 and abs(past_y - y) < 500 and datetime.now() - past_time < timedelta(seconds=300):
                        skip_detection = True
                        break
                
                if skip_detection:
                    print(f"Skipping detection for {cam_name} at ({x}, {y}) - Recently detected.")
                    continue

                # TRACK 4 DETECTIONS BEFORE PUSHING TO DB
                if cls_id != 0:  # If not helmet
                    non_helmet_detections[cam_name][track_id] += 1
                    logger.info(f"Camera {cam_name}: Track ID {track_id} detected {non_helmet_detections[cam_name][track_id]} times without helmet.")
                    print(f"Camera {cam_name} - Track ID {track_id} detected {non_helmet_detections[cam_name][track_id]} times.")

                    # Wait for 4 detections before sending to DB
                    if non_helmet_detections[cam_name][track_id] < 4:
                        logger.info(f"ALERT: Camera {cam_name} detected a person (Track ID {track_id}) without a helmet.")

                        continue

                    # ON 4TH DETECTION → PUSH TO DATABASE
                    last_report_time = person_last_report_time.get(track_id, datetime.min)
                    if datetime.now() - last_report_time > timedelta(seconds=300):
                        save_image_and_generate_report(frame, cam_name, track_id)
                        logger.info(f"ALERT: Camera {cam_name} detected a person (Track ID {track_id}) without a helmet.")

                        logger.info(f"Starting skip detection logic for camera {cam_name}, Track ID {track_id}. No duplicate reports for 5 minutes.")
                        person_last_report_time[track_id] = datetime.now()

                        # Activate skip detection logic after sending to DB
                        recent_detections[cam_name].append((x, y, datetime.now()))

                        # Reset detection counter for this track_id after it is stored
                        del non_helmet_detections[cam_name][track_id]

                else:
                    # Reset detection count for helmets
                    if track_id in non_helmet_detections[cam_name]:
                        del non_helmet_detections[cam_name][track_id]
                        logger.info(f"Helmet detected again for Track ID {track_id} on camera {cam_name}. Skip detection logic ended.")

                # Draw detection bounding boxes
                color = (0, 255, 0) if cls_id == 0 else (0, 0, 255)
                label = "Helmet" if cls_id == 0 else "Non-Helmet"
                cv2.rectangle(frame, (int(x), int(y)), (int(w), int(h)), color, 2)
                cv2.putText(frame, label, (int(x + 10), int(y - 20)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Calculate FPS
        elapsed_time = time.time() - start_time
        fps = 1 / elapsed_time if elapsed_time > 0 else 0
        start_time = time.time()

        # Display FPS and detection threshold lines
        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.line(frame, (0, high_threshold), (frame.shape[1], high_threshold), (0, 255, 255), 2)  # Yellow Line 
        cv2.line(frame, (0, low_threshold), (frame.shape[1], low_threshold), (255, 0, 0), 2)  # Blue Line 

        # Draw ROI
        cv2.polylines(frame, [roi], isClosed=True, color=(255, 255, 0), thickness=2)

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
    logger.info("Starting multi-camera detection process...")
    model_path = r'weights\\best.pt'
    cameras = get_cameras()  # Fetch camera configurations

    processes = []
    for cam in cameras:
        logger.info(f"Initializing camera: {cam['camera']} at {cam['cam_url']}")
        process = multiprocessing.Process(
            target=yolo_detection, 
            args=(model_path, cam['camera'], cam['cam_url'], cam['low_threshold'], cam['high_threshold'], cam['roi']),
            daemon=True
        )
        processes.append(process)
        process.start()
        logger.info(f"Process started for camera: {cam['camera']}.")
    
    for process in processes:
        process.join()

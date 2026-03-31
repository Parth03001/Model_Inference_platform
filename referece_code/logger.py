import logging
import os
from logging.handlers import RotatingFileHandler

# Define log folder and file
LOG_FOLDER = "backend_logs"
LOG_FILE = os.path.join(LOG_FOLDER, "helmet_detection.log")

# Ensure the log directory exists
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3),  # Max 5MB per file, keep last 3 backups
        logging.StreamHandler()  # Also output logs to console
    ]
)

# Get the logger instance
logger = logging.getLogger("helmet_detection_logger")

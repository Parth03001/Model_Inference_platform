import os

import time

import json

from flask import Flask, Response, stream_with_context, request, jsonify

import threading

from flask_cors import CORS

# from apoorva import start_detection  # Import the backend detection function
from referece_code.backend_with_roi import start_detection 
# from backend_with_roi import * # Import the backend detection function

import mysql.connector

from datetime import datetime

import requests

 
app = Flask(__name__)

CORS(app)
 
# MySQL Database Configuration

db_config = {

    'user': 'root',

    'password': 'root',

    'host': 'localhost',

    'database': 'helmet_detection',

}
 
# Global variables to manage backend status

backend_running = False

backend_lock = threading.Lock()

 
 
@app.route('/')

def home():

    """Home route to check if Flask app is running."""

    return "Flask app is running."
 
 
@app.route('/start_backend', methods=['GET'])

def start_backend():

    """

    Start the backend detection process.

    Ensures the backend is started only once using a global lock.

    """

    global backend_running

    with backend_lock:

        if backend_running:

            return "Backend detection is already running.", 200
 
        # Start the backend in a separate thread

        backend_thread = threading.Thread(target=start_detection, daemon=True)

        backend_thread.start()

        backend_running = True

        print("Backend detection started.")

        return "Backend detection started successfully!", 200
 
 
def get_db_connection():

    """Establish and return a MySQL database connection."""

    return mysql.connector.connect(**db_config)
 
 
def convert_datetime_to_string(data):

    """

    Convert datetime fields in the database results to strings.
 
    Args:

        data: List of dictionaries with potential datetime fields.
 
    Returns:

        List of dictionaries with datetime fields converted to strings.

    """

    for item in data:

        if isinstance(item.get('timestamp'), datetime):

            item['timestamp'] = item['timestamp'].isoformat()

    return data
 
 
@app.route('/stream_reports', methods=['GET'])
def stream_reports():
    def report_streamer():
        last_seen_id = 0  # Tracks the last seen report ID

        while True:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)

                today = datetime.now().date()
                print(f"[DEBUG] Fetching reports for today: {today} (last seen ID: {last_seen_id})")

                query = """
                    SELECT * FROM detection_reports 
                    WHERE id > %s AND DATE(timestamp) = %s 
                    ORDER BY id ASC
                """
                cursor.execute(query, (last_seen_id, today))
                new_reports = cursor.fetchall()

                print(f"[DEBUG] Found {len(new_reports)} new reports")

                if new_reports:
                    new_reports = convert_datetime_to_string(new_reports)

                    for report in new_reports:
                        yield f"data: {json.dumps(report)}\n\n"

                    last_seen_id = new_reports[-1]['id']  # Update last seen ID

                cursor.close()
                conn.close()

            except Exception as e:
                print(f"❌ Error streaming reports: {e}")

            time.sleep(1)

    return Response(stream_with_context(report_streamer()), headers={
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
    })

    return Response(stream_with_context(report_streamer()), headers=headers)

# API to fetch detection counts per camera within a date range
@app.route('/get_detection_counts', methods=['GET'])
def get_detection_counts():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    connection = connect_to_db()
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT camera_name, COUNT(*) as non_helmet_count
        FROM detection_reports
        WHERE status = 'no helmet'
        AND timestamp BETWEEN %s AND %s
        GROUP BY camera_name
        """
        cursor.execute(query, (start_date, end_date))
        results = cursor.fetchall()
        return jsonify(results)
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})
    finally:
        cursor.close()
        connection.close()

@app.route('/get_detection_counters', methods=['GET'])
def get_detection_counters():
    """
    Fetch the detection counters per camera from the detection_reports table 
    based on the provided start_date and end_date.
    """
    try:
        # Extract and parse the start_date and end_date from request parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start_date and end_date are required parameters'}), 400

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query to count non-helmet detections per camera within the given date range
        query = """
            SELECT camera_name, COUNT(*) AS non_helmet_count, MAX(timestamp) AS last_updated
            FROM detection_reports
            WHERE status = 'no helmet' AND timestamp BETWEEN %s AND %s
            GROUP BY camera_name
            ORDER BY last_updated DESC
        """
        cursor.execute(query, (start_date, end_date))
        result = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({'detection_counters': result}), 200

    except Exception as e:
        print(f"Error fetching detection counters: {e}")
        return jsonify({'error': 'An unexpected error occurred while fetching detection counters'}), 500

  
@app.route('/get_combined_report', methods=['GET'])
def get_combined_report():
    """
    Fetch paginated combined reports from the database with optional filters:
      - camera_name (default: "all")
      - start_date (either "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS.sssZ")
      - end_date (either "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS.sssZ")
      - page (default: 1)
      - limit (default: 10)
    """
    try:
        # -- Step 1: Retrieve Query Parameters --
        page_str = request.args.get('page', '1')
        limit_str = request.args.get('limit', '10')
        camera_name = request.args.get('camera_name', 'all')
        start_date_str = request.args.get('start_date')  # Could be "2023-01-01" or "2025-01-23T18:30:00.000Z"
        end_date_str = request.args.get('end_date')      # Could be "2023-01-31" or "2025-01-24T18:30:00.000Z"
 
        # Debug prints
        print(f"[DEBUG] page_str: {page_str}, limit_str: {limit_str}")
        print(f"[DEBUG] camera_name: {camera_name}")
        print(f"[DEBUG] start_date_str: {start_date_str}, end_date_str: {end_date_str}")
 
        # Convert page and limit to integers and validate
        try:
            page = int(page_str)
            limit = int(limit_str)
            if page < 1 or limit < 1:
                raise ValueError("Page and limit must be positive integers.")
        except ValueError as ve:
            return Response(
                json.dumps({'error': f'Invalid pagination parameters: {ve}'}),
                mimetype='application/json',
                status=400
            )
 
        print(f"[DEBUG] Parsed page: {page}, Parsed limit: {limit}")
 
        # -- Step 2: Helper to parse date or datetime --
        def parse_date_or_datetime(dt_str, is_start=True):
            """
            If 'T' is present, assume ISO 8601 datetime,
            else assume 'YYYY-MM-DD'.
            `is_start=True` means it sets time to '00:00:00' if no time is provided;
            `is_start=False` means it sets time to '23:59:59' if no time is provided.
            """
            if "T" in dt_str:
                # We have a datetime string in ISO8601 format, e.g. "2025-01-23T18:30:00.000Z"
                # Adjust to your exact format or use a second fallback parse if you want to be very flexible.
                # Example for microseconds: "%Y-%m-%dT%H:%M:%S.%fZ"
                fmt_variants = [
                    "%Y-%m-%dT%H:%M:%S.%fZ",  # with fractional seconds
                    "%Y-%m-%dT%H:%M:%SZ"     # without fractional seconds
                ]
                last_exception = None
                for f in fmt_variants:
                    try:
                        return datetime.strptime(dt_str, f)
                    except ValueError as ex:
                        last_exception = ex
                # If we fail both formats, raise
                raise ValueError(f"Invalid datetime format: {dt_str} ({last_exception})")
            else:
                # We have a simple date, e.g. "2023-01-01"
                d = datetime.strptime(dt_str, "%Y-%m-%d")
                if is_start:
                    # Start of day
                    return d
                else:
                    # End of day => 23:59:59
                    return d.replace(hour=23, minute=59, second=59)
 
        # -- Step 3: Parse optional date/time strings --
        start_dt = None
        end_dt = None
 
        if start_date_str:
            try:
                # If user gave a simple date, parse to 00:00:00, else parse exact datetime
                start_dt = parse_date_or_datetime(start_date_str, is_start=True)
                print(f"[DEBUG] Parsed start_dt: {start_dt}")
            except ValueError:
                return Response(
                    json.dumps({'error': f'Invalid start_date format. Expected YYYY-MM-DD or ISO8601 datetime.'}),
                    mimetype='application/json',
                    status=400
                )
 
        if end_date_str:
            try:
                # If user gave a simple date, parse to 23:59:59, else parse exact datetime
                end_dt = parse_date_or_datetime(end_date_str, is_start=False)
                print(f"[DEBUG] Parsed end_dt: {end_dt}")
            except ValueError:
                return Response(
                    json.dumps({'error': f'Invalid end_date format. Expected YYYY-MM-DD or ISO8601 datetime.'}),
                    mimetype='application/json',
                    status=400
                )
 
        # -- Step 4: Prepare Pagination --
        offset = (page - 1) * limit
        print(f"[DEBUG] Calculated offset: {offset}")
 
        base_query = """
            SELECT *
            FROM detection_reports
        """
        base_count_query = """
            SELECT COUNT(*) AS total
            FROM detection_reports
        """
 
        conditions = []
        params = []
 
        # Camera filter
        if camera_name.lower() != 'all':
            conditions.append("camera_name = %s")
            params.append(camera_name)
 
        # Date/time range filter
        if start_dt:
            conditions.append("timestamp >= %s")
            params.append(start_dt)
        if end_dt:
            conditions.append("timestamp <= %s")
            params.append(end_dt)
 
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
        else:
            where_clause = ""
 
        main_query = (
            base_query
            + where_clause
            + " ORDER BY timestamp ASC LIMIT %s OFFSET %s"
        )
        main_query_params = params + [limit, offset]
 
        # Debug: final queries
        print(f"[DEBUG] Main Query: {main_query}")
        print(f"[DEBUG] Main Query Params: {main_query_params}")
 
        count_query = base_count_query + where_clause
        count_query_params = params
 
        print(f"[DEBUG] Count Query: {count_query}")
        print(f"[DEBUG] Count Query Params: {count_query_params}")
 
        # -- Step 5: Execute Queries --
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
 
        cursor.execute(main_query, main_query_params)
        combined_reports = cursor.fetchall()
        combined_reports = convert_datetime_to_string(combined_reports)  # your helper function
 
        cursor.execute(count_query, count_query_params)
        total_records = cursor.fetchone()['total']
 
        cursor.close()
        conn.close()
 
        # -- Step 6: Calculate Pagination Metadata --
        total_pages = (total_records + limit - 1) // limit
        response_payload = {
            'data': combined_reports,
            'pagination': {
                'current_page': page,
                'per_page': limit,
                'total_records': total_records,
                'total_pages': total_pages
            }
        }
 
        return Response(json.dumps(response_payload), mimetype='application/json', status=200)
 
    except Exception as e:
        print(f"Error fetching combined report: {e}")
        return Response(
            json.dumps({'error': 'An unexpected error occurred while fetching data.'}),
            mimetype='application/json',
            status=500
        )
        
if __name__ == '__main__':

    """

    Run the Flask application.

    Optionally starts the backend detection automatically.

    """

    try:

        print("Starting the Flask application...")
 
        # Optionally start the backend automatically

        with backend_lock:

            if not backend_running:

                backend_thread = threading.Thread(target=start_detection, daemon=True)

                backend_thread.start()

                backend_running = True

                print("Backend detection started automatically!")
 
        app.run(host="0.0.0.0", port=5000, debug=True, threaded=True, use_reloader=False)

    except Exception as e:

        print(f"Error starting Flask application: {e}")

 
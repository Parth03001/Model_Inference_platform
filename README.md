# Model Inference Platform

A full-stack real-time AI inference platform built with **FastAPI**, **React**, and **PostgreSQL**.  
Upload any YOLO model weights, connect RTSP camera streams, run live inference, and store every detection automatically.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
  - [Prerequisites](#prerequisites)
  - [1. Database](#1-database)
  - [2. Backend](#2-backend)
  - [3. Frontend](#3-frontend)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Deployment](#deployment)
  - [Docker Compose (Recommended)](#docker-compose-recommended)
  - [Manual Deployment](#manual-deployment)
- [How It Works](#how-it-works)

---

## Features

- **Model Upload** — Upload `.pt`, `.engine`, or `.onnx` YOLO weight files via drag-and-drop
- **Multi-Camera Support** — Add unlimited RTSP cameras, each runs in its own inference worker thread
- **Real-Time Inference** — Annotated frames pushed to the browser over WebSocket
- **Auto DB Creation** — PostgreSQL database is created automatically on first startup if it does not exist
- **Detection Storage** — Every detection saved with label, confidence, bounding box, and base64 snapshot
- **History & Filtering** — Paginated detection history filterable by camera and label
- **Beautiful UI** — Dark-themed React frontend with Framer Motion animations

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 (create-react-app), Framer Motion, React Router v6 |
| Backend | FastAPI, Uvicorn, Python 3.11 |
| Inference | Ultralytics YOLO, OpenCV |
| Database | PostgreSQL 15, SQLAlchemy 2, psycopg2 |
| Realtime | WebSocket (FastAPI native) |
| Deployment | Docker, Docker Compose, Nginx |

---

## Project Structure

```
Model_Inference_platform/
│
├── docker-compose.yml          # Orchestrates postgres + backend + frontend
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example            # Copy to .env and fill in values
│   │
│   ├── main.py                 # FastAPI app entry point, CORS, startup hook
│   ├── database.py             # SQLAlchemy engine, auto DB creation, session factory
│   ├── models.py               # ORM models: ModelWeight, Camera, Detection
│   ├── schemas.py              # Pydantic request/response schemas
│   │
│   ├── routers/
│   │   ├── model_upload.py     # POST /models/upload, GET /models/, DELETE /models/{id}
│   │   ├── cameras.py          # CRUD for cameras
│   │   ├── stream.py           # POST /stream/start|stop, WebSocket /stream/ws/{camera_id}
│   │   └── detections.py       # GET /detections/, GET /detections/stats
│   │
│   ├── services/
│   │   └── inference_service.py  # Background inference workers, WS frame broadcast
│   │
│   └── uploads/                # Uploaded model weight files stored here (git-ignored)
│
└── frontend/
    ├── Dockerfile
    ├── nginx.conf              # Nginx config for production container
    ├── package.json
    │
    └── src/
        ├── index.js            # React entry point
        ├── index.css           # Global CSS variables and resets
        ├── App.js              # Router setup, layout wrapper
        ├── App.css
        │
        ├── services/
        │   └── api.js          # Axios instance + all API call functions
        │
        └── components/
            ├── Navbar/
            │   ├── Navbar.js
            │   └── Navbar.css
            │
            ├── LandingPage/
            │   ├── LandingPage.js
            │   └── LandingPage.css
            │
            ├── Dashboard/
            │   ├── Dashboard.js    # Stats grid, cameras/models overview, label distribution
            │   └── Dashboard.css
            │
            ├── ModelUpload/
            │   ├── ModelUpload.js  # Drag-and-drop upload, list, activate, delete
            │   └── ModelUpload.css
            │
            ├── CameraManager/
            │   ├── CameraManager.js  # Add/edit/delete cameras
            │   └── CameraManager.css
            │
            ├── VideoStream/
            │   ├── VideoStream.js    # Start inference, live WebSocket stream panels
            │   └── VideoStream.css
            │
            ├── DetectionHistory/
            │   ├── DetectionHistory.js  # Paginated table, filters, snapshot modal
            │   └── DetectionHistory.css
            │
            └── StatsCard/
                ├── StatsCard.js    # Reusable animated stat card
                └── StatsCard.css
```

---

## Development Setup

### Prerequisites

Make sure you have the following installed on your machine:

| Tool | Version | Install |
|---|---|---|
| Python | 3.10+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| PostgreSQL | 14+ | https://postgresql.org |
| Git | any | https://git-scm.com |

> PostgreSQL must be running locally with user `postgres` and password `password`.  
> The app will **auto-create** the database `model_inference_db` on first run — you do not need to create it manually.

---

### 1. Database

No manual setup required. Just make sure PostgreSQL is running:

```bash
# Linux / macOS (systemd)
sudo systemctl start postgresql

# macOS (Homebrew)
brew services start postgresql@15

# Windows
# Start via pgAdmin or Services panel
```

The backend will connect to `postgres` (the default maintenance db) on startup,  
check if `model_inference_db` exists, and create it if not.

---

### 2. Backend

```bash
cd backend
```

**Create and activate a virtual environment:**

```bash
# macOS / Linux
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Set up environment variables:**

```bash
cp .env.example .env
```

Edit `.env` if your database credentials differ:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/model_inference_db
UPLOAD_DIR=uploads
HOST=0.0.0.0
PORT=8000
```

**Run the development server:**

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at:
- **API base:** `http://localhost:8000`
- **Swagger docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

On first run you will see logs like:

```
INFO  Database 'model_inference_db' created.
INFO  Creating database tables...
INFO  Startup complete.
```

---

### 3. Frontend

```bash
cd frontend
```

**Install dependencies:**

```bash
npm install
```

**Start the development server:**

```bash
npm start
```

The app opens at `http://localhost:3000`.

The `proxy` field in `package.json` is set to `http://localhost:8000` so all  
`/models`, `/cameras`, `/stream`, `/detections` API calls automatically forward to the backend — no CORS issues during development.

---

### Development Workflow

```
┌──────────────┐        HTTP / WS        ┌──────────────────┐
│   Browser    │  ──────────────────────▶ │  FastAPI :8000   │
│  React :3000 │                          │                  │
└──────────────┘                          │  Inference       │
                                          │  Workers         │
                                          │  (per camera)    │
                                          └────────┬─────────┘
                                                   │ SQLAlchemy
                                                   ▼
                                          ┌──────────────────┐
                                          │  PostgreSQL      │
                                          │  :5432           │
                                          └──────────────────┘
```

**Typical development cycle:**

1. Make a backend change → Uvicorn hot-reloads automatically (`--reload` flag)
2. Make a frontend change → React hot-reloads automatically (CRA default)
3. Database schema change → Update `models.py`, then restart the backend — `create_all()` applies new tables automatically

---

## Environment Variables

### Backend `.env`

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:password@localhost:5432/model_inference_db` | Full PostgreSQL connection string |
| `UPLOAD_DIR` | `uploads` | Folder where uploaded weight files are stored |
| `HOST` | `0.0.0.0` | Uvicorn bind host |
| `PORT` | `8000` | Uvicorn bind port |

### Frontend

| Variable | Default | Description |
|---|---|---|
| `REACT_APP_API_URL` | `http://localhost:8000` | Backend base URL (used in production build) |

Set in `frontend/.env.local` for local overrides (git-ignored).

---

## API Reference

### Models

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/models/upload` | Upload a weight file (`multipart/form-data`) |
| `GET` | `/models/` | List all uploaded models |
| `PATCH` | `/models/{id}/activate` | Set model as active |
| `DELETE` | `/models/{id}` | Delete model and file |

### Cameras

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/cameras/` | Add a camera `{ name, rtsp_url }` |
| `GET` | `/cameras/` | List all cameras |
| `PATCH` | `/cameras/{id}` | Update camera name or URL |
| `DELETE` | `/cameras/{id}` | Delete a camera |

### Stream

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/stream/start` | Start inference `{ camera_id, model_id }` |
| `POST` | `/stream/stop` | Stop inference `{ camera_id }` |
| `GET` | `/stream/status/{camera_id}` | Check if inference is running |
| `WS` | `/stream/ws/{camera_id}` | WebSocket — receives `{ type: "frame", data: "<base64>" }` |

### Detections

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/detections/` | Paginated list. Query params: `camera_id`, `label`, `page`, `per_page` |
| `GET` | `/detections/stats` | Total counts and label distribution |

---

## Deployment

### Docker Compose (Recommended)

This is the easiest way to run the full stack in production.

**Prerequisites:** Docker Engine + Docker Compose installed.

```bash
# Clone the repo
git clone <repo-url>
cd Model_Inference_platform

# Build and start all services
docker-compose up --build -d
```

Services started:

| Service | Container | Port |
|---|---|---|
| PostgreSQL 15 | `inference_postgres` | `5432` |
| FastAPI backend | `inference_backend` | `8000` |
| React (Nginx) | `inference_frontend` | `3000` |

**Check logs:**

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

**Stop everything:**

```bash
docker-compose down
```

**Stop and delete the database volume (full reset):**

```bash
docker-compose down -v
```

---

### Manual Deployment

If you prefer to deploy without Docker:

#### Backend (Production)

```bash
cd backend
pip install -r requirements.txt

# Use gunicorn with uvicorn workers for production
pip install gunicorn

gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 2 \
  --bind 0.0.0.0:8000
```

> Use a process manager like **systemd** or **supervisor** to keep it running.

#### Frontend (Production Build)

```bash
cd frontend

# Set the backend URL for production
echo "REACT_APP_API_URL=http://your-server-ip:8000" > .env.production.local

npm install
npm run build
```

This creates a `frontend/build/` folder.  
Serve it with Nginx, pointing the root to the `build/` directory.

**Example Nginx config:**

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/frontend/build;
    index index.html;

    # React Router — serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to FastAPI
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## How It Works

### Inference Pipeline

```
RTSP Camera Stream
       │
       ▼
  OpenCV VideoCapture
       │  frame
       ▼
  YOLO model.predict()
       │  results
       ▼
  Annotate frame (bounding boxes + labels)
       │
       ├──── Encode as base64 JPEG
       │            │
       │            ▼
       │     WebSocket broadcast
       │     → Browser renders live
       │
       └──── Save detection to PostgreSQL
             (label, confidence, bbox, snapshot, timestamp)
```

### One Worker Per Camera

Each time you click **Start** on a camera, the backend spawns a background `threading.Thread` for that camera.  
Multiple cameras run in parallel — each has its own:
- OpenCV capture loop
- YOLO inference call
- WebSocket client set for broadcasting frames
- Detection throttle (saves once per 30 seconds per label to avoid flooding the DB)

### WebSocket Frame Protocol

The browser connects to `/stream/ws/{camera_id}`.  
The server sends JSON messages:

```json
{ "type": "frame", "data": "<base64-encoded-JPEG>" }
{ "type": "ping" }
```

The React `VideoStream` component sets the `<img src>` to `data:image/jpeg;base64,...` on every frame message.

# Face Recognition Attendance System

Local face-recognition attendance demo with a FastAPI backend and React camera UI.

## Project structure

```text
backend/
  app/
    routes/
    face/
    models/
    services/
  requirements.txt
frontend/
  src/
```

The backend uses FastAPI, SQLite, OpenCV, InsightFace, and ONNX Runtime. The frontend uses React + Vite.

## Install dependencies

Run once from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
npm --prefix frontend install
```

## Run the application

Start the backend in one terminal from the repository root:

```sh
source .venv/bin/activate
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

Start the frontend in a second terminal from the repository root:

```sh
cd frontend
npm run dev
```

Open the local URL printed by Vite (normally `http://127.0.0.1:5173`). The Vite development server proxies `/api` requests to the backend at `http://127.0.0.1:8001`.

The health endpoint is also available directly at `http://127.0.0.1:8001/api/health` and returns:

```json
{"status": "ok"}
```

## Use the app

Allow camera access when prompted. For enrollment, choose **Enroll person**, start the camera, capture one clear face, enter the person's name, registration number, course, department, and year/semester, confirm consent, and enroll. Registration numbers are unique and normalized to uppercase. These details are saved in SQLite and shown in the directory and attendance history. For attendance, choose **Check in**, capture the person's face, and mark attendance. A person can be checked in once per local calendar day. Remove a person from the directory to delete their face template and attendance history.

The `buffalo_l` model downloads on the first enrollment or recognition request and requires internet access. Model files are stored under `~/.insightface/models/`.

## Privacy and limitations

Enrollment requires an explicit consent confirmation. The service stores the face embedding and consent timestamp, not the captured photo. SQLite data is stored in `backend/data/attendance.sqlite3`, is excluded from Git, and is not encrypted at rest.

This is a local demo with no authentication, liveness detection, or anti-spoofing. Use only with informed consent; review applicable biometric privacy requirements before using real people's data. Review the InsightFace pretrained model license before non-research or commercial use.

## Tests

Run the backend tests from `backend/` with:

```sh
../.venv/bin/python -m unittest discover -s tests
```

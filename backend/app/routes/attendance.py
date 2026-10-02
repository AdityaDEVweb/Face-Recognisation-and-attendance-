import os

from fastapi import APIRouter, HTTPException

from app.face.recognizer import InvalidFaceImage, best_match, extract_face_embedding
from app.models.schemas import RecognitionRequest
from app.services import database


router = APIRouter(prefix="/api/attendance", tags=["attendance"])
MATCH_THRESHOLD = float(os.environ.get("FACE_MATCH_THRESHOLD", "0.45"))


@router.get("")
def get_attendance() -> dict:
    return {
        "records": database.list_attendance(),
        "today_count": database.today_attendance_count(),
    }


@router.post("/recognize")
def recognize_and_check_in(request: RecognitionRequest) -> dict:
    try:
        embedding = extract_face_embedding(request.image)
    except InvalidFaceImage as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="The face model could not start. Check the model download and try again.",
        ) from error

    person, similarity = best_match(embedding, database.list_face_embeddings())
    if person is None or similarity < MATCH_THRESHOLD:
        return {
            "status": "unrecognized",
            "similarity": round(similarity, 4) if similarity is not None else None,
            "student": None,
            "attendance": None,
        }

    attendance, created = database.record_attendance(person["id"])
    return {
        "status": "checked_in" if created else "already_checked_in",
        "similarity": round(similarity, 4),
        "student": {
            "id": person["id"],
            "name": person["name"],
            "registration_number": person["registration_number"],
            "course": person["course"],
            "department": person["department"],
            "year_semester": person["year_semester"],
        },
        "attendance": attendance,
    }
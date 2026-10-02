from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response

from app.face.recognizer import InvalidFaceImage, extract_face_embedding
from app.models.schemas import EnrollmentRequest
from app.services import database


router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("")
def get_students() -> list[dict]:
    return database.list_students()


@router.post("", status_code=201)
def enroll_student(request: EnrollmentRequest) -> dict:
    if not request.consent_given:
        raise HTTPException(
            status_code=400,
            detail="Enrollment requires the person's informed consent.",
        )

    try:
        embedding = extract_face_embedding(request.image)
    except InvalidFaceImage as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="The face model could not start. Check the model download and try again.",
        ) from error

    consented_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        return database.add_student(
            request.name,
            request.registration_number,
            request.course,
            request.department,
            request.year_semester,
            embedding,
            consented_at,
        )
    except database.DuplicateRegistrationError as error:
        raise HTTPException(
            status_code=409,
            detail="That registration number is already enrolled.",
        ) from error
    except database.DuplicatePersonError as error:
        raise HTTPException(
            status_code=409,
            detail="A person with this name is already enrolled.",
        ) from error


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int) -> Response:
    if not database.delete_student(student_id):
        raise HTTPException(status_code=404, detail="Person not found.")
    return Response(status_code=204)
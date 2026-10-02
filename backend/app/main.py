from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.attendance import router as attendance_router
from app.routes.students import router as students_router
from app.services.database import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Face Recognition Attendance System", lifespan=lifespan)
app.include_router(students_router)
app.include_router(attendance_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

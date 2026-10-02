import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator


DATABASE_PATH = Path(
    os.environ.get(
        "ATTENDANCE_DB_PATH",
        Path(__file__).resolve().parents[2] / "data" / "attendance.sqlite3",
    )
)


class DuplicatePersonError(Exception):
    pass


class DuplicateRegistrationError(Exception):
    pass


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _has_unique_name_index(connection: sqlite3.Connection) -> bool:
    for index in connection.execute("PRAGMA index_list(students)").fetchall():
        if not index["unique"]:
            continue
        escaped_name = index["name"].replace('"', '""')
        columns = connection.execute(
            f'PRAGMA index_info("{escaped_name}")'
        ).fetchall()
        if [column["name"] for column in columns] == ["name"]:
            return True
    return False


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connection() as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE,
                registration_number TEXT NOT NULL DEFAULT '',
                course TEXT NOT NULL DEFAULT '',
                department TEXT NOT NULL DEFAULT '',
                year_semester TEXT NOT NULL DEFAULT '',
                face_embedding TEXT NOT NULL,
                consented_at TEXT NOT NULL,
                enrolled_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                attendance_date TEXT NOT NULL,
                checked_in_at TEXT NOT NULL,
                UNIQUE(student_id, attendance_date)
            )
            """
        )
        existing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(students)")
        }
        for column in ("registration_number", "course", "department", "year_semester"):
            if column not in existing_columns:
                connection.execute(
                    f"ALTER TABLE students ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
                )
        if _has_unique_name_index(connection):
            connection.execute(
                """
                CREATE TABLE students_replacement (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE,
                    registration_number TEXT NOT NULL DEFAULT '',
                    course TEXT NOT NULL DEFAULT '',
                    department TEXT NOT NULL DEFAULT '',
                    year_semester TEXT NOT NULL DEFAULT '',
                    face_embedding TEXT NOT NULL,
                    consented_at TEXT NOT NULL,
                    enrolled_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO students_replacement (
                    id, name, registration_number, course, department, year_semester,
                    face_embedding, consented_at, enrolled_at
                )
                SELECT id, name, registration_number, course, department, year_semester,
                       face_embedding, consented_at, enrolled_at
                FROM students
                """
            )
            connection.execute("DROP TABLE students")
            connection.execute("ALTER TABLE students_replacement RENAME TO students")
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS students_registration_number_unique
            ON students(registration_number COLLATE NOCASE)
            WHERE registration_number <> ''
            """
        )


def add_student(
    name: str,
    registration_number: str,
    course: str,
    department: str,
    year_semester: str,
    embedding: list[float],
    consented_at: str,
) -> dict:
    enrolled_at = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        with _connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO students (
                    name, registration_number, course, department, year_semester,
                    face_embedding, consented_at, enrolled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    registration_number,
                    course,
                    department,
                    year_semester,
                    json.dumps(embedding),
                    consented_at,
                    enrolled_at,
                ),
            )
            student_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
        if "registration_number" in str(error).lower():
            raise DuplicateRegistrationError from error
        raise DuplicatePersonError from error

    return {
        "id": student_id,
        "name": name,
        "registration_number": registration_number,
        "course": course,
        "department": department,
        "year_semester": year_semester,
        "enrolled_at": enrolled_at,
    }


def list_students() -> list[dict]:
    with _connection() as connection:
        rows = connection.execute(
                 """
                 SELECT id, name, registration_number, course, department, year_semester,
                     enrolled_at
                 FROM students ORDER BY name COLLATE NOCASE
                 """
        ).fetchall()
    return [dict(row) for row in rows]


def delete_student(student_id: int) -> bool:
    with _connection() as connection:
        cursor = connection.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return cursor.rowcount > 0


def list_face_embeddings() -> list[dict]:
    with _connection() as connection:
        rows = connection.execute(
                 """
                 SELECT id, name, registration_number, course, department, year_semester,
                     face_embedding
                 FROM students
                 """
        ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "registration_number": row["registration_number"],
            "course": row["course"],
            "department": row["department"],
            "year_semester": row["year_semester"],
            "embedding": json.loads(row["face_embedding"]),
        }
        for row in rows
    ]


def list_attendance(limit: int = 30) -> list[dict]:
    with _connection() as connection:
        rows = connection.execute(
            """
                 SELECT attendance.id, students.id AS student_id, students.name,
                     students.registration_number, students.course, students.department,
                     students.year_semester,
                   attendance.attendance_date, attendance.checked_in_at
            FROM attendance
            JOIN students ON students.id = attendance.student_id
            ORDER BY attendance.checked_in_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def today_attendance_count() -> int:
    today = date.today().isoformat()
    with _connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM attendance WHERE attendance_date = ?",
            (today,),
        ).fetchone()
    return row["count"]


def record_attendance(student_id: int) -> tuple[dict, bool]:
    today = date.today().isoformat()
    checked_in_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with _connection() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO attendance (student_id, attendance_date, checked_in_at)
            VALUES (?, ?, ?)
            """,
            (student_id, today, checked_in_at),
        )
        row = connection.execute(
            """
            SELECT id, student_id, attendance_date, checked_in_at
            FROM attendance WHERE student_id = ? AND attendance_date = ?
            """,
            (student_id, today),
        ).fetchone()
    return dict(row), cursor.rowcount == 1
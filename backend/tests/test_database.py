import tempfile
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import database


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "attendance.sqlite3"
        self.path_patcher = patch.object(database, "DATABASE_PATH", self.database_path)
        self.path_patcher.start()
        database.initialize_database()

    def tearDown(self) -> None:
        self.path_patcher.stop()
        self.temp_dir.cleanup()

    def test_enrollment_stores_embedding_but_list_hides_it(self) -> None:
        person = database.add_student(
            "Alex", "REG-001", "Computer Science", "Computing", "Year 1",
            [0.6, 0.8], "2026-10-02T12:00:00+00:00",
        )

        self.assertEqual(database.list_students()[0]["id"], person["id"])
        self.assertEqual(database.list_students()[0]["registration_number"], "REG-001")
        self.assertEqual(database.list_students()[0]["course"], "Computer Science")
        self.assertEqual(database.list_students()[0]["department"], "Computing")
        self.assertEqual(database.list_students()[0]["year_semester"], "Year 1")
        self.assertEqual(database.list_face_embeddings()[0]["embedding"], [0.6, 0.8])
        second_person = database.add_student(
            "alex", "REG-002", "Computer Science", "Computing", "Year 1",
            [0.6, 0.8], "2026-10-02T12:00:00+00:00",
        )
        self.assertNotEqual(person["id"], second_person["id"])
        self.assertEqual(len(database.list_students()), 2)

    def test_registration_number_must_be_unique_case_insensitively(self) -> None:
        database.add_student(
            "Alex", "REG-001", "Computer Science", "Computing", "Year 1",
            [0.6, 0.8], "2026-10-02T12:00:00+00:00",
        )

        with self.assertRaises(database.DuplicateRegistrationError):
            database.add_student(
                "Sam", "reg-001", "Mathematics", "Science", "Year 2",
                [0.6, 0.8], "2026-10-02T12:00:00+00:00",
            )

    def test_initialize_migrates_existing_students_and_attendance(self) -> None:
        legacy_path = Path(self.temp_dir.name) / "legacy.sqlite3"
        with sqlite3.connect(legacy_path) as connection:
            connection.execute(
                """
                CREATE TABLE students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    face_embedding TEXT NOT NULL,
                    consented_at TEXT NOT NULL,
                    enrolled_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    attendance_date TEXT NOT NULL,
                    checked_in_at TEXT NOT NULL,
                    UNIQUE(student_id, attendance_date)
                )
                """
            )
            connection.execute(
                """
                INSERT INTO students (name, face_embedding, consented_at, enrolled_at)
                VALUES (?, ?, ?, ?)
                """,
                ("Existing", json.dumps([0.6, 0.8]), "consented", "enrolled"),
            )
            connection.execute(
                """
                INSERT INTO attendance (student_id, attendance_date, checked_in_at)
                VALUES (1, date('now', 'localtime'), 'checked-in')
                """
            )

        with patch.object(database, "DATABASE_PATH", legacy_path):
            database.initialize_database()
            students = database.list_students()
            attendance = database.list_attendance()
            embeddings = database.list_face_embeddings()

        self.assertEqual(students[0]["registration_number"], "")
        self.assertEqual(embeddings[0]["embedding"], [0.6, 0.8])
        self.assertEqual(attendance[0]["name"], "Existing")
        self.assertEqual(attendance[0]["course"], "")

    def test_attendance_is_unique_per_person_per_day_and_cascades_on_delete(self) -> None:
        person = database.add_student(
            "Alex", "REG-001", "Computer Science", "Computing", "Year 1",
            [0.6, 0.8], "2026-10-02T12:00:00+00:00",
        )

        first_record, first_created = database.record_attendance(person["id"])
        repeated_record, repeated_created = database.record_attendance(person["id"])

        self.assertTrue(first_created)
        self.assertFalse(repeated_created)
        self.assertEqual(first_record["id"], repeated_record["id"])
        self.assertEqual(database.list_attendance()[0]["registration_number"], "REG-001")
        self.assertEqual(database.today_attendance_count(), 1)

        database.delete_student(person["id"])
        self.assertEqual(database.today_attendance_count(), 0)


if __name__ == "__main__":
    unittest.main()
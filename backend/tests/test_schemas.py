import unittest

from pydantic import ValidationError

from app.models.schemas import EnrollmentRequest


class EnrollmentSchemaTests(unittest.TestCase):
    def test_registration_fields_are_trimmed_and_number_is_normalized(self) -> None:
        request = EnrollmentRequest(
            name=" Alex Morgan ",
            registration_number=" reg-2026-001 ",
            course=" Computer Science ",
            department=" Computing ",
            year_semester=" Year 1 / Semester 1 ",
            image="data:image/jpeg;base64,AA==",
            consent_given=True,
        )

        self.assertEqual(request.name, "Alex Morgan")
        self.assertEqual(request.registration_number, "REG-2026-001")
        self.assertEqual(request.course, "Computer Science")
        self.assertEqual(request.department, "Computing")
        self.assertEqual(request.year_semester, "Year 1 / Semester 1")

    def test_course_and_academic_details_are_required(self) -> None:
        with self.assertRaises(ValidationError):
            EnrollmentRequest(
                name="Alex Morgan",
                registration_number="REG-2026-001",
                course=" ",
                department="Computing",
                year_semester="Year 1",
                image="data:image/jpeg;base64,AA==",
                consent_given=True,
            )


if __name__ == "__main__":
    unittest.main()
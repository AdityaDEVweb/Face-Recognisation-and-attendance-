from pydantic import BaseModel, Field, field_validator


class EnrollmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    registration_number: str = Field(min_length=1, max_length=40)
    course: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=120)
    year_semester: str = Field(min_length=1, max_length=40)
    image: str = Field(min_length=1, max_length=15_000_000)
    consent_given: bool

    @field_validator("name", "course", "department", "year_semester")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank")
        return cleaned

    @field_validator("registration_number")
    @classmethod
    def clean_registration_number(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Registration number cannot be blank")
        return cleaned


class RecognitionRequest(BaseModel):
    image: str = Field(min_length=1, max_length=15_000_000)
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


APPLICATION_STATUSES = {"applied", "oa", "interview", "offer", "rejected"}


class ApplicationBase(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=160)
    status: str = "applied"
    tag: str | None = Field(default=None, max_length=80)
    source: str | None = Field(default=None, max_length=120)
    deadline: date | None = None
    notes: str | None = None

    @field_validator("company", "role", "tag", "source", "notes", mode="before")
    @classmethod
    def clean_optional_text(cls, value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        value = value.strip().lower()
        if value not in APPLICATION_STATUSES:
            allowed = ", ".join(sorted(APPLICATION_STATUSES))
            raise ValueError(f"status must be one of: {allowed}")
        return value


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, min_length=1, max_length=160)
    status: str | None = None
    tag: str | None = Field(default=None, max_length=80)
    source: str | None = Field(default=None, max_length=120)
    deadline: date | None = None
    notes: str | None = None

    @field_validator("company", "role", "tag", "source", "notes", mode="before")
    @classmethod
    def clean_optional_text(cls, value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value is None:
            return None
        value = value.strip().lower()
        if value not in APPLICATION_STATUSES:
            allowed = ", ".join(sorted(APPLICATION_STATUSES))
            raise ValueError(f"status must be one of: {allowed}")
        return value


class ApplicationOut(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

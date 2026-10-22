from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Category = Literal["Email", "Network", "Hardware", "Software", "Printer", "Access"]
Priority = Literal["Low", "Normal", "High"]
Status = Literal["Open", "In Progress", "Resolved"]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterInput(InputModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def valid_password(cls, value):
        if not value.strip():
            raise ValueError("Password cannot contain only spaces.")
        return value


class LoginInput(InputModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: Literal["employee", "admin"]


class TicketInput(InputModel):
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(min_length=15, max_length=10000)
    category: Category
    priority: Priority = "Normal"

    @field_validator("title", "description", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class TicketUpdate(InputModel):
    status: Status
    priority: Priority
    category: Category
    version: int = Field(ge=1)


class CommentInput(InputModel):
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body", mode="before")
    @classmethod
    def trim_body(cls, value):
        return value.strip() if isinstance(value, str) else value


class TicketOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    category: Category
    priority: Priority
    status: Status
    created_by: int
    creator: UserOutput
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    version: int


class CommentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    body: str
    author: UserOutput
    created_at: datetime


class EventOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    message: str
    author: UserOutput
    created_at: datetime


class TicketDetail(TicketOutput):
    comments: list[CommentOutput]
    events: list[EventOutput]


class TicketPage(BaseModel):
    items: list[TicketOutput]
    total: int
    page: int
    page_size: int


class DashboardOutput(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    high_priority: int
    recent: list[TicketOutput]

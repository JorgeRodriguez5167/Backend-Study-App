from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str
    email: str
    first_name: str
    last_name: str
    age: int
    major: str

    notes: List["Note"] = Relationship(back_populates="user")


class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    audio: str
    transcription: str
    summarized_notes: str
    category: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user_id: int = Field(foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="notes")

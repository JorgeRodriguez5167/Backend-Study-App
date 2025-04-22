from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, date
from sqlalchemy import Column, Text, String

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str
    email: str
    first_name: str
    last_name: str
    age: int
    date_of_birth: Optional[date] = None
    major: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    notes: List["Note"] = Relationship(back_populates="user")


class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default="Untitled Note")
    transcription: str = Field(sa_column=Column(Text(length=16777215), nullable=False))  # MEDIUMTEXT (up to 16MB)
    summarized_notes: str = Field(sa_column=Column(Text, nullable=False))  # TEXT (up to 64KB)
    category: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user_id: int = Field(foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="notes")

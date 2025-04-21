from sqlmodel import SQLModel, create_engine
import os
from pathlib import Path

# Ensure data directory exists
 data_dir = Path(os.environ.get("DATA_DIR", "."))
 data_dir.mkdir(exist_ok=True)

# Use environment variable for database path or default to data directory
 sqlite_file_name = os.path.join(data_dir, os.environ.get("DATABASE_NAME", "database.db"))
 sqlite_url = f"sqlite:///{sqlite_file_name}"

print(f"Using database at: {sqlite_file_name}")
 engine = create_engine(sqlite_url, echo=True, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

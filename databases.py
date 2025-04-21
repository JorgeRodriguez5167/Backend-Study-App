from sqlmodel import SQLModel, create_engine
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from Railway or use local MySQL configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Railway provides the full database URL
    print("Using Railway database URL")
    engine = create_engine(DATABASE_URL, echo=True)
else:
    # Local MySQL configuration
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "study_app")

    # Create MySQL connection URL
    mysql_url = f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    print(f"Using local MySQL database at: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
    engine = create_engine(mysql_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

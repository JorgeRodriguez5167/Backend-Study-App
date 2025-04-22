from sqlmodel import SQLModel, create_engine
import os
from pathlib import Path
import logging

# Set up logging
logger = logging.getLogger(__name__)

# MySQL database connection settings from environment variables
# Default values are set for Railway, but can be overridden with environment variables
mysql_host = os.environ.get("MYSQLHOST", "mysql.railway.internal")
mysql_port = os.environ.get("MYSQLPORT", "3306")
mysql_user = os.environ.get("MYSQLUSER", "root")
mysql_password = os.environ.get("MYSQLPASSWORD", "YJXnVfHQzvwQtLvDVZYjUlPoIOrZMcQP")
mysql_database = os.environ.get("MYSQLDATABASE", "railway")

# Check if we should use SQLite for local development
use_sqlite = os.environ.get("USE_SQLITE", "False").lower() == "true"

if use_sqlite:
    # SQLite configuration for local development and testing
    data_dir = Path(os.environ.get("DATA_DIR", "."))
    data_dir.mkdir(exist_ok=True)
    sqlite_file_name = os.path.join(data_dir, os.environ.get("DATABASE_NAME", "database.db"))
    db_url = f"sqlite:///{sqlite_file_name}"
    connect_args = {"check_same_thread": False}
    logger.info(f"Using SQLite database at: {sqlite_file_name}")
else:
    # MySQL configuration for production
    db_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
    connect_args = {}
    logger.info(f"Using MySQL database at: {mysql_host}:{mysql_port}/{mysql_database}")

# Create database engine
try:
    engine = create_engine(db_url, echo=True, connect_args=connect_args)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise

def create_db_and_tables():
    """Create database tables if they don't exist"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise

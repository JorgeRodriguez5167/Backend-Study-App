from sqlmodel import SQLModel, create_engine
import os
from dotenv import load_dotenv
import logging
from urllib.parse import quote_plus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_engine():
    # Get database URL from Railway or use local MySQL configuration
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if DATABASE_URL:
        # Railway provides the full database URL
        logger.info("Using Railway database URL")
        try:
            # Ensure the URL is properly formatted
            if not DATABASE_URL.startswith("mysql://"):
                DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://")
            engine = create_engine(DATABASE_URL, echo=True)
            logger.info("Successfully connected to Railway database")
            return engine
        except Exception as e:
            logger.error(f"Failed to connect to Railway database: {str(e)}")
            raise
    else:
        # Local MySQL configuration
        MYSQL_USER = os.getenv("MYSQL_USER", "root")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
        MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
        MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
        MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "study_app")

        # URL encode the password
        encoded_password = quote_plus(MYSQL_PASSWORD)
        
        # Create MySQL connection URL with explicit TCP/IP connection
        mysql_url = f"mysql+pymysql://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        logger.info(f"Using local MySQL database at: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
        
        try:
            engine = create_engine(mysql_url, echo=True)
            logger.info("Successfully connected to local MySQL database")
            return engine
        except Exception as e:
            logger.error(f"Failed to connect to local MySQL database: {str(e)}")
            raise

# Create engine instance
engine = get_engine()

def create_db_and_tables():
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise

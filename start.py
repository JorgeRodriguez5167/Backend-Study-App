# start.py
import os
import uvicorn
import logging
from dotenv import load_dotenv
import sys
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('startup.log')
    ]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['DATABASE_URL', 'PORT', 'HOST']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    return True

if __name__ == "__main__":
    try:
        # Check environment variables
        if not check_environment():
            logger.error("Missing required environment variables. Exiting...")
            sys.exit(1)

        # Get port from Railway environment variable or default to 8000
        port = int(os.environ.get("PORT", 8000))
        # Get host from Railway environment variable or default to 0.0.0.0
        host = os.environ.get("HOST", "0.0.0.0")
        # Get reload from environment variable or default to False
        reload = os.environ.get("RELOAD", "False").lower() == "true"
        
        logger.info(f"Starting server on {host}:{port}")
        logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
        logger.info(f"Database URL: {os.environ.get('DATABASE_URL', 'Not set')}")
        
        # Add a small delay to allow for database initialization
        time.sleep(2)
        
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            access_log=True,
            workers=1,
            timeout_keep_alive=300
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)

# start.py
import os
import uvicorn
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Get port from Railway environment variable or default to 8000
        port = int(os.environ.get("PORT", 8000))
        # Get host from Railway environment variable or default to 0.0.0.0
        host = os.environ.get("HOST", "0.0.0.0")
        # Get reload from environment variable or default to False
        reload = os.environ.get("RELOAD", "False").lower() == "true"
        
        logger.info(f"Starting server on {host}:{port}")
        logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
        logger.info(f"Database URL: {os.environ.get('DATABASE_URL', 'Not set')}")
        
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            access_log=True,
            workers=1
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise

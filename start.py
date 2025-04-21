# start.py
import os
import uvicorn

if __name__ == "__main__":
    # Get port from Railway environment variable or default to 8000
    port = int(os.environ.get("PORT", 8000))
    # Get host from Railway environment variable or default to 0.0.0.0
    host = os.environ.get("HOST", "0.0.0.0")
    # Get reload from environment variable or default to False
    reload = os.environ.get("RELOAD", "False").lower() == "true"
    
    uvicorn.run("main:app", host=host, port=port, reload=reload)

"""
main.py — start the server with: python main.py
or via uvicorn: uvicorn main:app --reload
"""

import logging
import uvicorn
from api.webhook import app
from utils.config import settings

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

if __name__ == "__main__":
    uvicorn.run(
        "api.webhook:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
    )

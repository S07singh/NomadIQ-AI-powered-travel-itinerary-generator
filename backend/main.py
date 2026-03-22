"""
NomadIQ — AI-Powered Travel Planner Backend

Entry point for the FastAPI server.
"""

from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from config.logger import setup_logging

# Configure logging
setup_logging(console_level="INFO")

from loguru import logger

logger.info("🌍 Starting NomadIQ Backend")

from api.app import app

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Launching NomadIQ API on http://localhost:8000")
    logger.info("📖 API Docs available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

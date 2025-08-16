"""FastAPI application for serving React console."""

import logging
from pathlib import Path
from typing import Dict, Any
import pkg_resources

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


def create_app(config: Dict[str, Any]) -> FastAPI:
    """Create FastAPI application with configuration."""
    app = FastAPI(
        title="Pandemic Console",
        description="Web-based dashboard for Pandemic edge computing system",
        version="1.0.0",
        docs_url=None,  # Disable docs for production
        redoc_url=None
    )
    
    # Get console files directory from package data
    try:
        console_dir = Path(pkg_resources.resource_filename('pandemic_console', 'console'))
        
        # Mount React's static files at /static (to match React's expectations)
        static_dir = console_dir / "static"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        @app.get("/")
        async def serve_react_app():
            """Serve React application."""
            index_file = console_dir / "index.html"
            return FileResponse(str(index_file))
        
        @app.get("/{path:path}")
        async def serve_react_routes(path: str):
            """Serve React routes (SPA routing)."""
            # For SPA routing, always serve index.html for non-API routes
            if not path.startswith("api/") and not path.startswith("static/"):
                index_file = console_dir / "index.html"
                return FileResponse(str(index_file))
            return {"error": "Not found"}
            
    except (ImportError, FileNotFoundError):
        # Fallback for development when console files aren't built
        @app.get("/")
        async def development_message():
            """Development message when console files not built."""
            return {
                "message": "Pandemic Console Development Mode",
                "instructions": [
                    "1. cd src/frontend",
                    "2. npm install",
                    "3. npm run build",
                    "4. pip install -e . (to include console files)",
                    "5. Restart the console service"
                ]
            }
    
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "pandemic-console"}
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    return app
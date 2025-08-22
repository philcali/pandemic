"""FastAPI application factory."""

import logging
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthManager
from .client import PandemicClient
from .routes.auth import create_auth_router
from .routes.health import create_health_router
from .routes.infections import create_infections_router
from .users import create_user_provider


def create_app(config: Dict[str, Any]) -> FastAPI:
    """Create FastAPI application with configuration."""
    # Create FastAPI app
    app = FastAPI(
        title="Pandemic REST API",
        description="HTTP REST API for Pandemic edge computing system",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    cors_config = config.get("cors", {})
    if cors_config.get("enabled", True):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_config.get("origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Create dependencies
    daemon_config = config.get("daemon", {})
    client = PandemicClient(
        socket_path=daemon_config.get("socket_path", "/var/run/pandemic/daemon.sock")
    )

    # Create user provider and auth manager
    user_management_config = config.get("user_management", {"provider": "local"})
    user_provider = create_user_provider(user_management_config)

    auth_config = config.get("auth", {})
    auth_manager = AuthManager(
        jwt_secret=auth_config.get("jwt_secret", "dev-secret-change-in-production"),
        jwt_expiry=auth_config.get("jwt_expiry", 3600),
        user_provider=user_provider,
    )

    # Create and include routers
    auth_router = create_auth_router(auth_manager)
    health_router = create_health_router(auth_manager, client)
    infections_router = create_infections_router(auth_manager, client)

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(infections_router, prefix="/api/v1")

    # Store dependencies for access in other parts of the app
    app.state.client = client
    app.state.auth_manager = auth_manager
    app.state.config = config

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "Pandemic REST API", "version": "1.0.0", "docs": "/docs"}

    return app

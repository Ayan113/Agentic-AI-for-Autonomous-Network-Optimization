"""
FastAPI application for the Agentic AI Network Optimizer.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routes import router
from ..agents.coordinator import Coordinator
from ..utils.config import get_config
from ..utils.logging import setup_logging, console


# Global coordinator instance
coordinator: Optional[Coordinator] = None

# Frontend directory
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global coordinator
    
    # Startup
    console.print("[bold green]Starting Agentic AI Network Optimizer API...[/]")
    console.print(f"[cyan]Frontend: http://localhost:8000[/]")
    console.print(f"[cyan]API Docs: http://localhost:8000/docs[/]")
    setup_logging()
    coordinator = Coordinator()
    
    yield
    
    # Shutdown
    if coordinator:
        await coordinator.stop()
    console.print("[bold yellow]API shutdown complete[/]")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title="Agentic AI Network Optimizer",
        description="Multi-agent AI system for autonomous network monitoring and optimization",
        version=config.system.version,
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router, prefix="/api")
    
    # Also mount routes at root for backward compatibility
    app.include_router(router)
    
    # Serve frontend static files
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
        
        @app.get("/")
        async def serve_frontend():
            return FileResponse(FRONTEND_DIR / "index.html")
    
    return app


def get_coordinator() -> Coordinator:
    """Get the global coordinator instance."""
    global coordinator
    if coordinator is None:
        coordinator = Coordinator()
    return coordinator


# Create the app instance
app = create_app()

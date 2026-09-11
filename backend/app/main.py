import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.core.config import settings
from backend.app.api import cameras, tracking, watchlist, alerts, evidence, system, analytics, auth, cases, ingest
from backend.app.core.realtime import alert_broadcaster

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Statewide CCTV Integration, AI Video Analytics & Intelligence Platform for Gujarat Police Hackathon 2026"
)

from backend.app.core.telemetry import APITelemetryMiddleware

# Keep browser origins explicit. Override with CORS_ORIGINS for deployment.
app.add_middleware(APITelemetryMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(cameras.router, prefix=settings.API_V1_STR)
app.include_router(ingest.router, prefix=settings.API_V1_STR)
app.include_router(tracking.router, prefix=settings.API_V1_STR)
app.include_router(watchlist.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(cases.router, prefix=settings.API_V1_STR)
app.include_router(evidence.router, prefix=settings.API_V1_STR)
app.include_router(system.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)


@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    await alert_broadcaster.connect(websocket)
    try:
        while True:
            # Clients may send ping to keep the connection active.
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await alert_broadcaster.disconnect(websocket)
    except Exception:
        await alert_broadcaster.disconnect(websocket)


frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def serve_index():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "GIVIN API is running. Frontend index.html not yet mounted."}


from fastapi import Response, status
from backend.app.core.database import check_db_health

@app.get("/health")
def root_health(response: Response):
    db_h = check_db_health()
    is_ready = (db_h.get("status") == "READY")
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "healthy" if is_ready else "unhealthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "database": db_h.get("status"),
        "realtime_alerts": "enabled",
        "docs_url": "/docs"
    }


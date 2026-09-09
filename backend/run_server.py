import os
import sys

# Windows OpenMP library duplication workaround
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uvicorn
from backend.app.seed_data import seed_database

if __name__ == "__main__":
    print("=" * 75)
    print("  GIVIN - Gujarat Integrated Video Intelligence Network")
    print("  Gujarat Police Innovation Hackathon 2026")
    print("  Statewide CCTV Integration, AI Video Analytics & Intelligence Platform")
    print("=" * 75)
    
    # Ensure database is seeded
    seed_database()

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"\n[INFO] Starting GIVIN C4I Server on http://{host}:{port}")
    print(f"[DOCS] Swagger API Docs: http://{host}:{port}/docs")
    print(f"[UI]   Command Center UI: http://{host}:{port}/\n")
    
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=False)

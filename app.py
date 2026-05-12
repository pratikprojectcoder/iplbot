"""
Dual entry for this repo:

- **Streamlit dashboard:** `streamlit run app.py`  
  Loads `streamlit_app.py` (your original UI).

- **FastAPI + React (same as http://127.0.0.1:8000):** set `FASTAPI_ONLY=1`, then  
  `uvicorn app:app --host 0.0.0.0 --port 8000`  
  Re-exports the FastAPI `app` from `api/main.py`, which already includes CORS,
  `/api/...` routes, and serving `web/dist` (React).

The tutorial pattern (StaticFiles, FileResponse, CORSMiddleware) lives in
`api/main.py` so one implementation stays consistent; importing here avoids
running Streamlit when Uvicorn loads this module.
"""
import os

if os.environ.get("FASTAPI_ONLY") == "1":
    from api.main import app  # noqa: F401
else:
    import streamlit_app  # noqa: F401 — Streamlit UI (side effects on import)

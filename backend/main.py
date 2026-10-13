"""
NomadIQ API entry point.

    python main.py                       # dev server with reload
    uvicorn main:app --host 0.0.0.0      # production (add --workers N)
"""

from app.main import build_default_app

app = build_default_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

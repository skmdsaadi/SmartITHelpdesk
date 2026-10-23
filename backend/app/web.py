"""Expose only the compiled UI, never the repository or backend directory."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI, directory: Path):
    if not (directory / "index.html").is_file() or not (directory / "assets").is_dir():
        return  # Vite serves the UI separately during local development.

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def index():
        return FileResponse(directory / "index.html")

    app.mount("/assets", StaticFiles(directory=directory / "assets"), name="assets")
    # Navigation uses URL hashes. Unknown API, asset and filesystem paths stay 404.

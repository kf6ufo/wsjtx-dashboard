"""Offline browser test host only. Never run this module on a station LAN."""
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from backend.app import create_app
from backend.receiver import Settings, ingest

app = create_app(Settings(enabled=False), serve_frontend=False)


class Fixture(BaseModel):
    hex: str


@app.post('/fixture/packet')
async def packet(body: Fixture):
    ingest(bytes.fromhex(body.hex), app.state.focus)
    return app.state.focus.snapshot()

app.mount('/', StaticFiles(directory=Path(__file__).resolve().parents[2] / 'dist', html=True), name='test-dashboard')

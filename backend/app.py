import asyncio
from contextlib import asynccontextmanager, suppress
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .receiver import Settings, create_socket, receive
from .state import FocusState


class BrowseRequest(BaseModel):
    call: str = Field(min_length=3, max_length=15)


def create_app(settings: Settings | None = None, state: FocusState | None = None, *, serve_frontend=True):
    settings, state = settings or Settings.from_env(), state or FocusState()

    @asynccontextmanager
    async def lifespan(_app):
        task, sock = None, None
        state.receiver.update(group=settings.group, port=settings.port, interface=settings.interface)
        if settings.enabled:
            try:
                sock = create_socket(settings)
                state.receiver['status'] = 'listening'
                task = asyncio.create_task(receive(sock, state))
            except OSError:
                state.receiver.update(status='error', error='Cannot join multicast. Check address, port and local interface.')
        state.publish()
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            if sock:
                sock.close()

    app = FastAPI(title='WSJT-X focus service', lifespan=lifespan)
    app.state.focus = state

    @app.get('/api/snapshot')
    async def snapshot():
        return state.snapshot()

    @app.post('/api/focus')
    async def browse(body: BrowseRequest, request: Request):
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'Use the dashboard on the same origin')
        if not state.browse(body.call):
            raise HTTPException(404, 'Callsign is not in radio selection history')
        return state.snapshot()

    @app.get('/api/events')
    async def events():
        try:
            queue = state.subscribe()
        except ValueError:
            raise HTTPException(503, 'Browser stream capacity reached')
        async def stream():
            try:
                while True:
                    try:
                        snapshot = await asyncio.wait_for(queue.get(), timeout=15)
                    except asyncio.TimeoutError:
                        yield ': keepalive\n\n'
                    else:
                        yield f"event: snapshot\ndata: {json.dumps(snapshot, separators=(',', ':'))}\n\n"
            finally:
                state.unsubscribe(queue)
        return StreamingResponse(stream(), media_type='text/event-stream', headers={
            'Cache-Control': 'no-cache, no-store', 'X-Accel-Buffering': 'no'})

    # Build output is optional for Mac Vite development; APIs precede the static mount.
    dist = Path(__file__).resolve().parent.parent / 'dist'
    if serve_frontend and dist.is_dir():
        app.mount('/', StaticFiles(directory=dist, html=True), name='dashboard')
    return app


app = create_app()

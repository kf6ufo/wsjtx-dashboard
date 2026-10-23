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
from .foundation import FoundationState
from .workspace import WorkspaceState
from .runtime import ReceiverRuntime
from .config import save_receiver_config
from dataclasses import asdict


class BrowseRequest(BaseModel):
    call: str = Field(min_length=3, max_length=15)


def create_app(settings: Settings | None = None, state: FocusState | None = None, *, serve_frontend=True, config_path: Path | None = None):
    settings, state = settings or Settings(), state or FocusState()

    runtime = ReceiverRuntime(state) if isinstance(state, WorkspaceState) else None

    @asynccontextmanager
    async def lifespan(_app):
        task, sock = None, None
        state.receiver.update(group=settings.group, port=settings.port, interface=settings.interface)
        if runtime:
            await runtime.apply(settings)
        elif settings.enabled:
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
            if runtime:
                await runtime.stop()
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            if sock:
                sock.close()
            if isinstance(state, WorkspaceState):
                state.close()
            elif isinstance(state, FoundationState):
                state.database.close()

    app = FastAPI(title='WSJT-X focus service', lifespan=lifespan)
    app.state.focus = state

    @app.middleware('http')
    async def same_origin(request: Request, call_next):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            origin = request.headers.get('origin')
            if (origin and origin != str(request.base_url).rstrip('/')) or request.headers.get('sec-fetch-site') == 'cross-site':
                from fastapi.responses import JSONResponse
                return JSONResponse({'detail': 'Use the dashboard on the same origin'}, status_code=403)
        return await call_next(request)

    if isinstance(state, FoundationState):
        if settings.enabled and not runtime:
            raise ValueError('Step 0 cannot enable UDP reception')

        class SampleSelection(BrowseRequest):
            rigId: str = Field(max_length=80)

        class Preferences(BaseModel):
            model_config = {'extra': 'forbid'}
            title: str = Field(min_length=1, max_length=60, pattern=r'^[^\x00-\x1f]+$')
            appearance: str = Field(pattern=r'^(dark|light)$')
            radioStrip: bool = Field(strict=True)

        @app.post('/api/sample/select')
        async def sample_select(body: SampleSelection):
            try:
                state.select_sample(body.call, body.rigId)
            except ValueError as exc:
                raise HTTPException(422, str(exc))
            return state.snapshot()

        @app.put('/api/settings')
        async def preferences(body: Preferences):
            state.preferences = body.model_dump()
            state.publish()
            if getattr(state, 'storage_error', None):
                raise HTTPException(503, state.storage_error)
            return state.snapshot()

    if runtime:
        class ReceiverRequest(BaseModel):
            model_config = {'extra': 'forbid'}
            enabled: bool = Field(strict=True)
            listen: str
            port: int = Field(ge=1024, le=65535, strict=True)
            group: str
            interface: str
            retention: int = Field(ge=50, le=500, strict=True)

        @app.put('/api/receiver')
        async def receiver_settings(body: ReceiverRequest):
            if config_path is None:
                raise HTTPException(503, 'Receiver settings require the installed config.toml entry point')
            try:
                new = Settings(**body.model_dump())
            except ValueError as exc:
                raise HTTPException(422, str(exc))
            async with runtime.lock:
                try:
                    save_receiver_config(config_path, new)
                except (ValueError, OSError) as exc:
                    raise HTTPException(503, f'Configuration not saved: {exc}')
                old = asdict(runtime.settings)
                updated = asdict(new)
                if {k: v for k, v in old.items() if k != 'retention'} == {k: v for k, v in updated.items() if k != 'retention'}:
                    runtime.settings = new
                    state.configure_receiver(new)
                    state.flush()
                else:
                    await runtime.apply(new)
            return state.snapshot()

        @app.post('/api/receiver/restart')
        async def receiver_restart():
            async with runtime.lock:
                await runtime.apply(runtime.settings)
            return state.snapshot()

        @app.get('/api/diagnostics')
        async def diagnostics():
            return state.diagnostic_rows()

        @app.get('/api/diagnostics/{sequence}')
        async def diagnostic_detail(sequence: int):
            detail = state.diagnostic_detail(sequence)
            if detail is None:
                raise HTTPException(404, 'Packet has expired from diagnostic retention')
            return detail

        @app.delete('/api/diagnostics')
        async def clear_diagnostics():
            state.clear_diagnostics()
            return state.diagnostic_rows()

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


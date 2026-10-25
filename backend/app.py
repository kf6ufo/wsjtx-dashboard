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
from .config import save_receiver_config, save_enrichment_config, save_wavelog_config, load_config
from .wavelog import WavelogService, WavelogError
from .wavelog_config import update_wavelog_settings
from .enrichment import EnrichmentService, EnrichmentSettings, update_settings
from .state import normalize_call
from .qso_config import update_qso_settings
from .qso_history import QsoHistoryService
from .qso_delivery import QsoDeliveryService
from .qso_model import QsoError
from .config import save_qso_config
from dataclasses import asdict


class BrowseRequest(BaseModel):
    call: str = Field(min_length=3, max_length=15)


def create_app(settings: Settings | None = None, state: FocusState | None = None, *, serve_frontend=True, config_path: Path | None = None, enrichment_settings: EnrichmentSettings | None = None):
    settings, state = settings or Settings(), state or FocusState()

    runtime = ReceiverRuntime(state) if isinstance(state, WorkspaceState) else None
    enrich = None
    wavelog = None
    qso_history = delivery = None
    config_lock = asyncio.Lock()
    if runtime and config_path:
        enrichment_settings = enrichment_settings or load_config(config_path).enrichment
        enrich = EnrichmentService(state, enrichment_settings, config_path.parent / 'data' / 'enrichment')
        state.enrichment_service = enrich
        wavelog = WavelogService(state, load_config(config_path).wavelog)
        state.wavelog_service = wavelog
        qso_settings = load_config(config_path).qso
        if qso_settings.adif_path or qso_settings.logging_enabled: state.enter_radio_workspace()
        qso_history = QsoHistoryService(state, qso_settings, wavelog)
        state.qso_history = qso_history
        delivery = QsoDeliveryService(state, qso_settings, wavelog, enrich, config_path.parent / 'data' / 'delivery.sqlite3', qso_history)
        state.qso_service = delivery

    @asynccontextmanager
    async def lifespan(_app):
        task, sock = None, None
        state.receiver.update(group=settings.group, port=settings.port, interface=settings.interface)
        if runtime:
            await runtime.apply(settings)
            if enrich:
                await enrich.start()
            if wavelog:
                await wavelog.start()
            if qso_history: await qso_history.start()
            if delivery: await delivery.start()
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
            if runtime: await runtime.stop()
            if delivery: await delivery.stop()
            if qso_history: await qso_history.stop()
            if wavelog:
                await wavelog.stop()
            if enrich:
                await enrich.stop()
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

    if wavelog:
        @app.put('/api/wavelog')
        async def wavelog_config(request: Request):
            try:
                payload = await request.json()
                async with config_lock:
                    new = update_wavelog_settings(wavelog.settings, payload)
                    save_wavelog_config(config_path, new)
                    wavelog.configure(new)
            except (ValueError, TypeError, OSError):
                raise HTTPException(422, 'Wavelog settings could not be saved. Check the URL, API v2 token, scope, limits and file permissions.')
            return state.snapshot()

        @app.post('/api/wavelog/test')
        async def wavelog_test():
            try:
                return await wavelog.test()
            except WavelogError as error:
                raise HTTPException(409, str(error))

        @app.post('/api/wavelog/refresh')
        async def wavelog_refresh():
            wavelog.refresh()
            return state.snapshot()

        @app.get('/api/wavelog/history/{lookup_id}')
        async def wavelog_history(lookup_id: str):
            try:
                return wavelog.history(lookup_id)
            except WavelogError as error:
                raise HTTPException(409, str(error))

    if delivery:
        @app.put('/api/qso/settings')
        async def qso_settings(request: Request):
            try:
                payload = await request.json()
                async with config_lock:
                    new = update_qso_settings(delivery.settings, payload)
                    if new.logging_enabled and new.log_to_wavelog and not (wavelog.settings.url and wavelog.settings.token):
                        raise ValueError('Configure Wavelog before enabling delivery')
                    save_qso_config(config_path, new)
                    delivery.settings = new
                    if new.adif_path or new.logging_enabled: state.enter_radio_workspace()
                    qso_history.configure(new)
                    delivery.retry()
                    state.flush()
            except (ValueError, TypeError, OSError):
                raise HTTPException(422, 'QSO settings could not be saved. Check the absolute ADIF path, coverage and rig mappings.')
            return state.snapshot()

        @app.get('/api/qso/history/{lookup_id}')
        async def qso_history_records(lookup_id: str, band: str | None = None, mode: str | None = None):
            from .qso_history import filter_history
            try: return filter_history(qso_history.history(lookup_id), band, mode)
            except QsoError: raise HTTPException(409, 'History changed; refresh the current station')

        @app.post('/api/qso/history/refresh')
        async def qso_history_refresh():
            qso_history.refresh()
            return state.snapshot()

        @app.post('/api/qso/retry')
        async def qso_retry():
            delivery.retry(); state.flush()
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
            async with config_lock, runtime.lock:
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

    if enrich:
        @app.put('/api/enrichment')
        async def enrichment_config(request: Request):
            try:
                body = await request.json()
                async with config_lock:
                    new = update_settings(enrich.settings, body)
                    save_enrichment_config(config_path, new)
                    enrich.configure(new)
            except (ValueError, TypeError, OSError):
                raise HTTPException(422, 'Enrichment settings could not be saved. Check values, ranges and file permissions.')
            return state.snapshot()

        @app.post('/api/enrichment/refresh')
        async def enrichment_refresh():
            enrich.configure(enrich.settings, refresh=True)
            return state.snapshot()

        @app.post('/api/enrichment/test')
        async def enrichment_test(request: Request):
            try:
                body = await request.json()
                call = normalize_call(body.get('call', ''))
                if not call:
                    raise ValueError('Enter a valid test callsign')
                return await enrich.test(call)
            except (ValueError, TypeError, AttributeError):
                raise HTTPException(422, 'Enter a valid test callsign, and wait for any running provider lookup.')

    if runtime:
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

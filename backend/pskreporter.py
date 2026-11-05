"""One receive-only MQTT connection, bounded volatile cache, shared via SSE.

The network thread only appends to a bounded queue. All application state and
cache mutation happens on the server loop. Focus never causes a network query.
"""
import asyncio
from contextlib import suppress
import json
import math
import queue
import re
import time
from .protocol import band_from_hz
from .state import normalize_call

BROKER = 'mqtt.pskreporter.info'
PORT = 1884  # Verified TLS, no credentials and no plaintext fallback.
CACHE_LIMIT = 10000
MAX_AGE = 3600


def topic_for(call):
    # Portable calls use a literal slash, which occupies another MQTT level.
    return f'pskr/filter/v2/+/+/{call}/#'


def parse_spot(payload, calls, now):
    """Validate the documented compact JSON schema; never accept reverse spots."""
    if not isinstance(payload, bytes) or len(payload) > 4096:
        return None
    try:
        data = json.loads(payload)
        if not isinstance(data, dict): return None
        tx, rx = data.get('sc'), data.get('rc')
        if not isinstance(tx, str) or not isinstance(rx, str): return None
        tx, rx = normalize_call(tx), normalize_call(rx)
        if tx not in calls or not rx: return None
        grid = data.get('rl')
        if not isinstance(grid, str): return None
        grid = grid.strip().upper()
        if not re.fullmatch(r'[A-R]{2}[0-9]{2}(?:[A-X]{2}(?:[0-9]{2})?)?', grid): return None
        frequency, heard = data.get('f'), data.get('t_tx', data.get('t'))
        if type(frequency) not in (int, float) or not math.isfinite(frequency): return None
        band = band_from_hz(frequency)
        if not band or type(heard) not in (int, float) or not math.isfinite(heard): return None
        if not now - MAX_AGE < heard <= now + 30: return None
        mode, snr = data.get('md'), data.get('rp')
        return dict(sender=tx, receiver=rx, grid=grid, band=band, heardAt=int(heard * 1000),
                    frequency=frequency, mode=mode[:16] if isinstance(mode, str) else '',
                    snr=snr if type(snr) in (int, float) and math.isfinite(snr) and -100 <= snr <= 100 else None)
    except (ValueError, TypeError, UnicodeError, OverflowError):
        return None


def mqtt_client(inbox):
    import paho.mqtt.client as mqtt
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
    client.tls_set()
    client.connect_timeout = 8
    client.reconnect_delay_set(min_delay=2, max_delay=60)

    def offer(kind, value=None):
        try: inbox.put_nowait((kind, value))
        except queue.Full: pass  # Explicitly bounded best-effort feed.

    client.on_connect = lambda c, u, f, reason, p: offer('connected' if not reason.is_failure else 'error')
    client.on_connect_fail = lambda c, u: offer('error')
    client.on_disconnect = lambda c, u, f, reason, p: offer('disconnected')
    client.on_subscribe = lambda c, u, mid, reasons, p: offer('subscription_error' if any(r.is_failure for r in reasons) else 'subscribed')
    client.on_message = lambda c, u, message: offer('spot', message.payload) if len(message.payload) <= 4096 else None
    client.connect_async(BROKER, PORT, keepalive=60)
    client.loop_start()
    return client


class PskReporterService:
    def __init__(self, state, settings, *, client_factory=mqtt_client, clock=time.time):
        self.state, self.settings = state, settings
        self.client_factory, self.clock = client_factory, clock
        self.client = self.task = None
        self.inbox = queue.Queue(maxsize=512)
        self.cache = {}
        self.calls, self.subscribed = set(), set()
        self.status, self.error = 'disabled', ''
        self.connected_at = None
        self.evicted = 0
        self.subscribe_after = 0

    def identities(self):
        if self.settings.callsign: return {self.settings.callsign}
        return {call for rig in self.state.rigs.values()
                if isinstance(raw := rig.get('stationCall'), str) and (call := normalize_call(raw))}

    async def start(self):
        await self.tick()
        self.task = asyncio.create_task(self.run())

    async def stop_client(self):
        client, self.client = self.client, None
        if client:
            client.disconnect()
            await asyncio.to_thread(client.loop_stop)
        self.subscribed.clear()
        self.connected_at = None
        while not self.inbox.empty():
            with suppress(queue.Empty): self.inbox.get_nowait()

    async def stop(self):
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError): await self.task
            self.task = None
        await self.stop_client()

    async def configure(self, settings):
        changed_identity = self.settings.callsign != settings.callsign
        self.settings = settings
        if changed_identity or not settings.enabled:
            self.cache.clear()
            await self.stop_client()
        await self.tick()
        self.state.flush()

    def ingest(self, payload):
        spot = parse_spot(payload, self.calls, self.clock())
        if not spot: return False
        key = (spot['sender'], spot['band'], spot['receiver'])
        previous = self.cache.get(key)
        if previous and previous['heardAt'] >= spot['heardAt']: return False
        self.cache[key] = spot
        if len(self.cache) > CACHE_LIMIT:
            oldest = min(self.cache, key=lambda k: self.cache[k]['heardAt'])
            del self.cache[oldest]
            self.evicted += 1
        return True

    def prune(self):
        cutoff = (self.clock() - MAX_AGE) * 1000
        expired = [key for key, spot in self.cache.items() if spot['heardAt'] <= cutoff or spot['sender'] not in self.calls]
        for key in expired: del self.cache[key]
        return bool(expired)

    async def tick(self):
        self.calls = self.identities() if self.settings.enabled else set()
        changed = self.prune()
        if not self.calls:
            await self.stop_client()
            new_status = 'waiting' if self.settings.enabled else 'disabled'
            changed |= self.status != new_status
            self.status, self.error = new_status, ''
        elif self.client is None:
            try:
                self.client = self.client_factory(self.inbox)
                self.status, self.error = 'connecting', ''
            except (OSError, ValueError, ImportError):
                self.status, self.error = 'error', 'MQTT could not start. Check the installation and internet connection.'
            changed = True
        for _ in range(512):
            try: kind, value = self.inbox.get_nowait()
            except queue.Empty: break
            if kind == 'spot': changed |= self.ingest(value)
            else:
                changed = True
                if kind == 'connected':
                    self.status, self.error = 'connected', ''
                    self.connected_at = int(self.clock() * 1000)
                    self.subscribed.clear()  # Clean session: resubscribe after every reconnect.
                    self.subscribe_after = 0
                elif kind == 'subscription_error':
                    self.status, self.error = 'error', 'MQTT subscription refused; retrying in one minute.'
                    self.subscribed.clear()
                    self.subscribe_after = self.clock() + 60
                elif kind == 'subscribed':
                    if self.clock() >= self.subscribe_after:
                        self.status, self.error = 'connected', ''
                elif kind == 'error':
                    self.status, self.error = 'error', 'MQTT connection or subscription failed; retrying automatically.'
                else:
                    self.status, self.error = 'reconnecting', 'MQTT disconnected; retrying automatically. Recent reports remain until they expire.'
        if self.client and self.client.is_connected() and self.clock() >= self.subscribe_after:
            for call in self.subscribed - self.calls:
                self.client.unsubscribe(topic_for(call))
            self.subscribed.intersection_update(self.calls)
            for call in self.calls - self.subscribed:
                result, _mid = self.client.subscribe(topic_for(call), qos=0)
                if result == 0: self.subscribed.add(call)
                else:
                    self.status, self.error = 'error', 'MQTT subscription could not be sent; retrying in one minute.'
                    self.subscribe_after = self.clock() + 60
                    changed = True
                    break
        if changed: self.state.flush()

    async def run(self):
        while True:
            await asyncio.sleep(2)
            await self.tick()

    def snapshot(self):
        # Send only the shared focus band's hour, rather than repeating every
        # band's reports in ordinary UDP snapshots. Focus filtering is local
        # cache access and never changes upstream subscriptions.
        entry = next((e for e in self.state.history if e['call'] == self.state.call), {})
        rig = self.state.rigs.get(entry.get('rigId'), {})
        sender = self.settings.callsign or entry.get('stationCall') or rig.get('stationCall', '')
        sender = normalize_call(sender) if isinstance(sender, str) else None
        cutoff = (self.clock() - MAX_AGE) * 1000
        return dict(config=self.settings.public(), status=self.status, error=self.error,
                    callsigns=sorted(self.calls), connectedAt=self.connected_at, evicted=self.evicted,
                    spots=[dict(spot) for spot in self.cache.values() if spot['heardAt'] > cutoff
                           and spot['sender'] == sender and spot['band'] == entry.get('band')])

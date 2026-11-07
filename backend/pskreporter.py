"""One receive-only MQTT connection, bounded volatile cache, shared via SSE.

The network thread only appends to a bounded queue. All application state and
cache mutation happens on the server loop. Focus never causes a network query.
"""
import asyncio
from collections import Counter, deque
from copy import deepcopy
import threading
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


def inspect_spot(payload, calls, now):
    """Return a validated report or an explicit rejection reason plus safe fields."""
    preview = {}
    if not isinstance(payload, bytes): return None, 'invalid_payload', preview
    if len(payload) > 4096: return None, 'oversized', preview
    try:
        data = json.loads(payload)
        if not isinstance(data, dict): return None, 'malformed_json', preview
        # Public radio fields only: never retain arbitrary JSON or raw payloads.
        for key in ('sc', 'rc', 'rl', 'f', 'md', 'rp', 't', 't_tx'):
            value = data.get(key)
            if isinstance(value, str): preview[key] = ''.join(c for c in value if c.isprintable())[:64]
            elif type(value) in (int, float) and math.isfinite(value): preview[key] = value
        tx, rx = data.get('sc'), data.get('rc')
        if not isinstance(tx, str) or not isinstance(rx, str): return None, 'invalid_callsign', preview
        tx, rx = normalize_call(tx), normalize_call(rx)
        if not tx or not rx: return None, 'invalid_callsign', preview
        if tx not in calls: return None, 'wrong_sender', preview
        grid = data.get('rl')
        if not isinstance(grid, str): return None, 'invalid_grid', preview
        grid = grid.strip().upper()
        if not re.fullmatch(r'[A-R]{2}[0-9]{2}(?:[A-X]{2}(?:[0-9]{2}(?:[A-X]{2})?)?)?', grid): return None, 'invalid_grid', preview
        frequency, heard = data.get('f'), data.get('t_tx', data.get('t'))
        if type(frequency) not in (int, float) or not math.isfinite(frequency): return None, 'unsupported_frequency', preview
        band = band_from_hz(frequency)
        if not band: return None, 'unsupported_frequency', preview
        if type(heard) not in (int, float) or not math.isfinite(heard): return None, 'invalid_timestamp', preview
        if heard <= now - MAX_AGE: return None, 'too_old', preview
        if heard > now + 30: return None, 'future_timestamp', preview
        mode, snr = data.get('md'), data.get('rp')
        return dict(sender=tx, receiver=rx, grid=grid, band=band, heardAt=int(heard * 1000),
                    frequency=frequency, mode=mode[:16] if isinstance(mode, str) else '',
                    snr=snr if type(snr) in (int, float) and math.isfinite(snr) and -100 <= snr <= 100 else None), '', preview
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        return None, 'malformed_json', preview


def parse_spot(payload, calls, now):
    return inspect_spot(payload, calls, now)[0]


class MqttInbox(queue.Queue):
    """Bounded handoff with thread-safe wire counters, including dropped reports."""
    def __init__(self, clock):
        super().__init__(maxsize=512)
        self.clock = clock
        self.stats_lock = threading.Lock()
        self.stats = dict(received=0, bytes=0, oversized=0, queueDropped=0, controlDropped=0, lastMessageAt=None)

    def put_nowait(self, item):
        kind, value = item
        if kind == 'spot':
            value = dict(payload=value) if isinstance(value, bytes) else dict(value)
            payload = value['payload']
            value.setdefault('at', int(self.clock() * 1000))
            value['topic'] = str(value.get('topic', ''))[:240]
            with self.stats_lock:
                self.stats['received'] += 1; self.stats['bytes'] += len(payload)
                self.stats['lastMessageAt'] = value['at']
                if len(payload) > 4096:
                    self.stats['oversized'] += 1
                    return
            item = (kind, value)
        try: super().put_nowait(item)
        except queue.Full:
            with self.stats_lock: self.stats['queueDropped' if kind == 'spot' else 'controlDropped'] += 1
            raise

    def metrics(self):
        with self.stats_lock: return dict(self.stats)


def mqtt_client(inbox):
    import paho.mqtt.client as mqtt
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
    client.tls_set()
    client.connect_timeout = 8
    client.reconnect_delay_set(min_delay=2, max_delay=60)

    def offer(kind, value=None):
        try: inbox.put_nowait((kind, value))
        except queue.Full: pass  # Explicitly bounded best-effort feed.

    client.on_connect = lambda c, u, f, reason, p: offer('connected' if not reason.is_failure else 'error', str(reason)[:160])
    client.on_connect_fail = lambda c, u: offer('error', 'DNS, TCP or TLS connection failed; retrying automatically.')
    client.on_disconnect = lambda c, u, f, reason, p: offer('disconnected', str(reason)[:160])
    client.on_subscribe = lambda c, u, mid, reasons, p: offer('subscription_error' if any(r.is_failure for r in reasons) else 'subscribed', dict(mid=mid, reason=', '.join(map(str, reasons))[:160]))
    client.on_message = lambda c, u, message: offer('spot', dict(payload=message.payload, topic=message.topic))
    client.connect_async(BROKER, PORT, keepalive=60)
    client.loop_start()
    return client


class PskReporterService:
    def __init__(self, state, settings, *, client_factory=mqtt_client, clock=time.time):
        self.state, self.settings = state, settings
        self.client_factory, self.clock = client_factory, clock
        self.client = self.task = None
        self.inbox = MqttInbox(clock)
        self.cache = {}
        self.calls, self.subscribed = set(), set()
        self.status, self.error = 'disabled', ''
        self.connected_at = None
        self.evicted = 0
        self.subscribe_after = 0
        self.pending_subscriptions, self.acknowledged = {}, set()
        self.started_at = int(clock() * 1000)
        self.counts = Counter()
        self.rejections = Counter()
        self.events, self.reports = deque(maxlen=50), deque(maxlen=100)
        self.sequence = 0
        self.last_accepted_at = self.last_disconnected_at = None

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
        self.pending_subscriptions.clear(); self.acknowledged.clear()
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

    def event(self, kind, message):
        self.sequence += 1
        self.events.appendleft(dict(id=self.sequence, at=int(self.clock()*1000), kind=kind, message=message[:240]))

    def ingest(self, payload, *, topic='', at=None):
        spot, reason, preview = inspect_spot(payload, self.calls, self.clock())
        changed = False
        if spot:
            key = (spot['sender'], spot['band'], spot['receiver'])
            previous = self.cache.get(key)
            if previous and previous['heardAt'] >= spot['heardAt']:
                reason = 'duplicate_or_older'; self.counts['duplicates'] += 1
            else:
                self.cache[key] = spot
                self.counts['accepted'] += 1
                self.last_accepted_at = int(self.clock()*1000)
                changed = True
                if len(self.cache) > CACHE_LIMIT:
                    oldest = min(self.cache, key=lambda k: self.cache[k]['heardAt'])
                    del self.cache[oldest]; self.evicted += 1
        else:
            self.counts['rejected'] += 1; self.rejections[reason] += 1
        self.sequence += 1
        self.reports.appendleft(dict(id=self.sequence, at=at if at is not None else int(self.clock()*1000),
            outcome='accepted' if changed else 'duplicate' if spot else 'rejected', reason=reason,
            topic=topic[:240], size=len(payload), preview=preview, band=spot['band'] if spot else None))
        return changed

    def prune(self):
        cutoff = (self.clock() - MAX_AGE) * 1000
        expired = [key for key, spot in self.cache.items() if spot['heardAt'] <= cutoff or spot['sender'] not in self.calls]
        for key in expired: del self.cache[key]
        self.counts['expired'] += len(expired)
        return bool(expired)

    async def tick(self):
        calls = self.identities() if self.settings.enabled else set()
        changed = calls != self.calls
        self.calls = calls
        changed |= self.prune()
        if not self.calls:
            await self.stop_client()
            new_status = 'waiting' if self.settings.enabled else 'disabled'
            changed |= self.status != new_status
            if self.status != new_status: self.event(new_status, 'Reception overlay disabled.' if new_status == 'disabled' else 'Waiting for a WSJT-X station callsign or explicit override.')
            self.status, self.error = new_status, ''
        elif self.client is None:
            try:
                self.event('connecting', f'Connecting to {BROKER}:{PORT} using TLS.')
                self.client = self.client_factory(self.inbox)
                self.status, self.error = 'connecting', ''
            except (OSError, ValueError, ImportError) as exc:
                self.counts['connectionFailures'] += 1
                self.event('error', f'MQTT client could not start ({type(exc).__name__}).')
                self.status, self.error = 'error', 'MQTT could not start. Check the installation and internet connection.'
            changed = True
        for _ in range(512):
            try: kind, value = self.inbox.get_nowait()
            except queue.Empty: break
            if kind == 'spot':
                self.ingest(value['payload'], topic=value['topic'], at=value['at'])
                changed = True
            else:
                changed = True
                if kind == 'connected':
                    self.counts['connections'] += 1
                    self.event('connected', f'Broker connection accepted: {value or "Success"}.')
                    self.status, self.error = 'connected', ''
                    self.connected_at = int(self.clock() * 1000)
                    self.subscribed.clear()  # Clean session: resubscribe after every reconnect.
                    self.pending_subscriptions.clear(); self.acknowledged.clear()
                    self.subscribe_after = 0
                elif kind == 'subscription_error':
                    self.counts['subscriptionErrors'] += 1
                    self.event('subscription_error', f'Subscription refused: {(value or {}).get("reason", "No reason provided")}.')
                    self.pending_subscriptions.clear(); self.acknowledged.clear()
                    self.status, self.error = 'error', 'MQTT subscription refused; retrying in one minute.'
                    self.subscribed.clear()
                    self.subscribe_after = self.clock() + 60
                elif kind == 'subscribed':
                    self.counts['subscriptionAcks'] += 1
                    calls = self.pending_subscriptions.pop(value.get('mid'), set()) if isinstance(value, dict) else set()
                    self.acknowledged.update(calls)
                    self.event('subscribed', f'Broker acknowledged subscription: {", ".join(sorted(calls)) or "acknowledgement received"}.')
                    if self.clock() >= self.subscribe_after:
                        self.status, self.error = 'connected', ''
                elif kind == 'error':
                    self.counts['connectionFailures'] += 1
                    self.event('error', value if isinstance(value, str) else 'MQTT connection failed.')
                    self.status, self.error = 'error', 'MQTT connection or subscription failed; retrying automatically.'
                else:
                    self.counts['disconnects'] += 1
                    self.last_disconnected_at = int(self.clock()*1000)
                    self.event('disconnected', f'Broker disconnected: {value or "No reason provided"}.')
                    self.subscribed.clear(); self.pending_subscriptions.clear(); self.acknowledged.clear()
                    self.status, self.error = 'reconnecting', 'MQTT disconnected; retrying automatically. Recent reports remain until they expire.'
        if self.client and self.client.is_connected() and self.clock() >= self.subscribe_after:
            for call in self.subscribed - self.calls:
                self.client.unsubscribe(topic_for(call))
                self.acknowledged.discard(call)
                for pending in self.pending_subscriptions.values(): pending.discard(call)
                self.event('unsubscribe', f'Stopped monitoring {call}.')
                changed = True
            self.subscribed.intersection_update(self.calls)
            for call in self.calls - self.subscribed:
                result, _mid = self.client.subscribe(topic_for(call), qos=0)
                self.counts['subscriptionRequests'] += 1
                if result == 0:
                    self.subscribed.add(call)
                    self.pending_subscriptions.setdefault(_mid, set()).add(call)
                    self.event('subscribe', f'Subscription requested: {topic_for(call)}')
                    changed = True
                else:
                    self.counts['subscriptionErrors'] += 1
                    self.event('subscription_error', f'Subscription send failed (code {result}).')
                    self.status, self.error = 'error', 'MQTT subscription could not be sent; retrying in one minute.'
                    self.subscribe_after = self.clock() + 60
                    changed = True
                    break
        if changed: self.state.flush()

    async def run(self):
        while True:
            await asyncio.sleep(2)
            await self.tick()

    def clear_diagnostics(self):
        self.events.clear(); self.reports.clear()

    def diagnostics(self):
        now = self.clock()
        snapshot = self.snapshot()
        entry = next((e for e in self.state.history if e['call'] == self.state.call), {})
        rig = self.state.rigs.get(entry.get('rigId'), {})
        raw = self.settings.callsign or entry.get('stationCall') or rig.get('stationCall', '')
        sender = normalize_call(raw) if isinstance(raw, str) else None
        cached = [s for s in self.cache.values() if s['heardAt'] > (now-MAX_AGE)*1000 and s['sender'] in self.calls]
        visible = [s for s in snapshot['spots'] if s['heardAt'] > (now-self.settings.window_minutes*60)*1000]
        counts = {key:self.counts[key] for key in ('accepted','rejected','duplicates','expired','connections',
                  'connectionFailures','disconnects','subscriptionRequests','subscriptionAcks','subscriptionErrors')}
        counts.update(self.inbox.metrics(), cached=len(cached), focusBand=len(snapshot['spots']),
                      matchingWindow=len(visible), evicted=self.evicted, queued=self.inbox.qsize())
        bands = Counter((s['sender'],s['band']) for s in cached)
        status, message = self.status, ''
        worker_failed = self.task is not None and self.task.done() and not self.task.cancelled() and self.task.exception() is not None
        if worker_failed:
            status, message = 'error', 'The MQTT processing worker stopped. Restart Dashboard after checking the server log.'
        elif not self.settings.enabled: message = 'PSKReporter is disabled. Enable it in Settings → PSKReporter and save to start collecting reports.'
        elif not self.calls: message = 'Waiting for a WSJT-X station callsign. Receive Status from a radio or set the transmitting callsign override.'
        elif status != 'connected': message = self.error or 'Waiting for the MQTT broker connection.'
        elif not self.acknowledged: message = 'Connected to the broker; waiting for subscription acknowledgement. A connection alone does not confirm report delivery.'
        elif not counts['received']: message = 'Subscribed successfully; no reports have arrived yet. Reports are collected only while Dashboard runs, with no historical backfill.'
        elif not self.state.call or not entry.get('band'): message = 'Reports are arriving, but the focus has no known band. Select a station in WSJT-X.'
        elif sender not in self.calls: message = 'The focus transmitting identity is not currently monitored. Check its radio identity or the callsign override in Settings.'
        elif not visible and snapshot['spots']: message = 'Reports exist on the focus band, but are older than the saved map window. Try a longer window on the Station map.'
        elif not visible and cached: message = 'Reports are cached, but none match the focus transmitting callsign and band. Check the cached bands below.'
        elif not visible: message = 'Messages arrived, but no usable reports match the map. Check rejected reports and reasons below.'
        else: message = f'{len(visible)} receivers match the focus callsign/band and saved map window. Zoom out or center the Station map if needed.'
        reasons = dict(self.rejections)
        if counts['oversized']: reasons['oversized'] = counts['oversized']
        return dict(status=status, error=self.error, explanation=message, startedAt=self.started_at,
                    generatedAt=int(now*1000), broker=BROKER, port=PORT, tls=True, workerRunning=bool(self.task and not self.task.done()),
                    connectedAt=self.connected_at, lastDisconnectedAt=self.last_disconnected_at,
                    lastAcceptedAt=self.last_accepted_at, config=self.settings.public(), counts=counts, rejectionReasons=reasons,
                    focus=dict(call=self.state.call, sender=sender or '', band=entry.get('band'), windowMinutes=self.settings.window_minutes,
                               focusHeard=any(s['receiver']==self.state.call for s in visible)),
                    subscriptions=[dict(callsign=call,topic=topic_for(call),status='acknowledged' if call in self.acknowledged
                        else 'pending' if call in self.subscribed else 'waiting') for call in sorted(self.calls)],
                    bands=[dict(sender=sender,band=band,count=count) for (sender,band),count in sorted(bands.items())],
                    limits=dict(events=50,reports=100,queue=512,cache=CACHE_LIMIT),
                    events=deepcopy(list(self.events)), reports=deepcopy(list(self.reports)))

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

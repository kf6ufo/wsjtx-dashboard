"""Single-event-loop owned state. History records radio selections only."""
import asyncio
from copy import deepcopy
import re
import time
import uuid
from .protocol import Packet, band_from_hz


def normalize_call(raw: str) -> str | None:
    if not raw.isascii():
        return None
    call = raw.strip().upper()
    if re.fullmatch(r'(?=.*[A-Z])(?=.*\d)[A-Z0-9]+(?:/[A-Z0-9]+)*', call, flags=re.ASCII) and 3 <= len(call) <= 15:
        return call
    return None


class FocusState:
    def __init__(self, *, history_limit=200, rig_limit=32):
        self.history_limit, self.rig_limit = history_limit, rig_limit
        self.epoch = uuid.uuid4().hex
        self.revision = 0
        self.call = ''
        self.source = 'radio'
        self.history = []
        self.rigs = {}
        self.previous = {}
        self.counters = dict(packets=0, malformed=0, decodes=0, ignored=0, capacity=0)
        self.receiver = dict(status='disabled', group=None, port=None, interface=None, error=None)
        self.subscribers: set[asyncio.Queue] = set()
        self.selection_sequence = 0

    def snapshot(self):
        return deepcopy(dict(epoch=self.epoch, revision=self.revision, call=self.call,
                             source=self.source, history=self.history, rigs=list(self.rigs.values()),
                             counters=self.counters, receiver=self.receiver))

    def publish(self):
        self.revision += 1
        for queue in self.subscribers:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(self.snapshot())

    def subscribe(self):
        if len(self.subscribers) >= 32:
            raise ValueError('Browser stream capacity reached')
        queue = asyncio.Queue(maxsize=1)
        self.subscribers.add(queue)
        queue.put_nowait(self.snapshot())  # Atomic subscribe + full initial snapshot.
        return queue

    def unsubscribe(self, queue):
        self.subscribers.discard(queue)

    def accept(self, packet: Packet, *, at: int | None = None):
        self.counters['packets'] += 1
        now = at if at is not None else int(time.time() * 1000)
        if packet.kind == 2:
            self.counters['decodes'] += 1
        elif packet.kind == 6:
            self.previous.pop(packet.rig_id, None)
            if packet.rig_id in self.rigs:
                self.rigs[packet.rig_id]['online'] = False
        elif packet.kind == 1:
            call = normalize_call(packet.dx_call)
            # A blank is an intentional clear; invalid nonblank input is ignored.
            if packet.dx_call.strip() and call is None:
                self.counters['ignored'] += 1
                if packet.rig_id in self.previous:
                    self.publish()
                    return
                # The first parsed Status still establishes a baseline even
                # when its DX field is invalid; it cannot select a station.
            if packet.rig_id not in self.rigs and len(self.rigs) >= self.rig_limit:
                self.counters['capacity'] += 1
                self.publish()
                return
            baseline = packet.rig_id not in self.previous
            previous = self.previous.get(packet.rig_id)
            self.previous[packet.rig_id] = call
            band = band_from_hz(packet.frequency)
            self.rigs[packet.rig_id] = dict(self.rigs.get(packet.rig_id, {}), id=packet.rig_id, name=packet.rig_id.removeprefix('WSJT-X - '),
                                          band=band, mode=packet.mode, frequency=packet.frequency,
                                          call=call or '', lastSeen=now, online=True, color='#70c9bd')
            if not baseline and call and call != previous:
                self.selection_sequence += 1
                entry = dict(call=call, rigId=packet.rig_id, selectedAt=now, band=band,
                             mode=packet.mode, frequency=packet.frequency, recency=self.selection_sequence)
                self.history = [entry] + [e for e in self.history if e['call'] != call]
                del self.history[self.history_limit:]
                self.call, self.source = call, 'radio'
        else:
            self.counters['ignored'] += 1
        self.publish()

    def browse(self, call: str) -> bool:
        entry = next((e for e in self.history if e['call'] == call), None)
        if entry is None:
            return False
        entry['browsedAt'] = int(time.time() * 1000)
        self.call, self.source = call, 'browse'
        self.publish()
        return True

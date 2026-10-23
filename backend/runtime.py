"""One receive-only socket owner; settings changes restart only this receiver."""
import asyncio
from contextlib import suppress
from .receiver import create_socket, receive


class ReceiverRuntime:
    def __init__(self, state):
        self.state = state
        self.sock = self.task = self.health_task = None
        self.lock = asyncio.Lock()

    async def stop(self):
        for task in (self.task, self.health_task):
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        if self.sock:
            self.sock.close()
        self.sock = self.task = self.health_task = None

    async def apply(self, settings):
        self.settings = settings
        await self.stop()
        self.state.previous.clear()
        for rig in self.state.rigs.values():
            rig['online'] = False
        if settings.enabled:
            self.state.enter_radio_workspace()
        self.state.configure_receiver(settings)
        self.state.receiver.update(status='disabled', error=None)
        if settings.enabled:
            try:
                self.sock = create_socket(settings)
                self.state.receiver['status'] = 'listening'
                self.task = asyncio.create_task(receive(self.sock, self.state))
                self.health_task = asyncio.create_task(self.health())
            except OSError as exc:
                self.state.counters['receiverErrors'] += 1
                self.state.receiver.update(status='error', error=f'Cannot start receiver: {exc}. Check listen address, port and receiving interface.')
        self.state.publish()
        self.state.flush()

    async def health(self):
        while True:
            await asyncio.sleep(5)
            self.state.expire_instances()

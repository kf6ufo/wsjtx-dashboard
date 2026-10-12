"""Receive-only primary multicast socket. Never sends or acknowledges packets."""
import asyncio
from dataclasses import dataclass
import ipaddress
import os
import socket
from .protocol import PacketError, parse_packet
from .state import FocusState


@dataclass(frozen=True)
class Settings:
    enabled: bool = False
    group: str = '239.255.0.73'
    port: int = 2238
    interface: str | None = None

    def __post_init__(self):
        if not ipaddress.IPv4Address(self.group).is_multicast:
            raise ValueError('WSJTX_GROUP must be an IPv4 multicast address')
        if not 1 <= self.port <= 65535:
            raise ValueError('WSJTX_PORT must be 1..65535')
        if self.enabled and (not self.interface or self.interface == '0.0.0.0'):
            raise ValueError('Set WSJTX_INTERFACE to the receiving host IPv4 address explicitly')
        if self.interface:
            ipaddress.IPv4Address(self.interface)

    @classmethod
    def from_env(cls):
        enabled = os.getenv('WSJTX_RECEIVER', 'off')
        if enabled not in ('on', 'off'):
            raise ValueError('WSJTX_RECEIVER must be on or off')
        return cls(enabled=enabled == 'on', group=os.getenv('WSJTX_GROUP', '239.255.0.73'),
                   port=int(os.getenv('WSJTX_PORT', '2238')), interface=os.getenv('WSJTX_INTERFACE'))


def create_socket(settings: Settings):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', settings.port))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                        socket.inet_aton(settings.group) + socket.inet_aton(settings.interface))
        # Linux: receive only groups joined by this socket, not other sockets.
        if hasattr(socket, 'IP_MULTICAST_ALL'):
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_ALL, 0)
        sock.setblocking(False)
        return sock
    except BaseException:
        sock.close()
        raise


def ingest(data: bytes, state: FocusState):
    try:
        packet = parse_packet(data)
    except PacketError:
        state.counters['malformed'] += 1
        state.publish()
    else:
        state.accept(packet)


async def receive(sock, state: FocusState):
    loop = asyncio.get_running_loop()
    try:
        while True:
            data, _sender = await loop.sock_recvfrom(sock, 65535)
            ingest(data, state)
    except OSError:
        state.receiver.update(status='error', error='UDP receive failed; restart after checking the interface.')
        state.publish()

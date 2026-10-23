"""Receive-only primary multicast socket. Never sends or acknowledges packets."""
import asyncio
from dataclasses import dataclass
import ipaddress
import socket
from .protocol import PacketError, parse_packet
from .state import FocusState


@dataclass(frozen=True)
class Settings:
    enabled: bool = False
    group: str = '239.255.0.73'
    port: int = 2238
    interface: str | None = None
    listen: str = '0.0.0.0'
    retention: int = 200

    def __post_init__(self):
        if not isinstance(self.group, str) or not isinstance(self.listen, str) or (self.interface is not None and not isinstance(self.interface, str)):
            raise ValueError('Receiver addresses must be IPv4 strings')
        if type(self.enabled) is not bool:
            raise ValueError('Receiver enabled must be true or false')
        if self.group and not ipaddress.IPv4Address(self.group).is_multicast:
            raise ValueError('Multicast group must be empty (unicast) or an IPv4 multicast address')
        if type(self.port) is not int or not 1024 <= self.port <= 65535:
            raise ValueError('Receiver port must be 1024..65535')
        if type(self.retention) is not int or not 50 <= self.retention <= 500:
            raise ValueError('Diagnostic retention must be 50..500 packets')
        listen = ipaddress.IPv4Address(self.listen)
        if listen.is_multicast or listen.is_reserved or listen.is_global:
            raise ValueError('Listen address must be wildcard, loopback or a local private IPv4 address')
        if self.interface:
            interface = ipaddress.IPv4Address(self.interface)
            if interface.is_unspecified or interface.is_multicast:
                raise ValueError('Interface must be a specific receiving host IPv4 address')
        if self.enabled and self.group and not self.interface:
            raise ValueError('Set the receiving host interface IPv4 address explicitly for multicast')



def create_socket(settings: Settings):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('' if settings.listen == '0.0.0.0' else settings.listen, settings.port))
        if settings.group:
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


def ingest(data: bytes, state: FocusState, source=('127.0.0.1', 0)):
    try:
        packet = parse_packet(data)
    except PacketError as exc:
        if hasattr(state, 'record_datagram'):
            state.record_datagram(data, source, error=str(exc))
            state.counters['packets'] += 1
        state.counters['malformed'] += 1
        state.publish()
    else:
        if hasattr(state, 'record_datagram'):
            state.record_datagram(data, source, packet=packet)
        state.accept(packet)


async def receive(sock, state: FocusState):
    loop = asyncio.get_running_loop()
    try:
        while True:
            data, sender = await loop.sock_recvfrom(sock, 65535)
            ingest(data, state, sender)
    except OSError:
        state.counters['receiverErrors'] = state.counters.get('receiverErrors', 0) + 1
        state.receiver.update(status='error', error='UDP receive failed; restart after checking the interface.')
        state.publish()

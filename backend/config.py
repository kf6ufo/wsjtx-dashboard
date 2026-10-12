"""Single TOML configuration for the installed server; no shell evaluation."""
from dataclasses import dataclass
import ipaddress
from pathlib import Path
import tomllib
from .receiver import Settings


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    receiver: Settings


def load_config(path: Path) -> ServerConfig:
    try:
        with path.open('rb') as source:
            data = tomllib.load(source)
        if set(data) != {'http', 'wsjtx'}:
            raise ValueError('Expected only [http] and [wsjtx] sections')
        http, radio = data['http'], data['wsjtx']
        if set(http) != {'host', 'port'} or set(radio) != {'enabled', 'group', 'port', 'interface'}:
            raise ValueError('Use the keys shown in config.example.toml')
        for name, value in (('http.port', http['port']), ('wsjtx.port', radio['port'])):
            if type(value) is not int or not 1024 <= value <= 65535:
                raise ValueError(f'{name} must be an unprivileged port (1024..65535)')
        if type(radio['enabled']) is not bool:
            raise ValueError('wsjtx.enabled must be true or false')
        for name, value in (('http.host', http['host']), ('wsjtx.group', radio['group']), ('wsjtx.interface', radio['interface'])):
            if not isinstance(value, str):
                raise ValueError(f'{name} must be an IPv4 address string')
            ipaddress.IPv4Address(value)
        address = ipaddress.IPv4Address(http['host'])
        private_networks = ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8')
        if not any(address in ipaddress.IPv4Network(network) for network in private_networks):
            raise ValueError('http.host must be a specific private LAN or loopback IPv4 address')
        receiver = Settings(enabled=radio['enabled'], group=radio['group'], port=radio['port'], interface=radio['interface'])
        return ServerConfig(http['host'], http['port'], receiver)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ValueError(f'Configuration error in {path}: {exc}') from exc

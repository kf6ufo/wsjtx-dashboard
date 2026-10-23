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
        if set(http) != {'host', 'port'} or not {'enabled', 'group', 'port', 'interface'} <= set(radio) or set(radio) - {'enabled', 'group', 'port', 'interface', 'listen', 'retention'}:
            raise ValueError('Use the keys shown in config.example.toml')
        for name, value in (('http.port', http['port']), ('wsjtx.port', radio['port'])):
            if type(value) is not int or not 1024 <= value <= 65535:
                raise ValueError(f'{name} must be an unprivileged port (1024..65535)')
        if type(radio['enabled']) is not bool:
            raise ValueError('wsjtx.enabled must be true or false')
        for name, value in (('http.host', http['host']),):
            if not isinstance(value, str):
                raise ValueError(f'{name} must be an IPv4 address string')
            ipaddress.IPv4Address(value)
        address = ipaddress.IPv4Address(http['host'])
        private_networks = ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8')
        if not any(address in ipaddress.IPv4Network(network) for network in private_networks):
            raise ValueError('http.host must be a specific private LAN or loopback IPv4 address')
        receiver = Settings(**radio)
        return ServerConfig(http['host'], http['port'], receiver)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ValueError(f'Configuration error in {path}: {exc}') from exc


def save_receiver_config(path: Path, settings: Settings):
    """Replace only the receiver keys atomically; retain operator comments/HTTP settings."""
    from dataclasses import asdict, replace
    import json
    import os
    import re
    import tempfile
    settings = replace(settings, interface=settings.interface or '')
    original = path.read_text()
    load_config(path)
    values = asdict(settings)
    values['interface'] = values['interface'] or ''
    seen, lines, inside = set(), [], False

    def missing():
        for key, value in values.items():
            if key not in seen:
                lines.append(f'{key} = {json.dumps(value)}\n')
                seen.add(key)

    for line in original.splitlines(keepends=True):
        section = re.match(r'\s*\[([^]]+)\]\s*(?:#.*)?$', line.rstrip())
        if section:
            if inside:
                missing()
            inside = section[1] == 'wsjtx'
        match = re.match(r'\s*(\w+)\s*=', line) if inside else None
        if match and match[1] in values:
            key = match[1]
            comment = ('  #' + line.split('#', 1)[1].rstrip()) if '#' in line else ''
            lines.append(f'{key} = {json.dumps(values[key])}{comment}\n')
            seen.add(key)
        else:
            lines.append(line if line.endswith('\n') else line + '\n')
    if inside:
        missing()
    pending = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=path.parent, prefix='.receiver-', suffix='.toml', delete=False) as target:
            pending = Path(target.name)
            target.write(''.join(lines))
            target.flush()
            os.fsync(target.fileno())
        if load_config(pending).receiver != settings:
            raise ValueError('Receiver configuration could not be written consistently')
        if path.read_text() != original:
            raise ValueError('Configuration changed on disk; reload settings and try again')
        os.replace(pending, path)
    finally:
        if pending and pending.exists():
            pending.unlink()

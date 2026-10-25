"""Single TOML configuration for the installed server; no shell evaluation."""
from dataclasses import dataclass, field
import ipaddress
from pathlib import Path
import tomllib
from .receiver import Settings
from .enrichment_config import EnrichmentSettings
from .wavelog_config import WavelogSettings
from .qso_config import QsoSettings
from .history_config import HistorySettings
from .forwarding_config import ForwardingSettings


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    receiver: Settings
    enrichment: EnrichmentSettings = field(default_factory=EnrichmentSettings)
    wavelog: WavelogSettings = field(default_factory=WavelogSettings)
    qso: QsoSettings = field(default_factory=QsoSettings)
    history: HistorySettings = field(default_factory=HistorySettings)
    forwarding: ForwardingSettings = field(default_factory=ForwardingSettings)


def load_config(path: Path) -> ServerConfig:
    try:
        with path.open('rb') as source:
            data = tomllib.load(source)
        if not {'http', 'wsjtx'} <= set(data) or set(data) - {'http', 'wsjtx', 'enrichment', 'wavelog', 'qso', 'history', 'forwarding'}:
            raise ValueError('Expected [http], [wsjtx], optional [enrichment] and [wavelog] sections')
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
        return ServerConfig(http['host'], http['port'], receiver, EnrichmentSettings(**data.get('enrichment', {})), WavelogSettings(**data.get('wavelog', {})), QsoSettings(**data.get('qso', {})), HistorySettings(**data.get('history', {})), ForwardingSettings(**data.get('forwarding', {})))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ValueError(f'Configuration error in {path}: {exc}') from exc


def save_receiver_config(path: Path, settings: Settings):
    from dataclasses import asdict, replace
    settings = replace(settings, interface=settings.interface or '')
    _save_section(path, 'wsjtx', asdict(settings))
    if load_config(path).receiver != settings:
        raise ValueError('Receiver configuration could not be written consistently')


def save_enrichment_config(path: Path, settings: EnrichmentSettings):
    from dataclasses import asdict
    _save_section(path, 'enrichment', asdict(settings))


def save_wavelog_config(path: Path, settings: WavelogSettings):
    from dataclasses import asdict
    _save_section(path, 'wavelog', asdict(settings))


def save_qso_config(path: Path, settings: QsoSettings):
    from dataclasses import asdict
    _save_section(path, 'qso', asdict(settings))


def save_history_config(path: Path, settings: HistorySettings):
    from dataclasses import asdict
    _save_section(path, 'history', asdict(settings))


def save_forwarding_config(path: Path, settings: ForwardingSettings):
    from dataclasses import asdict
    _save_section(path, 'forwarding', asdict(settings))


def _save_section(path: Path, section_name: str, values: dict):
    """Atomic section update, preserving other settings and inline comments."""
    import json
    import os
    import re
    import tempfile
    original = path.read_text()
    load_config(path)
    seen, lines, inside, found = set(), [], False, False

    def comment_in(line):
        quote, escape = '', False
        for index, char in enumerate(line):
            if escape:
                escape = False
            elif char == '\\' and quote == '"':
                escape = True
            elif quote:
                if char == quote:
                    quote = ''
            elif char in ('"', "'"):
                quote = char
            elif char == '#':
                return '  ' + line[index:].rstrip()
        return ''

    def toml(value):
        if isinstance(value, dict): return '{' + ', '.join(json.dumps(k) + ' = ' + toml(v) for k,v in value.items()) + '}'
        if isinstance(value, list): return '[' + ', '.join(map(toml, value)) + ']'
        return json.dumps(value)

    def missing():
        for key, value in values.items():
            if key not in seen:
                lines.append(f'{key} = {toml(value)}\n')
                seen.add(key)

    for line in original.splitlines(keepends=True):
        section = re.match(r'\s*\[([^]]+)\]\s*(?:#.*)?$', line.rstrip())
        if section:
            if inside:
                missing()
            inside = section[1] == section_name
            found = found or inside
        match = re.match(r'\s*(\w+)\s*=', line) if inside else None
        if match and match[1] in values:
            key = match[1]
            comment = comment_in(line)
            lines.append(f'{key} = {toml(values[key])}{comment}\n')
            seen.add(key)
        else:
            lines.append(line if line.endswith('\n') else line + '\n')
    if inside:
        missing()
    if not found:
        lines.append(f'\n[{section_name}]\n')
        missing()
    pending = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=path.parent, prefix='.receiver-', suffix='.toml', delete=False) as target:
            pending = Path(target.name)
            target.write(''.join(lines))
            target.flush()
            os.fsync(target.fileno())
        parsed = load_config(pending)
        from dataclasses import asdict
        actual = asdict(getattr(parsed, 'receiver' if section_name == 'wsjtx' else section_name))
        if actual != values:
            raise ValueError('Configuration could not be written consistently')
        if path.read_text() != original:
            raise ValueError('Configuration changed on disk; reload settings and try again')
        os.replace(pending, path)
    finally:
        if pending and pending.exists():
            pending.unlink()

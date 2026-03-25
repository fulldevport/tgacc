from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class Px:
    proxy_type: Any = "socks5"
    host: str = "127.0.0.1"
    port: int = 9050
    rdns: bool = True
    username: Optional[str] = None
    password: Optional[str] = None

    def to_telethon_proxy(self) -> tuple[Any, str, int, bool, Optional[str], Optional[str]]:
        return (self.proxy_type, self.host, int(self.port), bool(self.rdns), self.username, self.password)


@dataclass(slots=True)
class Acc:
    account_id: str
    session_name: str
    api_id: int = 2040
    api_hash: str = "b18441a1ff607e10a989891a5462e627"
    params_patch: dict[str, str] = field(default_factory=dict)
    use_proxy: bool = False
    proxy: Optional[Px] = None
    telethon_kwargs: dict[str, Any] = field(default_factory=dict)

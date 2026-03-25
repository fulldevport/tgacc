from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.account import UpdateStatusRequest

from .exceptions import JsonErr, OTErr
from .models import Acc, Px

PATCH_KEYS: tuple[str, ...] = (
    "device_model",
    "system_version",
    "app_version",
    "lang_code",
    "system_lang_code",
    "lang_pack",
)


class Hub:
    def __init__(self, sessions_dir: str | Path = "sessions") -> None:
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._accounts: dict[str, Acc] = {}
        self._clients: dict[str, TelegramClient] = {}

    def _json_path(self, account_id: str) -> Path:
        return self.sessions_dir / f"{account_id}.json"

    def _session_path(self, account_id: str) -> Path:
        return self.sessions_dir / f"{account_id}.session"

    @staticmethod
    def _normalize_patch(raw_patch: Mapping[str, Any]) -> dict[str, str]:
        out: dict[str, str] = {}
        for k in PATCH_KEYS:
            v = raw_patch.get(k, "")
            out[k] = "" if v is None else str(v)
        return out

    def _opentele_patch(self) -> dict[str, str]:
        try:
            from opentele.api import API

            api_data = API.TelegramDesktop.Generate()
            return self._normalize_patch(
                {
                    "device_model": getattr(api_data, "device_model", None),
                    "system_version": getattr(api_data, "system_version", None),
                    "app_version": getattr(api_data, "app_version", None),
                    "lang_code": getattr(api_data, "lang_code", None),
                    "system_lang_code": getattr(api_data, "system_lang_code", None),
                    "lang_pack": getattr(api_data, "lang_pack", None),
                }
            )
        except Exception as exc:
            raise OTErr("OpenTele patch generation failed") from exc

    def _proxy_from_dict(self, data: Mapping[str, Any] | None) -> Px | None:
        if not data:
            return None
        return Px(
            proxy_type=data.get("proxy_type", "socks5"),
            host=str(data.get("host", "127.0.0.1")),
            port=int(data.get("port", 9050)),
            rdns=bool(data.get("rdns", True)),
            username=data.get("username"),
            password=data.get("password"),
        )

    def _proxy_to_dict(self, proxy: Px | None) -> dict[str, Any] | None:
        if proxy is None:
            return None
        return {
            "proxy_type": proxy.proxy_type,
            "host": proxy.host,
            "port": proxy.port,
            "rdns": proxy.rdns,
            "username": proxy.username,
            "password": proxy.password,
        }

    def account_to_dict(self, account: Acc) -> dict[str, Any]:
        return {
            "account_id": account.account_id,
            "session_name": account.session_name,
            "api_id": int(account.api_id),
            "api_hash": str(account.api_hash),
            "params_patch": self._normalize_patch(account.params_patch),
            "use_proxy": bool(account.use_proxy),
            "proxy": self._proxy_to_dict(account.proxy),
            "telethon_kwargs": dict(account.telethon_kwargs),
        }

    def account_from_dict(self, data: Mapping[str, Any], fallback_id: str | None = None) -> Acc:
        account_id = str(data.get("account_id") or fallback_id or "").strip()
        if not account_id:
            raise JsonErr("account_id is empty")

        raw_patch = data.get("params_patch")
        if not isinstance(raw_patch, Mapping):
            raise JsonErr("params_patch is missing or invalid")

        return Acc(
            account_id=account_id,
            session_name=str(data.get("session_name") or f"{account_id}.session"),
            api_id=int(data.get("api_id", 2040)),
            api_hash=str(data.get("api_hash", "b18441a1ff607e10a989891a5462e627")),
            params_patch=self._normalize_patch(raw_patch),
            use_proxy=bool(data.get("use_proxy", False)),
            proxy=self._proxy_from_dict(data.get("proxy")) if isinstance(data.get("proxy"), Mapping) else None,
            telethon_kwargs=dict(data.get("telethon_kwargs") or {})
            if isinstance(data.get("telethon_kwargs") or {}, Mapping)
            else {},
        )

    def save_json(self, account: Acc) -> Path:
        path = self._json_path(account.account_id)
        path.write_text(json.dumps(self.account_to_dict(account), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_json(self, account_id: str) -> Acc:
        path = self._json_path(account_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise JsonErr("invalid json structure")
        account = self.account_from_dict(data, fallback_id=account_id)
        self._accounts[account.account_id] = account
        return account

    def ensure_json(self, account_id: str) -> Acc:
        path = self._json_path(account_id)
        if path.exists():
            try:
                return self.load_json(account_id)
            except (JsonErr, json.JSONDecodeError, OSError, ValueError, TypeError):
                pass

        account = Acc(
            account_id=account_id,
            session_name=f"{account_id}.session",
            params_patch=self._opentele_patch(),
        )
        self._accounts[account_id] = account
        self.save_json(account)
        return account

    def discover_account_ids(self) -> list[str]:
        ids: set[str] = set()
        for p in self.sessions_dir.glob("*.json"):
            ids.add(p.stem)
        for p in self.sessions_dir.glob("*.session"):
            ids.add(p.stem)
        return sorted(ids)

    def get_account(self, account_id: str) -> Acc:
        return self._accounts.get(account_id) or self.ensure_json(account_id)

    def _proxy_kwargs(self, account: Acc) -> dict[str, Any]:
        if not account.use_proxy:
            return {}
        if account.proxy is None:
            raise JsonErr("use_proxy=true but proxy is missing")
        return {"proxy": account.proxy.to_telethon_proxy()}

    def create_client(self, account_id: str, **kwargs: Any) -> TelegramClient:
        account = self.get_account(account_id)
        final_kwargs = dict(account.telethon_kwargs)
        final_kwargs.update(dict(account.params_patch))
        final_kwargs.update(kwargs)
        final_kwargs.update(self._proxy_kwargs(account))

        ctor_params = set(inspect.signature(TelegramClient.__init__).parameters.keys())
        lang_pack_value = final_kwargs.pop("lang_pack", None) if "lang_pack" not in ctor_params else None

        client = TelegramClient(
            session=str(self.sessions_dir / account.session_name),
            api_id=int(account.api_id),
            api_hash=str(account.api_hash),
            **final_kwargs,
        )

        if lang_pack_value is not None:
            init_request = getattr(client, "_init_request", None)
            if init_request is not None and hasattr(init_request, "lang_pack"):
                setattr(init_request, "lang_pack", lang_pack_value)

        return client

    async def connect(self, account_id: str, **kwargs: Any) -> TelegramClient:
        client = self.create_client(account_id, **kwargs)
        await client.connect()
        self._clients[account_id] = client
        return client

    async def disconnect(self, account_id: str) -> None:
        client = self._clients.pop(account_id, None)
        if client is not None and client.is_connected():
            await client.disconnect()

    async def disconnect_all(self) -> None:
        for account_id in list(self._clients.keys()):
            await self.disconnect(account_id)

    async def ensure_authorized(
        self,
        account_id: str,
        phone: str,
        code_callback: Callable[[], str],
        password_callback: Callable[[], str] | None = None,
    ) -> TelegramClient:
        client = await self.connect(account_id)
        if await client.is_user_authorized():
            return client

        sent = await client.send_code_request(phone)
        code = code_callback().strip()
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
        except SessionPasswordNeededError:
            if password_callback is None:
                raise
            await client.sign_in(password=password_callback().strip())
        return client

    async def set_online(self, account_id: str, online: bool = True) -> None:
        client = self._clients.get(account_id) or await self.connect(account_id)
        await client(UpdateStatusRequest(offline=not online))

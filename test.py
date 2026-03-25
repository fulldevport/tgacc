from __future__ import annotations

import asyncio
import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from tgacc import Hub


async def main() -> None:
    parser = argparse.ArgumentParser(prog="test.py")
    parser.add_argument("account_id", nargs="?", default="demo_account")
    parser.add_argument("--sessions", default="sessions")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    base_dir = Path("sessions")
    base_dir = Path(args.sessions)
    base_dir.mkdir(parents=True, exist_ok=True)

    account_id = str(args.account_id)
    session_path = base_dir / f"{account_id}.session"
    json_path = base_dir / f"{account_id}.json"

    hub = Hub(sessions_dir=base_dir)
    account = hub.ensure_json(account_id)

    print(f"account={account.account_id} session={account.session_name}")
    print(f"paths session={session_path} json={json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    patch = data.get("params_patch") or {}
    patch_ok = isinstance(patch, dict) and all(k in patch for k in ("device_model", "system_version", "app_version"))
    print(f"json_ok={bool(json_path.exists())} patch_ok={patch_ok}")

    client = await hub.connect(account_id)
    try:
        if not await client.is_user_authorized():
            phone = input("phone (+1234567890): ").strip()
            if not phone:
                raise ValueError("Phone number is required for first login")
            await hub.ensure_authorized(
                account_id=account_id,
                phone=phone,
                code_callback=lambda: input("code: "),
                password_callback=lambda: input("2fa (if enabled): "),
            )
            client = hub._clients[account_id]

        await hub.set_online(account_id, online=True)

        me = await client.get_me()
        if me is not None:
            print(f"me id={me.id} username={me.username!r}")

        count = 0
        async for dialog in client.iter_dialogs(limit=max(0, int(args.limit))):
            count += 1
            entity = dialog.entity
            username = getattr(entity, "username", None)
            print(f"chat id={dialog.id} title={dialog.name!r} username={username!r}")
        print(f"chats={count}")
    finally:
        await hub.disconnect_all()


if __name__ == "__main__":
    asyncio.run(main())

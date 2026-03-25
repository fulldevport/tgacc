# tgacc

Lightweight Telegram multi-account library with JSON-first configuration and OpenTele bootstrap.

---

## English

### What it does

`tgacc` manages many Telegram accounts from the `sessions/` folder in your project:

- `<account_id>.session` - Telethon session file
- `<account_id>.json` - account settings used for connection

Rules:

- valid JSON is reused
- missing JSON is generated from OpenTele
- broken JSON is regenerated
- connection parameters are always taken from JSON

### Installation

```bash
pip install -e .
```

Or:

```bash
pip install telethon opentele
```

### Quick start

```python
import asyncio
from tgacc import Hub


async def main() -> None:
    hub = Hub("sessions")
    hub.ensure_json("my_account")
    client = await hub.connect("my_account")
    me = await client.get_me()
    print(me.id if me else None, me.username if me else None)
    await hub.disconnect_all()


asyncio.run(main())
```

### Main API

- `Hub`
  - `ensure_json(account_id)`
  - `load_json(account_id)`
  - `save_json(account)`
  - `discover_account_ids()`
  - `connect(account_id, **kwargs)`
  - `ensure_authorized(account_id, phone, code_callback, password_callback=None)`
  - `set_online(account_id, online=True)`
  - `disconnect(account_id)`
  - `disconnect_all()`
- `Acc`
- `Px`

### Exceptions

- `TgErr`
- `OTErr`
- `JsonErr`

### Manual check

```bash
python test.py my_account --limit 20
```

---

## Русский

### Что делает библиотека

`tgacc` управляет несколькими Telegram-аккаунтами через папку `sessions/` в вашем проекте:

- `<account_id>.session` - файл сессии Telethon
- `<account_id>.json` - настройки подключения аккаунта

Правила:

- если JSON валиден, он используется как есть
- если JSON отсутствует, он создается из OpenTele
- если JSON поврежден, он пересоздается
- для подключения всегда используются данные из JSON

### Установка

```bash
pip install -e .
```

Или:

```bash
pip install telethon opentele
```

### Быстрый старт

```python
import asyncio
from tgacc import Hub


async def main() -> None:
    hub = Hub("sessions")
    hub.ensure_json("my_account")
    client = await hub.connect("my_account")
    me = await client.get_me()
    print(me.id if me else None, me.username if me else None)
    await hub.disconnect_all()


asyncio.run(main())
```

### Основной API

- `Hub`
  - `ensure_json(account_id)`
  - `load_json(account_id)`
  - `save_json(account)`
  - `discover_account_ids()`
  - `connect(account_id, **kwargs)`
  - `ensure_authorized(account_id, phone, code_callback, password_callback=None)`
  - `set_online(account_id, online=True)`
  - `disconnect(account_id)`
  - `disconnect_all()`
- `Acc`
- `Px`

### Исключения

- `TgErr`
- `OTErr`
- `JsonErr`

### Ручная проверка

```bash
python test.py my_account --limit 20
```

---

## License

MIT, see `LICENSE`.

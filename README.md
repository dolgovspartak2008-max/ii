# Telegram AI SaaS

Мультитенантный ИИ-ассистент для Telegram Business.

## Локальная разработка

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

## Docker

Скопируйте `.env.example` в `.env`, замените оба placeholder-токена, затем
запустите:

```powershell
docker compose up --build
```

Проверка состояния приложения:

```powershell
curl http://localhost:8000/healthz
```

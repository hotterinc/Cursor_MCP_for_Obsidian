---
title: Архитектура API
tags:
  - backend
  - api
---

# Архитектура API

## Обзор

Система использует REST API для взаимодействия с клиентами.

## Аутентификация

JWT токены используются для аутентификации. См. [[Auth Guide]].

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/login | Login |
| GET | /api/users | List users |

```python
def authenticate(token: str) -> bool:
    return verify_jwt(token)
```

#backend #architecture

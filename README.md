# FastAPI Auth Service

Сервис аутентификации на FastAPI с JWT, blacklist токенов и RBAC-схемой в PostgreSQL.

## Функциональность

- Регистрация пользователя: `POST /auth/register`
- Логин (`OAuth2PasswordRequestForm`): `POST /auth/login` (`username` = email)
- Обновление токенов: `POST /auth/refresh`
- Logout (инвалидация текущего токена): `POST /auth/logout`
- Текущий пользователь: `GET /users/me`
- Обновление профиля: `PUT /users/me`
- Мягкое удаление аккаунта: `DELETE /users/me`

### Поведение при logout и удалении

- При `logout` токен попадает в `token_blacklist`.
- На каждом защищенном запросе проверяется blacklist.
- При `DELETE /users/me`:
  - `is_active` переключается в `false`
  - текущий токен инвалидируется
  - повторный логин запрещен.

## Модель данных

### Users

Поля пользователя:
- `first_name`
- `last_name`
- `patronymic`
- `email` (уникальный)
- `hashed_password`
- `is_active`

### Token blacklist

Таблица `token_blacklist` хранит:
- `token_hash` (sha256)
- `token_type`
- `user_id` (nullable FK)
- `expires_at`
- `blacklisted_at`

### RBAC

- `roles`
- `resources`
- `permissions` (`role_id + resource_id + action`)
- `user_roles`

## Быстрый старт (через Make)

1. Инициализация env-файлов:

```bash
make env-init
```

2. Генерация JWT ключей:

```bash
make keys-init
```

3. Поднять dev-окружение:

```bash
make run-dev
```

4. Применить миграции:

```bash
make migrate
```

5. Заполнить RBAC стартовыми данными:

```bash
make seed-rbac
```

6. Прогнать тесты:

```bash
make test
```

## Что делает `make seed-rbac`

Запускает `scripts/seed_rbac.py` и идемпотентно создает:
- роли: `admin`, `moderator`, `user`
- ресурсы: `profile`, `auth`
- permissions для действий `read/write/delete`
- пользователей:
  - `admin@example.com` / `AdminPass123!`
  - `moderator@example.com` / `ModeratorPass123!`
  - `user@example.com` / `UserPass123!`
- назначения ролей для этих пользователей

## Проверочные RBAC-ручки

- `GET /users/check/admin`
- `GET /users/check/moderator`
- `GET /users/check/user`

Каждая ручка требует bearer token и возвращает `403`, если у текущего пользователя нет требуемой роли.

Повторный запуск безопасен: дубликаты не создаются.

## Полезные команды

- Остановить окружение: `make down-dev`
- Логи сервиса: `make logs-dev SERVICE=app`
- Shell в контейнере: `make shell-service-dev SERVICE=app`
- Пересборка: `make build-dev`

## Тесты и покрытие

- Тесты запускаются внутри контейнера: `make test`
- В проекте включен coverage с порогом (см. `pyproject.toml`)

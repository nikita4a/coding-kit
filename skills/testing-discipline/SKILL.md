---
name: testing-discipline
description: 'Использовать, когда пользователь хочет: добавить/починить тесты, понять что покрыто, определить «готово ли», воспроизвести баг тестом, проверить лимиты/rate-limit/отказы, или когда тесты пишут в реальную БД/сеть. Покрывает: изоляцию от prod-хранилища, domain-first тесты, имена тестов как спеку, граничные случаи, тесты денег/лимитов/UI/копии, DoD (parse + import + test + live process). Не использовать для стратегии дебага (debug-incident-protocol).'
compatibility: pytest, jest и аналоги; применимо к любому языку
---

# Testing discipline: тесты как спека и определение «готово»

## 1. Изоляция и структура

1. **NEVER TOUCH PROD STORE IN TESTS** — тесты на throwaway storage: env path override + temp file + fresh import. После suite prod row count неизменен.
2. **FRESH IMPORT FOR MODULE-LEVEL SIDE EFFECTS** — import-time connect/migrate ломает изоляцию: `sys.modules.pop` + importlib на каждый тест/фикстуру.
3. **UNIT DOMAIN FIRST, HANDLER WIRING SECOND** — бизнес-правила без фреймворка; хендлеры — тонкий клей с fakes для I/O. Domain suite зелёный offline за <2s.
4. **FAKE THE EDGES, NOT THE CORE** — мокай Telegram/HTTP/API; НЕ мокай свою бизнес-логику «для удобства». Handler test меняет реальную temp DB.

## 2. Имена и границы

- **TEST NAMES ARE THE SPEC** — `test_referral_no_self`, `test_crypto_idempotent` — имя = правило. `pytest --collect-only` читается как чеклист продукта. НЕ test_1, test_works.
- **PRODUCT RULES AS NAMED TESTS** — спека живёт в тестах: `test_free_spent_first`, `test_cannot_buy_while_paid_remains`. Новый разработчик читает тесты = понимает продукт.
- **ASSERT THE BOUNDARY CASES** — минимум на каждую функцию: happy + один edge + один abuse. free→0, paid edge, self-ref, double credit, empty username, overflow.
- **WRITE THE ABUSE CASE WHEN YOU WRITE THE GROWTH CASE** — рефералка/промо пишутся с анти-фрод тестом в том же PR.

## 3. Специфичные тесты

- **MONEY PATH**: double-submit → баланс +X не +2X; инъекция ошибки провайдера → баланс не меняется; reject → `assert not user_exists(...)`.
- **LIMITS (cap)**: тест до реализации: cap исчерпан → False, юзер не создан; monkeypatch.setenv; `assert cap and invited >= cap`.
- **RATE LIMIT**: два вызова подряд → второй заблокирован без внешнего API: mock API → assert len(calls) <= 1.
- **UI: PRESENCE + ROUTING** — на каждое UI-добавление: test_X_exists + test_X_routes_to_Y.
- **USER-FACING COPY AS REGRESSION TESTS** — `assert "ключевая фраза" in TEXT` — изменение копии = breaking change.
- **PAYLOAD VALIDATION** — `assert len(body.encode("utf-8")) <= PLATFORM_LIMIT` до деплоя.

## 4. DoD — определение «готово»

**«Закоммитил» ≠ «работает в рантайме».** Чеклист из 4 пунктов:

1. **Parse** — `python -m compileall -q` / синтаксис
2. **Import** — модуль импортируется без ошибок
3. **Test** — pytest зелёный (домен offline; интеграция с fakes)
4. **One live process** — реальный запуск entrypoint, лог OK

Три-шаговая верификация: **ruff → compileall → pytest** — в этом порядке, не пропуская.

## Workflow (порядок применения)

1. **Изолируй хранилище.** Тесты на throwaway storage.
2. **Определи слой тестирования.** Domain-логика — юнит без фреймворка; handler'ы — тонкий клей с fakes.
3. **Пиши тесты от правил продукта.** Имя = спека. `pytest --collect-only` = чеклист.
4. **Покрой границы.** На каждую функцию: happy + edge + abuse.
5. **Добавь специфичные тесты.** Money, limits, rate-limit, UI, copy, payload.
6. **Прогони три-шаговую верификацию.** ruff → compileall → pytest.
7. **DoD перед «готово».** parse + import + test + live process.

## Чеклист

- [ ] тесты не пишут в prod storage
- [ ] domain-логика тестируется без фреймворка
- [ ] на каждое правило есть именованный тест (имя = спека)
- [ ] границы: happy + edge + abuse
- [ ] money: double-submit, error-no-debit, no-side-effects-on-reject
- [ ] лимиты и rate-limit покрыты
- [ ] DoD: parse + import + test + live process
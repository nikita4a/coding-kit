---
name: money-path-safety
description: 'Использовать, когда пользователь хочет: оплатить/купить/подписаться, получить или потратить бонус/промокод/рефералку, проверить баланс или лимит, вернуть деньги, или когда меняется любая логика списания/начисления/квот — даже если запрос не называет деньги явно («дай ещё минут», «почему списалось дважды», «введи промокод»). Проверки: идемпотентность, атомарность, логирование мутаций, раздельные корзины, hard gate до дорогой работы, списание после успеха, soft delete, compound PK, structured failure. Не использовать для чистого CRUD без value-семантики и для дебага инцидентов (это debug-incident-protocol).'
compatibility: любые языки/стеки, где есть балансы, квоты, промокоды, лимиты
---

# Money path safety: деньги и ценность — особый класс кода

Дистилляция из боевых сессий биллинга. Применять к ЛЮБОМУ пути, где списывают/начисляют/оплачивают/ограничивают.

## 1. Деньги: железные правила

1. **MONEY PATH IS SACRED** — lock/транзакция + идемпотентность + лог на каждое событие + тест на double-submit. Проверка: дважды нажал «оплатить» → баланс +X, не +2X.
2. **IDEMPOTENCY BY DEFAULT** — ключ операции (invoice_id, event_id) + флаг credited + early return. Проверка: прогнать handler 2 раза — второй no-op.
3. **SEPARATE BUCKETS** — trial/promo/purchase/subscription = разные сущности, не одно поле `balance`. Явный порядок списания: free → bonus → paid.
4. **HARD GATE BEFORE EXPENSIVE WORK** — проверка права/лимита/денег ДО внешнего вызова (CPU/API/LLM). При нулевом балансе API не вызывается.
5. **CHARGE AFTER SUCCESS** — успех → debit; ошибка → no debit (+ log). Инъекция ошибки провайдера → баланс не меняется.
6. **LOG EVERY MUTATION** — одна строка на credit/debit/grant/refund: `charge uid=%s seconds=%.3f from_free=%.3f from_bonus=%.3f from_paid=%.3f`. grep по user_id восстанавливает историю.
7. **NO SILENT EXCEPT ON SIDE EFFECTS** — except: pass допустим на cleanup, НЕДОПУСТИМ на money/auth/data-loss. Money path: log + fallback или fail loud.
8. **READ-MODIFY-WRITE UNDER LOCK** — «прочитал→посчитал→записал» без блокировки = lost update. Mutex/транзакция на весь RMW.
9. **ONE SOURCE OF TRUTH** — UI/кэш/лог — производные. Истина — хранилище. Инцидент начинается с чтения storage, не с теории.

## 2. Атомарность в SQL (без гонок)

- **Atomic check-and-increment**: `UPDATE ... SET used = used + 1 WHERE used < max` — один запрос, rowcount 0 = лимит исчерпан. НЕ SELECT → IF → UPDATE.
- **Compound PK как идемпотентность**: `PRIMARY KEY (code, user_id)` — повтор блокируется на уровне БД, без SELECT перед INSERT.
- **SQLite**: `connect(timeout=30.0)` + `PRAGMA busy_timeout=30000` + `journal_mode=WAL` — три настройки вместе.
- **Metric upsert**: `INSERT ... ON CONFLICT DO UPDATE SET value=value+excluded.value` — без SELECT+UPDATE race.

## 3. Промокоды и value-операции

- **SOFT DELETE**: никогда DELETE бизнес-строки — `UPDATE status='finished'`. Аудит и FK выживают.
- **INPUT NORMALIZATION AT BOUNDARY**: каноническая форма один раз на входе (upper/strip/charset); downstream доверяет.
- **STRUCTURED FAILURE**: возвращать `(ok, reason_code, value)` — "not_found", "already_used", "exhausted"; UI мапит код в человеческое сообщение. НЕ просто False.
- **CREATOR-SCOPED ADMIN QUERIES**: `WHERE created_by=?` во всех admin-запросах; мутации проверяют владельца.
- **SINGLE CONSTANT DRIVES ALL SURFACES**: REFERRAL_BONUS=30 — в БД, UI-тексте, share-сообщении, тестах. Grep числа находит только определение.
- **PRE-CAP SIDE-EFFECT GUARD**: проверка cap ДО `_ensure()`/INSERT — иначе rejected-пользователи оставляют мусор в БД. Отказ → return без мутаций.

## Workflow (порядок применения)

1. **Найди денежные пути.** Grep по handler'ам/функциям: charge, debit, credit, grant, refund, invoice, balance, promo, referral, quota, limit. Отметь каждый путь списания/начисления.
2. **Проверь идемпотентность.** У каждого мутатора есть ключ операции + флаг credited + early return? Нет → добавь. Тест: прогнать дважды → второй no-op.
3. **Проверь атомарность.** RMW под lock/транзакцией? Инкременты лимитов — одним SQL с WHERE-ограничением? SQLite — timeout + busy_timeout + WAL?
4. **Проверь порядок и гейты.** Списание в одной функции (free→bonus→paid)? Hard gate ДО дорогого вызова? Charge после успеха, не на ошибке?
5. **Проверь логирование.** Каждая мутация логируется одной строкой с id субъекта и amount? grep по user_id восстанавливает историю? Нет silent except на money path?
6. **Проверь границы и отказы.** Rejected-операция не создаёт записей? Структурированные причины (ok, reason_code, value)? Cap=0 = unlimited явно?
7. **Проверь промо/рефералки.** Soft delete? Compound PK на повтор? no-self-deal? бонус только new accounts?
8. **Напиши/обнови тесты.** double-submit, error-no-debit, reject-no-side-effects, cap edge, abuse case. Имена = спека.

## Чеклист ревью money-кода

- [ ] double-submit → баланс не изменился дважды (тест)
- [ ] ошибка провайдера → списания нет (тест)
- [ ] каждая мутация логируется с id субъекта и amount
- [ ] нет except: pass на money path
- [ ] RMW под lock/транзакцией
- [ ] порядок списания — один алгоритм в одном месте (free→bonus→paid)
- [ ] rejected-операция не создала строк в БД (тест)
- [ ] у каждого лимита warning-лог при достижении
---
name: architecture-simplicity
description: 'Использовать, когда пользователь хочет: спроектировать/перепроектировать модули и слои, выбрать между библиотекой и своим кодом, понять почему проект стал god-file, добавить абстракцию «на вырост», обновить схему БД без потери данных, или на ревью архитектуры. Покрывает: YAGNI until second need, stdlib-first, модули по причине изменений, shared core + thin adapters, конфиг вне репо + дефолты в коде, эволюцию схемы без DROP, fallback chain провайдеров, нерепрезентабельные невалидные состояния, удаление мёртвого кода. Не использовать для денег (money-path-safety).'
compatibility: любой язык и стек, этап проектирования/ревью архитектуры
---

# Architecture & simplicity: проектные принципы

## 1. Простота и зависимость

1. **YAGNI UNTIL SECOND NEED** — абстракция с одним потребителем — долг, не архитектура. Inline до второго потребителя; тогда extract. Можно удалить слой — поведение то же, кода меньше.
2. **STD LIB / PLATFORM BEFORE DEPENDENCY** — новая зависимость дороже 30 строк своего кода (часто). Сначала stdlib/native; dep только если боль измерима. moment.js ради одного format = нет.
3. **SEPARATE MODULES BY CHANGE REASON** — generators.py, payments.py, access.py, bot.py — разные оси изменений. Фича PDF не требует трогать billing. НЕ 3000-line god file.
4. **SHARED CORE, THIN ADAPTERS** — бизнес-логика одна; Telegram/CLI/desktop — оболочка (I/O + auth + UX). Баг в polish чинится в одном месте, оба клиента ок.
5. **STOP WHEN THE NEXT ABSTRACTION DOESN'T PAY RENT THIS WEEK** — абстракция должна окупаться сейчас, не «когда-нибудь».

## 2. Конфиг и эволюция

- **CONFIG OUTSIDE REPO, DEFAULTS IN CODE** — секреты и ops-тюнинг не в git; безопасные default'ы в коде; override env.
- **SCHEMA EVOLUTION MUST NOT WIPE PROD** — деплой не требует DROP TABLE: CREATE IF NOT EXISTS + ALTER ADD COLUMN ignore-if-exists.
- **FEATURE FLAG/ENV DEFAULT > REWRITE** — ops-тюнинг через флаг/env, не переписывание.
- **DETERMINISTIC REBUILD > STALE CACHE** — пересобрать детерминированно лучше, чем жить со старым кэшем.

## 3. Паттерны кода

- **EXPLICIT SPEND ORDER IN ONE FUNCTION** — порядок списания (free→bonus→paid) — один алгоритм в одном месте.
- **FALLBACK CHAIN FOR PROVIDERS** — один вендор = SPOF: ordered list; next on timeout/5xx; fail только когда все мертвы.
- **PURE FUNCTIONS FOR ASSEMBLE/EXPORT; IMPURE AT THE EDGES** — сборка/экспорт — чистые функции; I/O на границах.
- **MAKE ILLEGAL STATES UNREPRESENTABLE** — отдельные поля > boolean soup: `status: active|finished` вместо флагов.
- **COMMENTS EXPLAIN WHY AND CEILING** — не что делает строка, а почему и какой потолок.
- **DELETE DEAD CODE; DON'T COMMENT IT OUT FOREVER** — мёртвый код удаляется.
- **NAMING: VERBS THAT MEAN $** — charge_seconds, apply_referral, can_afford — имена-глаголы с денежным смыслом.
- **FLOAT MONEY IS EVIL LONG-TERM** — деньги не float; минуты можно, если консистентно + тесты.

## Workflow (порядок применения)

1. **Определи границы модулей по причине изменений.** Разные оси → разные модули. Нет god-file на 3000 строк.
2. **Проверь каждую абстракцию на YAGNI.** Один потребитель? → inline. Можно удалить слой? → удалить.
3. **Проверь зависимости.** Сначала stdlib/платформа; dep только если боль измерима.
4. **Раздели ядро и адаптеры.** Бизнес-логика одна; оболочки тонкие.
5. **Проверь конфиг и секреты.** Секреты вне git; дефолты в коде; override env.
6. **Проверь эволюцию схемы.** Деплой без DROP TABLE.
7. **Проверь ключевые паттерны.** Порядок списания в одной функции. Fallback chain. Невалидные состояния нерепрезентабельны.
8. **Убери мёртвое.** Мёртвый код удаляется. Комментарии WHY, не WHAT.

## Чеклист ревью архитектуры

- [ ] нет абстракций с одним потребителем (YAGNI)
- [ ] зависимость оправдана (stdlib сначала)
- [ ] модули разделены по причине изменений
- [ ] бизнес-ядро одно; адаптеры тонкие
- [ ] секреты вне репо; дефолты в коде
- [ ] схема эволюционирует без DROP
- [ ] порядок списания в одной функции
- [ ] fallback chain на провайдеров
- [ ] невалидные состояния нерепрезентабельны
- [ ] мёртвый код удалён; комментарии WHY
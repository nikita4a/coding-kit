---
name: windows-encoding-fixes
description: 'Использовать при работе с Windows (консоль cmd/PowerShell, MINGW64, установка скриптов): кодировка stdout (cp1251 vs UTF-8, UnicodeEncodeError на ✓/кириллице), CRLF/LF при записи файлов (md5-проверки зеркал), UTF-8 BOM для PowerShell 5.1, npm.cmd вместо npm, venv Scripts vs bin, PYTHONIOENCODING/PYTHONUTF8. Проверено на 2 багрепортах Windows 10.'
compatibility: Windows (win32), PowerShell 5.1, MINGW64, Python 3.12
license: Proprietary
---


# Windows: кодировки, консоль, кроссплатформенность

Опыт из двух багрепортов установки coding-kit на Windows 10 (research.db
id=141, 146). Каждая грабля — с симптомом, причиной, фиксом. Применять
к ЛЮБОМУ скрипту/файлу, который должен работать и на Windows.

## 1. Кодировка stdout: cp1251 убивает русский вывод

**Симптом:** `UnicodeEncodeError: '\u2713' ... codec can't encode` — падает
на печати `✓`/`✗`/кириллицы. Проявляется при перенаправлении вывода
(`script > log 2>&1`) и в cp1251-консоли.

**Причина:** Windows-консоль по умолчанию cp1251; Python 3.12 при
перенаправлении берёт кодировку консоли, юникод в неё не входит.

**Фикс (обязателен в каждом CLI-скрипте):**
```python
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален
    pass
```
В coding-kit — единый `scripts/_compat.py: fix_encoding()` вместо копирования.

**Фикс для bash-обёрток (run_tests.sh):**
```bash
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
```

**Системный фикс (рекомендация в SETUP.md):**
```powershell
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
```

## 2. Запись файлов: CRLF ломает md5-проверки

**Симптом:** `Path.write_text()` на Windows пишет `\r\n`; канон — `\n`.
Любая md5-проверка зеркал/копий ложно падает: «файлы разошлись».

**Фикс при записи:** `newline="\n"` + сравнение по байтам:
```python
dst.write_text(content, encoding="utf-8", newline="\n")
# проверка актуальности:
if dst.read_bytes() == content.encode("utf-8"): ...
```

**Фикс при проверке (bash, md5 с нормализацией):**
```bash
first=$(tr -d '\r' < "${MIRRORS[0]}" | md5sum | cut -d' ' -f1)
```

## 3. PowerShell 5.1: UTF-8 без BOM читается как cp1251

**Симптом:** `bootstrap.ps1` игнорирует `--check`, выводит кракозябры,
падает на тире «—» в комментариях.

**Причина:** Windows PowerShell 5.1 декодирует .ps1 без BOM как cp1251;
кириллица и тире ломают парсинг (вплоть до логики аргументов).

**Фикс:** сохранить .ps1 в UTF-8 **with BOM** (EF BB BF в начале файла).
```python
if not data.startswith(b"\xef\xbb\xbf"):
    p.write_bytes(b"\xef\xbb\xbf" + data)
```
Проверка: `head -c 3 file.ps1 | od -An -tx1` → `ef bb bf`.

## 4. npm на Windows — это npm.cmd

**Симптом:** `subprocess.run(["npm", "install", ...])` →
`FileNotFoundError: [WinError 2]`.

**Причина:** CreateProcess (без shell) не запускает .cmd-файлы; на Windows
npm — это npm.cmd.

**Фикс:** искать `npm.cmd` первым на Windows:
```python
def _npm_cmd():
    if os.name == "nt":
        for name in ("npm.cmd", "npm"):
            p = shutil.which(name)
            if p:
                return p
    return "npm"
```

## 5. venv: bin vs Scripts, .exe

**Симптом:** скрипт ищет `venv/bin/python` — на Windows его нет, venv в
`venv\Scripts\python.exe`.

**Фикс (единый резолвер, `_compat.py`):**
```python
VENV_BIN = VENV / ("Scripts" if os.name == "nt" else "bin")
# бинарь на Windows — с .exe:
# d / "Scripts" / f"{name}.exe"  vs  d / "bin" / name
```
В bash: перебирать кандидатов `Scripts/python.exe` и `bin/python`.

## 6. winget кладёт бинари не в PATH

**Симптом:** `shutil.which("clangd")` не находит — но clangd установлен.

**Причина:** winget кладёт в `%LOCALAPPDATA%\Microsoft\WinGet\Links\`
(этот каталог не всегда в PATH процесса).

**Фикс:** искать и там:
```python
win_get = Path(os.environ.get("LOCALAPPDATA", HOME)) / "Microsoft" / "WinGet" / "Links"
extra = [str(win_get / "clangd.exe")] if os.name == "nt" else []
```

## 7. GitHub-релизы: у проектов разные форматы ассетов по платформам

**Симптом:** скрипт ищет `win32-x64.tar.gz`, а проект отдаёт только
`.zip` для Windows (LuaLS), или наоборот.

**Фикс:** формат ассета выбирать по платформе:
```python
ext = r"\.zip" if IS_NT else r"\.tar\.gz"
m = re.search(rf'https://[^"]*{key}-{variant}{ext}', json)
# распаковка: zipfile.ZipFile (NT) vs tarfile.open (posix)
```

## 8. bash в PATH Windows — WSL-заглушка, не Git Bash

**Симптом:** `C:\Windows\System32\bash.exe` выводит «для перечисления
дистрибутивов используйте wsl.exe --list» и падает.

**Причина:** системный bash.exe — заглушка WSL, а не Git Bash.

**Фикс:** в доке требовать Git for Windows (`C:\Program Files\Git\bin\
bash.exe`) или PowerShell-обёртки. Не рассчитывать на `bash` из PATH.

## 9. Camoufox на Windows: три класса багов (ресёрч 08.2026)

Проверено по issues daijro/camoufox (#282, #614, #624, #650). Симптомы —
из багрепортов и PR, фиксы — рабочие:

**9a. Python из Microsoft Store сандбоксит AppData\Local (#282).**
`camoufox fetch` пишет «successfully installed», но `camoufox.exe` не
находится: Store-версия Python перенаправляет `AppData\Local` в
`Packages\PythonSoftwareFoundation...\LocalCache`. Фикс: Python с
python.org (не MS Store). Проверка: `sys.executable` содержит
`WindowsApps` → предупредить.

**9b. headless падает с STATUS_BREAKPOINT 0x80000003 (#614).**
На части Windows-билдов headless-запуск мгновенно крашится (headed
работает). Фикс: fallback `headless=False, windows_hide=True` — окно
скрыто от пользователя. В нашем воркере (`mcp/camoufox_worker.py`) —
автоматически в `_launch()`: try headless → except (только на NT) →
headed+hidden.

**9c. SxS mozglue / нет MSVC CRT (#624/#650).**
«The application has failed to start because its side-by-side
configuration is incorrect» / Playwright `spawn UNKNOWN` на чистых
системах. Причины: встроенный манифест объявляет mozglue как SxS-
зависимость; AppContainer SID от Edge/Chrome в AppData\Local включает
строгий режим; пакет может не содержать VCRUNTIME140.dll. Фиксы:
VC++ Redistributable (x64), установка вне AppData\Local
(`CAMOUFOX_INSTALL_DIR=C:\Users\...\.camoufox`), обновление до v152+.

**Диагностика:** `python3 scripts/tools/update_camoufox.py --check` — проверяет
всё выше + обновляет пакет/браузер. См. также `mcp/README.md» «Camoufox
на Windows».

## 10. subprocess: кодировка вывода детей (BUG-1/4, багрепорт v2.4)

**Симптом:** `UnicodeDecodeError: 'charmap' codec can't decode byte 0x98`
в reader-потоках subprocess (часть вывода теряется; у LuaLS-скачивания
`stdout` стал None → «ассет не найден») или кракозябры `Џа®ўҐапо §ҐаЄ`
вместо «Проверяю зеркала» (doctor.py).

**Причина:** `subprocess.run(..., text=True)` без явной кодировки берёт
ANSI-кодовую страницу (`locale.getencoding()` — cp1251), а консольные
дети пишут в OEM-страницу (cp866, `GetConsoleOutputCP`). Двух разных
кодировок нет и не будет (CPython issue #105312).

**Фикс с двух сторон (общий хелпер + дети пишут UTF-8):**

```python
# родитель: scripts/_compat.py run() — декодирует utf-8 + errors=replace,
# python-детям передаёт PYTHONUTF8=1 (они пишут UTF-8). НИКОГДА не падает
# на чужой кодировке:
r = _compat.run(cmd, timeout=120)          # вместо subprocess.run(text=True)
```

```powershell
# ребёнок: PowerShell 5.1 пишет в пайпы OEM-страницей — переключить в
# начале .ps1 (about_Character_Encoding):
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [Console]::OutputEncoding
```

**Отвергнуто:** `encoding='oem'` — есть только в Python 3.13+ (нужно
поддерживать 3.12); декодирование через `GetOEMCP()` только в родителе —
не лечит вывод python-детей, которые сами пишут UTF-8 (после
`fix_encoding()`), и всё равно не спасает от потери вывода при битой
кодировке; `errors="strict"` — один чужой байт роняет весь захват.

## Универсальные грабли кроссплатформенности

Наши 8 граблей — НЕ уникальные: это известные классы проблем, описанные
в индустрии (blog.shellnetsecurity.com «Cross-Platform Scripting Tips»,
PEP 686, pythonfriday.dev #130). Проверено веб-ресёрчем 08.2026.

**Из наших граблей универсальны (подтверждены источниками):**
- кодировка stdout (cp1251 vs UTF-8) — PEP 686, pythonfriday.dev #130;
- CRLF/LF при записи и md5-проверках — классика (git core.autocrlf,
  .gitattributes);
- npm.cmd / .cmd-файлы через CreateProcess — известный WinError 2 класс;
- venv Scripts vs bin — стандартное отличие, у всех venv-инструментов;
- ассеты GitHub-релизов по платформе — общая проблема автоматизации.

**Чего НЕТ у нас, но известно в индустрии (добавить в код при случае):**

| Грабля | Симптом | Фикс |
|---|---|---|
| Разделители путей | хардкод `/` в путях | `Path.home() / "x"` или `os.path.join()` (pathlib) |
| Регистр файлов | `Config.json` == `config.json` на NTFS/macOS, ≠ на Linux | единый регистр имён, не полагаться на чувствительность |
| HOME vs USERPROFILE | на Windows `$HOME` часто не задан (без Git Bash) | `Path.home()` в Python; в bash `${HOME:-$USERPROFILE}` |
| TEMP vs /tmp | TMPDIR/TEMP различаются | `tempfile.gettempdir()` |
| find/which/grep/sed | утилит нет или другие (find = поиск текста!) | `shutil.which`, python вместо unix-пайплайнов |
| curl — алиас | в PowerShell `curl` = Invoke-WebRequest | `curl.exe` явно |
| Захват файла (lock) | Windows держит открытые файлы, PermissionError | закрывать файлы (with), не удалять открытое |
| Shell по умолчанию | bash нет нативно, PowerShell/CMD свои синтаксисы | один шелл + требовать его (Git Bash) или Python |
| subprocess + PATH на Windows | shell=True решает поиск, но грязно | явные пути, shutil.which, .cmd-обёртки |
| PEP 686: UTF-8 по умолчанию | Python 3.15 включит UTF-8 везде | уже сейчас писать `encoding="utf-8"` явно — потом не сломается |

**Вывод:** наши грабли — частный случай общих классов; скилл держит
конкретные фиксы, таблица выше — страховку от «следующей» грабли.

## Чеклист «скрипт готов к Windows»

- [ ] `fix_encoding()` (или reconfigure) в начале — stdout utf-8
- [ ] вывод детей — через `_compat.run()` (не `subprocess.run(text=True)`
      без encoding) — раздел 10; .ps1-дети — `[Console]::OutputEncoding`
- [ ] запись файлов с `newline="\n"`, сравнение по байтам
- [ ] venv через резолвер (Scripts vs bin, .exe)
- [ ] npm → npm.cmd (или shell=True), winget-ссылки как extra-путь
- [ ] .ps1 — UTF-8 with BOM
- [ ] md5-проверки с `tr -d '\r'`
- [ ] ассеты GitHub-релизов по платформе (zip vs tar.gz)
- [ ] пути — только pathlib/Path.home(), без хардкода `/` и `\`
- [ ] файлы читать/писать с явным `encoding="utf-8"` (PEP 686-готовность)
- [ ] temp-файлы — `tempfile.gettempdir()`, не `/tmp`
- [ ] прогон `python3 scripts/doctor/doctor.py` на Windows (0 ошибок)

## Ссылки

- `scripts/_compat.py` — единый кроссплатформенный модуль (coding-kit).
- Первый багрепорт Windows, второй, doctor-диагностика.
- Источники: blog.shellnetsecurity.com «Cross-Platform Scripting Tips
  and Tricks» (01.2026); PEP 686 (UTF-8 default, Python 3.15);
  pythonfriday.dev #130 «Different File Encodings Between Windows and
  Linux».

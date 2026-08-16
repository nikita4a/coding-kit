#!/usr/bin/env python3

"""Общий кроссплатформенный модуль coding-kit: кодировка stdout, пути venv,
платформенные хелперы. Единое место вместо копирования в каждый скрипт
(рекомендация из багрепорта Windows: «продублируйте в общий модуль,
а не копируйте в 6 файлов»).

Использование:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
    import _compat
    _compat.fix_encoding()          # stdout/stderr → UTF-8 (Windows cp1251)
    py = _compat.venv_python()      # путь к python проекта (bin/ vs Scripts/)
"""

import os
import subprocess
import sys
from pathlib import Path


IS_NT = os.name == "nt"
IS_CI = os.environ.get("CI") == "true"


def fix_encoding():
    """Windows-консоль по умолчанию cp1251 — русский вывод (✓/✗/кириллица)
    падает с UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
    Вызывать в начале каждого CLI-скрипта."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
        pass


def run(cmd, *, timeout=None, cwd=None, env=None, check=False):
    """subprocess.run для CLI-скриптов: кроссплатформенная кодировка.

    Windows-грабля (багрепорт v2.4 BUG-1/4): text=True без явной кодировки
    берёт ANSI-кодовую страницу (locale.getencoding — cp1251), а консольные
    дети пишут в OEM (cp866) — UnicodeDecodeError в reader-потоках или
    кракозябры (CPython issue #105312). Фикс с двух сторон:
    (1) python-детям передаём PYTHONUTF8=1 — они пишут UTF-8;
    (2) вывод декодируем utf-8 + errors="replace" — на чужой кодировке
    никогда не падаем (PowerShell-дети переключаются сами через
    [Console]::OutputEncoding, см. run_tests.ps1).
    """
    child_env = os.environ.copy() if env is None else {**os.environ, **env}
    if IS_NT:
        child_env.setdefault("PYTHONUTF8", "1")
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          timeout=timeout, cwd=cwd, env=child_env, check=check)


# Маркеры корня coding-kit: файлы/папки, которые есть ТОЛЬКО в корне воркспейса
# (VERSION уникален — в проектах его нет; db-tools/ и scripts/_compat.py —
# часть корня). Используются для валидации найденного корня.
ROOT_MARKERS = ("VERSION", "db-tools", "scripts/_compat.py")


def chulan_root():
    """Корень coding-kit. Паттерн индустрии (jayqi/python-find-project-root-
    cookbook, R here): цепочка — (1) явный оверрайд $CODING_KIT_ROOT, (2)
    маркер-файл VERSION при подъёме вверх, (3) __file__-based fallback.
    Никаких захардкоженных путей: корень может лежать где угодно (любая
    ОС, любой mount point, распакованный архив) — находится автоматически.
    Ошибка, если найденное место не похоже на корень (переименовано,
    скрипт перенесён) — вместо молчаливой работы из неверного каталога.
    """
    env = os.environ.get("CODING_KIT_ROOT")
    if env:
        root = Path(env).expanduser()
        if not root.is_absolute():
            raise RuntimeError(
                f"CODING_KIT_ROOT должен быть абсолютным путём: {env!r}")
        _validate_root(root, source="CODING_KIT_ROOT")
        return root
    here = Path(__file__).resolve().parent.parent  # scripts/ -> корень
    _validate_root(here, source="__file__")
    return here


def _validate_root(root, source):
    """Проверка, что каталог действительно корень coding-kit (маркеры на месте)."""
    missing = [m for m in ROOT_MARKERS if not (root / m).exists()]
    if missing:
        raise RuntimeError(
            f"корень coding-kit ({source}) не похож на корень: {root} — "
            f"нет маркеров: {', '.join(missing)}. Задайте CODING_KIT_ROOT или "
            f"положите файл VERSION в корень воркспейса.")


def venv_dir():
    """Общий venv воркспейса: ~/.venvs/coding-kit (вынесенный из папки, чтобы
    проект шерился чисто). Создаётся setup.py (ensure_env)."""
    return Path.home() / ".venvs" / "coding-kit"


def venv_python():
    """Путь к python в venv проекта (bin/python vs Scripts/python.exe)."""
    d = venv_dir()
    if IS_NT:
        return d / "Scripts" / "python.exe"
    return d / "bin" / "python"


def yaml_scalar(value):
    """YAML-скаляр из python-значения. JSON-строка — валидный YAML
    (двойные кавычки): json.dumps безопасен для путей и аргументов.
    Используется текстовыми YAML-хирургами (install_mcp apply_hermes,
    install_proshivka hermes-hook) — без YAML-парсера, чтобы не убивать
    комментарии и чужое форматирование."""
    import json
    if isinstance(value, str):
        return json.dumps(value)
    return str(value)


def replace_top_level_yaml_block(path, block, marker):
    """Хирургическая замена top-level блока YAML-конфига: строка marker
    без отступа + все последующие строки с отступом заменяются на block;
    остальное (чужие секции, комментарии) сохраняется байт-в-байт.
    Нет блока — дописывается в конец. Файла нет — создаётся (родительский
    каталог создаётся сам). Возвращает True, если блок был найден (заменён),
    False — если дописан в конец (нужно для логики «есть ли у юзера свой
    блок»)."""
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
        lines = text.splitlines()
        out = []
        i = 0
        replaced = False
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            is_block_start = (
                bool(line) and not line[0].isspace()
                and (stripped == marker
                     or stripped.startswith(marker + " ")
                     or stripped.startswith(marker + "\t")
                     or stripped.startswith(marker + "#"))
            )
            if is_block_start:
                i += 1
                while i < len(lines) and (
                        not lines[i].strip() or lines[i][0].isspace()):
                    i += 1
                out.extend(block.splitlines())
                replaced = True
                continue
            out.append(line)
            i += 1
        if not replaced:
            if out and out[-1].strip():
                out.append("")
            out.extend(block.splitlines())
        text = "\n".join(out) + "\n"
    else:
        replaced = False
        text = block
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return replaced
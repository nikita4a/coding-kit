

"""parsers — парсеры языков (tree-sitter JS/TS/bash) + extract-API
(символы/импорты/вызовы/наследование/ошибки).

Вынесено из build.py механически (verbatim) — гейт god-файлов
(FILE-SIZE.md). build.py реэкспортирует extract_* (контракт тестов)."""
import ast
import glob
import os
import sys

_JS_EXTS = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}
_TS_LANGS = {".js": "javascript", ".mjs": "javascript",
             ".cjs": "javascript", ".jsx": "javascript",
             ".ts": "typescript", ".tsx": "tsx",
             ".sh": "bash"}
_SH_EXTS = {".sh"}

def _ts_parser(content, ext):
    """Парсер tree-sitter для JS/TS. Ленивый import: если библиотеки нет —
    None (старое поведение: файл без символов). tree_sitter_language_pack
    живёт в venv проекта (~/.venvs/coding-kit, приходит с code-review-graph), а
    build.py запускается и системным python3 — подмешиваем site-packages
    venv при первом импорте."""
    try:
        from tree_sitter_language_pack import get_parser
    except ImportError:
        sp = _venv_site_packages()
        if sp and sp not in sys.path:
            sys.path.insert(0, sp)
        try:
            from tree_sitter_language_pack import get_parser
        except ImportError:
            return None
    try:
        return get_parser(_TS_LANGS[ext]).parse(bytes(content, "utf-8"))
    except Exception:
        return None


def _venv_site_packages():
    """site-packages venv проекта (~/.venvs/coding-kit) или None."""
    if os.name == "nt":
        p = os.path.join(os.path.expanduser("~"), ".venvs", "coding-kit",
                         "Lib", "site-packages")
        return p if os.path.isdir(p) else None
    hits = glob.glob(os.path.join(os.path.expanduser("~"), ".venvs",
                                  "coding-kit", "lib*", "python*",
                                  "site-packages"))
    return hits[0] if hits else None


def _ts_text(node):
    return node.text.decode("utf-8", errors="replace") if node else ""


def _ts_symbols(rel_path, content):
    """Символы JS/TS: function_declaration, class_declaration (с базой),
    method_definition, const f = () => {} / function () {}."""
    ext = os.path.splitext(rel_path)[1].lower()
    tree = _ts_parser(content, ext)
    if tree is None:
        return []
    syms = []
    name_types = ("identifier", "type_identifier")

    def params(node):
        for c in node.children:
            if c.type == "formal_parameters":
                return _ts_text(c)
        return "()"

    def ids(node):
        """Все идентификаторы под узлом (рекурсивно): имя класса в TS —
        type_identifier, база может быть обёрнута extends_clause."""
        out = []
        for c in node.children:
            if c.type in name_types:
                out.append(c)
            out.extend(ids(c))
        return out

    def walk(node, in_class=False):
        t = node.type
        if t in ("function_declaration", "generator_function_declaration"):
            name = next((c for c in node.children
                         if c.type == "identifier"), None)
            if name:
                nm = _ts_text(name)
                sig = f"function {nm}{params(node)}"
                syms.append((nm, "method" if in_class else "function",
                             node.start_point[0] + 1, sig))
            for c in node.children:
                walk(c, False)
        elif t == "class_declaration":
            found = ids(node)
            name = found[0] if found else None
            if name:
                nm = _ts_text(name)
                base = ""
                h = next((c for c in node.children
                          if c.type == "class_heritage"), None)
                if h:
                    b = ids(h)
                    if b:
                        base = f"({_ts_text(b[-1])})"
                syms.append((nm, "class", node.start_point[0] + 1,
                             f"class {nm}{base}"))
            for c in node.children:
                walk(c, True)
        elif t == "method_definition":
            name = next((c for c in node.children
                         if c.type == "property_identifier"), None)
            if name:
                nm = _ts_text(name)
                syms.append((nm, "method", node.start_point[0] + 1,
                             f"method {nm}{params(node)}"))
        elif t == "variable_declarator":
            name = next((c for c in node.children
                         if c.type == "identifier"), None)
            fn = next((c for c in node.children
                       if c.type in ("arrow_function", "function_expression",
                                     "generator_function")), None)
            if name and fn:
                nm = _ts_text(name)
                syms.append((nm, "function", node.start_point[0] + 1,
                             f"function {nm}{params(fn)}"))
            for c in node.children:
                walk(c, in_class)
        else:
            for c in node.children:
                walk(c, in_class)

    walk(tree.root_node)
    return sorted(syms, key=lambda s: s[2])


def _ts_imports(rel_path, content):
    """Рёбра импортов для JS/TS: (модуль, строка). Модуль — имя файла
    из строки импорта (./mod.js -> mod.js), как .py берёт корневой пакет."""
    ext = os.path.splitext(rel_path)[1].lower()
    tree = _ts_parser(content, ext)
    if tree is None:
        return []
    edges = []

    def walk(node):
        if node.type == "import_statement":
            for c in node.children:
                if c.type == "string":
                    mod = _ts_text(c).strip("'\"")
                    edges.append((mod.split("/")[-1],
                                  node.start_point[0] + 1))
                    break
        for c in node.children:
            walk(c)

    walk(tree.root_node)
    return edges


def _ts_calls(rel_path, content):
    """Рёбра вызовов для JS/TS: (имя_вызываемого, строка). Имя — последний
    атрибут цепочки (chrome.tabs.query -> query), как в .py."""
    ext = os.path.splitext(rel_path)[1].lower()
    tree = _ts_parser(content, ext)
    if tree is None:
        return []
    edges = []

    def walk(node):
        if node.type == "call_expression" and node.children:
            fn = node.children[0]
            if fn.type == "identifier":
                edges.append((_ts_text(fn), node.start_point[0] + 1))
            elif fn.type == "member_expression":
                prop = next((c for c in fn.children
                             if c.type == "property_identifier"), None)
                if prop:
                    edges.append((_ts_text(prop), node.start_point[0] + 1))
        for c in node.children:
            walk(c)

    walk(tree.root_node)
    return edges


def _ts_inherits(rel_path, content):
    """Наследование для JS/TS: (класс, базовый, строка) из class_heritage."""
    ext = os.path.splitext(rel_path)[1].lower()
    tree = _ts_parser(content, ext)
    if tree is None:
        return []
    edges = []

    def ids(node):
        out = []
        for c in node.children:
            if c.type in ("identifier", "type_identifier"):
                out.append(c)
            out.extend(ids(c))
        return out

    def walk(node):
        if node.type == "class_declaration":
            found = ids(node)
            h = next((c for c in node.children
                      if c.type == "class_heritage"), None)
            if found and h:
                base = ids(h)
                if base:
                    edges.append((_ts_text(found[0]), _ts_text(base[-1]),
                                  node.start_point[0] + 1))
        for c in node.children:
            walk(c)

    walk(tree.root_node)
    return edges


def _ts_errors(rel_path, content):
    """Синтаксические ошибки JS/TS: (строка, сообщение) — первый ERROR-узел
    или missing-узел (не закрытая скобка и т.п.)."""
    ext = os.path.splitext(rel_path)[1].lower()
    tree = _ts_parser(content, ext)
    if tree is None:
        return []
    if not tree.root_node.has_error:
        return []
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "ERROR" or n.is_missing:
            return [(n.start_point[0] + 1, "syntax error (tree-sitter)")]
        stack.extend(n.children)
    return []


def _walk_ts(node):
    """Обход дерева tree-sitter целиком (все узлы, включая вложенные)."""
    yield node
    for c in node.children:
        yield from _walk_ts(c)


def _ts_bash_symbols(content):
    """Символы bash: function_definition через tree-sitter-bash (имя, строка).
    Ловит все формы: `name() {}`, `function name {}`, `function name() {}`,
    многострочные тела — то, что регекс 'name() {' пропускал (function-ключевое
    слово, пробел перед скобками, '{' на следующей строке)."""
    tree = _ts_parser(content, ".sh")
    if tree is None:
        return []
    syms = []
    for node in _walk_ts(tree.root_node):
        if node.type == "function_definition":
            name = next((c for c in node.children if c.type == "word"), None)
            if name:
                syms.append((_ts_text(name), "function",
                             node.start_point[0] + 1, ""))
    return sorted(syms, key=lambda s: s[2])


def _ts_bash_calls(content):
    """Вызовы bash: узлы command — имя команды и строка (для графа --calls)."""
    tree = _ts_parser(content, ".sh")
    if tree is None:
        return []
    edges = []
    for node in _walk_ts(tree.root_node):
        if node.type == "command":
            cn = node.child_by_field_name("name")
            if cn is not None and cn.type == "command_name":
                w = next((c for c in cn.children if c.type == "word"), None)
                if w:
                    edges.append((_ts_text(w), node.start_point[0] + 1))
    return edges


def _ts_bash_errors(rel_path, content):
    """Синтаксические ошибки bash: tree-sitter has_error (как _ts_errors для JS)."""
    tree = _ts_parser(content, ".sh")
    if tree is None:
        return []
    return [(rel_path, "tree-sitter")] if tree.root_node.has_error else []


def extract_symbols(rel_path, content):
    """Символы файла: (имя, тип, строка, сигнатура). Для .py —
    функции/классы/методы через ast (у функций — сигнатура); для .md —
    заголовки (# / ## / ###) как разделы; для .sh — функции через
    tree-sitter-bash (fallback: регекс 'имя() {'); для .js/.ts —
    tree-sitter (функции, классы, методы, стрелочные в переменных)."""
    ext = os.path.splitext(rel_path)[1].lower()
    syms = []
    if ext in _JS_EXTS:
        return _ts_symbols(rel_path, content)
    if ext == ".py":
        import ast
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return syms

        def sig(node):
            try:
                args = node.args
                parts = [a.arg for a in args.posonlyargs + args.args]
                if args.vararg:
                    parts.append("*" + args.vararg.arg)
                for a in args.kwonlyargs:
                    parts.append(a.arg)
                if args.kwarg:
                    parts.append("**" + args.kwarg.arg)
                return f"def {node.name}({', '.join(parts)})"
            except (AttributeError, TypeError, ValueError):
                return f"def {node.name}(...)"

        def walk(node, in_class=False):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    kind = "method" if in_class else "function"
                    syms.append((child.name, kind, child.lineno,
                                 sig(child)))
                    walk(child, in_class=False)
                elif isinstance(child, ast.ClassDef):
                    bases = [b.id for b in child.bases if isinstance(b, ast.Name)]
                    syms.append((child.name, "class", child.lineno,
                                 f"class {child.name}({', '.join(bases)})"
                                 if bases else f"class {child.name}"))
                    walk(child, in_class=True)
                else:
                    walk(child, in_class)

        walk(tree)
        return sorted(syms, key=lambda s: s[2])
    if ext == ".md":
        import re
        for i, line in enumerate(content.split("\n"), 1):
            m = re.match(r"^(#{1,3})\s+(.*)$", line)
            if m:
                depth = len(m.group(1))
                syms.append((m.group(2).strip(), f"h{depth}", i, ""))
        return syms
    if ext == ".sh":
        syms = _ts_bash_symbols(content)
        if syms:
            return syms
        # фолбэк без tree-sitter (системный python3 без venv-пакета)
        import re
        for i, line in enumerate(content.split("\n"), 1):
            m = re.match(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\(\)\s*(\{)?\s*(#.*)?$",
                         line)
            if m:
                syms.append((m.group(1), "function", i, ""))
        return syms
    return syms


def extract_imports(rel_path, content):
    """Рёбра импортов: .py — ast; .js/.ts — tree-sitter."""
    ext = os.path.splitext(rel_path)[1].lower()
    if ext in _JS_EXTS:
        return _ts_imports(rel_path, content)
    if not rel_path.endswith(".py"):
        return []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    edges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                edges.append((a.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            edges.append((mod.split(".")[0], node.lineno))
    return edges


def extract_calls(rel_path, content):
    """Рёбра вызовов: .py — ast; .js/.ts — tree-sitter; .sh — tree-sitter-bash.
    Имя — последний атрибут цепочки (os.path.join -> join, tg_send_text)."""
    ext = os.path.splitext(rel_path)[1].lower()
    if ext in _JS_EXTS:
        return _ts_calls(rel_path, content)
    if ext in _SH_EXTS:
        return _ts_bash_calls(content)
    if not rel_path.endswith(".py"):
        return []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    edges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                edges.append((f.id, node.lineno))
            elif isinstance(f, ast.Attribute):
                edges.append((f.attr, node.lineno))
    return edges


def extract_inherits(rel_path, content):
    """Наследование: .py — ast; .js/.ts — tree-sitter (class X extends Y).
    Простые имена (class X(Base)) и последний атрибут цепочки
    (unittest.TestCase -> TestCase, как в extract_calls): полное имя
    неоднозначно, но граф «кто наследует от TestCase» работает."""
    ext = os.path.splitext(rel_path)[1].lower()
    if ext in _JS_EXTS:
        return _ts_inherits(rel_path, content)
    if not rel_path.endswith(".py"):
        return []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    edges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for b in node.bases:
                if isinstance(b, ast.Name):
                    edges.append((node.name, b.id, node.lineno))
                elif isinstance(b, ast.Attribute):
                    edges.append((node.name, b.attr, node.lineno))
    return edges


def extract_errors(rel_path, content):
    """Синтаксические ошибки: .py — ast; .js/.ts — tree-sitter; .sh —
    tree-sitter-bash. Файл, который не парсится, — диагностика для поиска,
    а не молчаливый пропуск (раньше SyntaxError просто давал пустой список)."""
    ext = os.path.splitext(rel_path)[1].lower()
    if ext in _JS_EXTS:
        return _ts_errors(rel_path, content)
    if ext in _SH_EXTS:
        return _ts_bash_errors(rel_path, content)
    if not rel_path.endswith(".py"):
        return []
    try:
        ast.parse(content)
    except SyntaxError as e:
        return [(e.lineno or 0, e.msg)]
    return []

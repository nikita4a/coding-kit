import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from task_runner import (
    ERROR_CLASSES,
    classify_error,
    resolve_cmd,
    run_task_suite,
)


def test_task_runner_discovers_tasks():
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "task_runner.py"), "--dry-run"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr
    assert "3 tasks discovered" in r.stdout or "3 tasks" in r.stdout


def test_verify_rejects_pristine_fixture(tmp_path):
    # pristine fixture fails for all 3 tasks
    for task in ("001-fix-div-zero", "002-add-validation", "003-regression-guard"):
        sandbox = tmp_path / task
        shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sandbox)
        v = ROOT / "eval" / "tasks" / task / "verify.py"
        r = subprocess.run(
            [sys.executable, str(v), str(sandbox)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert r.returncode == 1, f"{task} verify must reject pristine fixture: {r.stdout} {r.stderr}"


def test_verify_accepts_fixed_fixture(tmp_path):
    # Task 001 reference fix
    sandbox_001 = tmp_path / "fixed_001"
    shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sandbox_001)
    (sandbox_001 / "calc.py").write_text(
        (sandbox_001 / "calc.py").read_text(encoding="utf-8").replace(
            "    return a / b",
            '    if b == 0:\n        raise ValueError("division by zero")\n    return a / b',
        ),
        encoding="utf-8",
        newline="\n",
    )
    tests_001 = (sandbox_001 / "test_calc.py").read_text(encoding="utf-8")
    tests_001 += "\n\ndef test_divide_by_zero():\n    import pytest\n    with pytest.raises(ValueError):\n        divide(1, 0)\n"
    (sandbox_001 / "test_calc.py").write_text(tests_001, encoding="utf-8", newline="\n")
    v1 = ROOT / "eval" / "tasks" / "001-fix-div-zero" / "verify.py"
    r1 = subprocess.run(
        [sys.executable, str(v1), str(sandbox_001)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r1.returncode == 0, r1.stdout + r1.stderr

    # Task 002 reference fix
    sandbox_002 = tmp_path / "fixed_002"
    shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sandbox_002)
    (sandbox_002 / "calc.py").write_text(
        (sandbox_002 / "calc.py").read_text(encoding="utf-8").replace(
            "def parse_int(s):\n    return int(s)",
            'def parse_int(s):\n    s = str(s).strip()\n    try:\n        return int(s)\n    except ValueError:\n        raise ValueError(f"not an integer: {s}")',
        ),
        encoding="utf-8",
        newline="\n",
    )
    tests_002 = (sandbox_002 / "test_calc.py").read_text(encoding="utf-8")
    tests_002 += '\n\ndef test_parse_int_whitespace():\n    assert parse_int(" 42 ") == 42\n    assert parse_int("\\t7\\n") == 7\n\ndef test_parse_int_non_numeric():\n    import pytest\n    with pytest.raises(ValueError, match="not an integer"):\n        parse_int("abc")\n'
    (sandbox_002 / "test_calc.py").write_text(tests_002, encoding="utf-8", newline="\n")
    v2 = ROOT / "eval" / "tasks" / "002-add-validation" / "verify.py"
    r2 = subprocess.run(
        [sys.executable, str(v2), str(sandbox_002)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr

    # Task 003 reference fix
    sandbox_003 = tmp_path / "fixed_003"
    shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sandbox_003)
    (sandbox_003 / "calc.py").write_text(
        (sandbox_003 / "calc.py").read_text(encoding="utf-8").replace(
            "def clamp(v, lo, hi):\n    if lo > v < hi:\n        return hi\n    return v",
            "def clamp(v, lo, hi):\n    if v < lo:\n        return lo\n    if v > hi:\n        return hi\n    return v",
        ),
        encoding="utf-8",
        newline="\n",
    )
    tests_003 = (sandbox_003 / "test_calc.py").read_text(encoding="utf-8")
    tests_003 += "\n\ndef test_clamp_bounds():\n    assert clamp(-5, 0, 10) == 0\n    assert clamp(15, 0, 10) == 10\n"
    (sandbox_003 / "test_calc.py").write_text(tests_003, encoding="utf-8", newline="\n")
    v3 = ROOT / "eval" / "tasks" / "003-regression-guard" / "verify.py"
    r3 = subprocess.run(
        [sys.executable, str(v3), str(sandbox_003)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r3.returncode == 0, r3.stdout + r3.stderr


def test_verify_rejects_pass_stubs_and_missing_tests(tmp_path):
    # Fix calc.py for all 3 tasks, but test_calc.py has either pass stub or no new tests
    # 1. Pass stub on 001
    sb1 = tmp_path / "stub_001"
    shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sb1)
    (sb1 / "calc.py").write_text(
        (sb1 / "calc.py").read_text(encoding="utf-8").replace(
            "    return a / b",
            '    if b == 0:\n        raise ValueError("division by zero")\n    return a / b',
        ),
        encoding="utf-8",
    )
    (sb1 / "test_calc.py").write_text(
        (sb1 / "test_calc.py").read_text(encoding="utf-8") + "\n\ndef test_stub():\n    pass\n",
        encoding="utf-8",
    )
    r = subprocess.run([sys.executable, str(ROOT / "eval" / "tasks" / "001-fix-div-zero" / "verify.py"), str(sb1)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 1, "Pass stub on 001 must fail verify"

    # 2. Fix without test on 002
    sb2 = tmp_path / "fix_only_002"
    shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sb2)
    (sb2 / "calc.py").write_text(
        (sb2 / "calc.py").read_text(encoding="utf-8").replace(
            "def parse_int(s):\n    return int(s)",
            'def parse_int(s):\n    s = str(s).strip()\n    try:\n        return int(s)\n    except ValueError:\n        raise ValueError(f"not an integer: {s}")',
        ),
        encoding="utf-8",
    )
    r = subprocess.run([sys.executable, str(ROOT / "eval" / "tasks" / "002-add-validation" / "verify.py"), str(sb2)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 1, "Fix without test on 002 must fail verify"

    # 3. Unrelated extra test on 003
    sb3 = tmp_path / "unrelated_003"
    shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sb3)
    (sb3 / "calc.py").write_text(
        (sb3 / "calc.py").read_text(encoding="utf-8").replace(
            "def clamp(v, lo, hi):\n    if lo > v < hi:\n        return hi\n    return v",
            "def clamp(v, lo, hi):\n    if v < lo:\n        return lo\n    if v > hi:\n        return hi\n    return v",
        ),
        encoding="utf-8",
    )
    (sb3 / "test_calc.py").write_text(
        (sb3 / "test_calc.py").read_text(encoding="utf-8") + "\n\ndef test_unrelated():\n    assert 1 == 1\n",
        encoding="utf-8",
    )
    r = subprocess.run([sys.executable, str(ROOT / "eval" / "tasks" / "003-regression-guard" / "verify.py"), str(sb3)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 1, "Unrelated extra test on 003 must fail verify"


def test_verify_rejects_wrong_regression_target(tmp_path):
    # In task 001, candidate fixes divide and also fixes clamp, but adds regression test for clamp only
    sb = tmp_path / "wrong_target_001"
    shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sb)
    cand_calc = (
        'def divide(a, b):\n'
        '    if b == 0:\n'
        '        raise ValueError("division by zero")\n'
        '    return a / b\n\n'
        'def parse_int(s):\n'
        '    return int(s)\n\n'
        'def clamp(v, lo, hi):\n'
        '    if v < lo:\n'
        '        return lo\n'
        '    if v > hi:\n'
        '        return hi\n'
        '    return v\n'
    )
    (sb / "calc.py").write_text(cand_calc, encoding="utf-8")
    tests = (sb / "test_calc.py").read_text(encoding="utf-8")
    tests += "\n\ndef test_clamp_fixed():\n    assert clamp(-5, 0, 10) == 0\n"
    (sb / "test_calc.py").write_text(tests, encoding="utf-8")

    r = subprocess.run([sys.executable, str(ROOT / "eval" / "tasks" / "001-fix-div-zero" / "verify.py"), str(sb)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 1, "Testing wrong function must fail verify (caught by revert step)"

def test_zero_tasks_returns_1_and_no_zero_division(tmp_path):
    # rc 1 on zero tasks in dry-run and live
    rc_dry = run_task_suite([], None, dry_run=True)
    assert rc_dry == 1

    rc_live = run_task_suite([], "dummy-executor")
    assert rc_live == 1

    # with json_out, saves payload with 0 metrics and no division by zero
    out_file = tmp_path / "zero.json"
    rc_json = run_task_suite([], "dummy-executor", json_out=out_file, model="zero-model")
    assert rc_json == 1
    assert out_file.is_file()

    doc = json.loads(out_file.read_text(encoding="utf-8"))
    assert doc["total"] == 0
    assert doc["passed"] == 0
    assert doc["pass_rate"] == 0.0
    assert doc["pass@1"] == 0.0
    assert doc["pass@2"] == 0.0
    assert doc["rows"] == []


def test_dry_run_no_subprocess_and_persistence(tmp_path):
    # dry run without json persists nothing
    out_dir = tmp_path / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = run_task_suite(["001-fix-div-zero"], None, dry_run=True)
    assert rc == 0
    assert list(out_dir.glob("*.json")) == []

    # dry run with explicit json_out creates result doc
    explicit_json = tmp_path / "dry_out.json"
    rc_json = run_task_suite(
        ["001-fix-div-zero"],
        None,
        dry_run=True,
        json_out=explicit_json,
    )
    assert rc == 0
    assert explicit_json.is_file()
    doc = json.loads(explicit_json.read_text(encoding="utf-8"))
    assert doc["kind"] == "tasks"
    assert doc["total"] == 1
    assert doc["passed"] == 0
    assert doc["rows"][0]["verdict"] == "DRY_RUN"


def test_fresh_sandboxes_on_retry(tmp_path):
    # State tracking file to record each attempt
    state_file = tmp_path / "attempts.txt"
    state_file.write_text("0", encoding="utf-8")

    # Script: on try 1, drops a poison file and exits 1.
    # On try 2, checks that poison file does NOT exist (pristine fixture), then fixes calc.py and exits 0.
    fix_code = (
        'import sys, pathlib\n'
        'state_p = pathlib.Path(sys.argv[1])\n'
        'cur = int(state_p.read_text(encoding="utf-8")) + 1\n'
        'state_p.write_text(str(cur), encoding="utf-8")\n'
        'poison = pathlib.Path("poison.marker")\n'
        'if cur == 1:\n'
        '    poison.write_text("polluted", encoding="utf-8")\n'
        '    sys.exit(1)\n'
        'if poison.exists():\n'
        '    sys.exit(2)\n'
        'calc_p = pathlib.Path("calc.py")\n'
        'calc_p.write_text(calc_p.read_text(encoding="utf-8").replace("return a / b", "if b == 0:\\n        raise ValueError(\\"division by zero\\")\\n    return a / b"), encoding="utf-8")\n'
        'test_p = pathlib.Path("test_calc.py")\n'
        'test_p.write_text(test_p.read_text(encoding="utf-8") + "\\ndef test_divide_by_zero():\\n    import pytest\\n    with pytest.raises(ValueError):\\n        divide(1, 0)\\n", encoding="utf-8")\n'
        'sys.exit(0)\n'
    )
    script_path = tmp_path / "executor.py"
    script_path.write_text(fix_code, encoding="utf-8")

    executor_cmd = f"{sys.executable} {script_path} {state_file}"
    json_path = tmp_path / "retry_result.json"

    rc = run_task_suite(
        ["001-fix-div-zero"],
        executor_cmd=executor_cmd,
        tries=2,
        json_out=json_path,
        model="retry-model",
    )
    assert rc == 0
    assert int(state_file.read_text(encoding="utf-8")) == 2

    doc = json.loads(json_path.read_text(encoding="utf-8"))
    assert doc["passed"] == 1
    assert doc["total"] == 1
    assert doc["pass@1"] == 0.0
    assert doc["pass@2"] == 1.0
    row = doc["rows"][0]
    assert row["verdict"] == "PASS"
    assert len(row["attempts"]) == 2
    assert row["attempts"][0]["verdict"] == "FAIL"
    assert row["attempts"][1]["verdict"] == "PASS"


def test_early_stop_on_first_pass(tmp_path):
    state_file = tmp_path / "calls.txt"
    state_file.write_text("0", encoding="utf-8")

    fix_code = (
        'import sys, pathlib\n'
        'state_p = pathlib.Path(sys.argv[1])\n'
        'cur = int(state_p.read_text(encoding="utf-8")) + 1\n'
        'state_p.write_text(str(cur), encoding="utf-8")\n'
        'calc_p = pathlib.Path("calc.py")\n'
        'calc_p.write_text(calc_p.read_text(encoding="utf-8").replace("return a / b", "if b == 0:\\n        raise ValueError(\\"division by zero\\")\\n    return a / b"), encoding="utf-8")\n'
        'test_p = pathlib.Path("test_calc.py")\n'
        'test_p.write_text(test_p.read_text(encoding="utf-8") + "\\ndef test_divide_by_zero():\\n    import pytest\\n    with pytest.raises(ValueError):\\n        divide(1, 0)\\n", encoding="utf-8")\n'
        'sys.exit(0)\n'
    )
    script_path = tmp_path / "fix_immediately.py"
    script_path.write_text(fix_code, encoding="utf-8")

    executor_cmd = f"{sys.executable} {script_path} {state_file}"
    json_path = tmp_path / "early_stop.json"
    rc = run_task_suite(
        ["001-fix-div-zero"],
        executor_cmd=executor_cmd,
        tries=5,
        json_out=json_path,
        model="early-model",
    )
    assert rc == 0
    # Stopped after first try; did not run tries 2..5
    assert int(state_file.read_text(encoding="utf-8")) == 1

    doc = json.loads(json_path.read_text(encoding="utf-8"))
    assert doc["pass@1"] == 1.0
    assert doc["pass@2"] == 1.0
    assert len(doc["rows"][0]["attempts"]) == 1


def test_error_classes_and_nonzero_skips_verifier(tmp_path):
    # Verify the 6 error classes
    assert classify_error(timed_out=True) == "test_timeout"
    assert classify_error(error_text="Subprocess timed out") == "test_timeout"
    assert classify_error(stderr="context_length_exceeded: maximum context length is 8192") == "exhausted_context"
    assert classify_error(stdout="Could you please clarify what tests are needed?") == "user_asks"
    assert classify_error(stderr="SyntaxError: invalid syntax in calc.py line 3") == "syntax_error"
    assert classify_error(returncode=1, stdout="", stderr="") == "malformed_response"
    assert classify_error(stderr="AssertionError: assert 1 == 2") == "other"

    for cls_name in (
        "syntax_error",
        "test_timeout",
        "malformed_response",
        "exhausted_context",
        "user_asks",
        "other",
    ):
        assert cls_name in ERROR_CLASSES

    # Nonzero executor returncode skips running verifier
    fail_script = tmp_path / "fail_executor.py"
    fail_script.write_text(
        'import sys\nsys.stderr.write("context limit exceeded")\nsys.exit(3)\n',
        encoding="utf-8",
    )
    json_path = tmp_path / "err_res.json"
    rc = run_task_suite(
        ["001-fix-div-zero"],
        executor_cmd=f"{sys.executable} {fail_script}",
        tries=1,
        json_out=json_path,
        model="err-model",
    )
    assert rc == 1
    doc = json.loads(json_path.read_text(encoding="utf-8"))
    row = doc["rows"][0]
    assert row["verdict"] == "FAIL"
    assert row["attempts"][0]["error_class"] == "exhausted_context"
    assert "trace_tail" in row["attempts"][0]


def test_model_and_executor_separation(tmp_path):
    dry_json = tmp_path / "model_sep.json"
    run_task_suite(
        ["001-fix-div-zero"],
        executor_cmd="python -m custom_exec --arg 1",
        tries=1,
        model="claude-3-7-sonnet",
        dry_run=True,
        json_out=dry_json,
    )
    doc = json.loads(dry_json.read_text(encoding="utf-8"))
    assert doc["model"] == "claude-3-7-sonnet"
    assert doc["executor_name"] == "python"

    # When model is omitted / None -> unspecified
    unspec_json = tmp_path / "model_unspec.json"
    run_task_suite(
        ["001-fix-div-zero"],
        executor_cmd="claude -p -",
        tries=1,
        model=None,
        dry_run=True,
        json_out=unspec_json,
    )
    doc_unspec = json.loads(unspec_json.read_text(encoding="utf-8"))
    assert doc_unspec["model"] == "unspecified"
    assert doc_unspec["executor_name"] == "claude"


def test_task_runner_resolve_cmd_windows_paths(monkeypatch):
    import task_runner

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        task_runner.shutil,
        "which",
        lambda x: r"C:\Users\test\AppData\npm\claude.cmd" if x == "claude" else None,
    )

    # Empty / whitespace
    assert resolve_cmd("") == []
    assert resolve_cmd("   ") == []

    # Unquoted backslash path to exe
    assert resolve_cmd(r"C:\tools\agent.exe --flag") == [r"C:\tools\agent.exe", "--flag"]

    # Quoted path with spaces to exe
    cmd_exe = resolve_cmd(r'"C:\Program Files\My Agent\agent.exe" --model gpt-4')
    assert cmd_exe == [r"C:\Program Files\My Agent\agent.exe", "--model", "gpt-4"]

    # Quoted path with spaces to .cmd -> cmd /c with quotes removed
    cmd_batch = resolve_cmd(r'"C:\Program Files\npm\claude.cmd" run --arg "val with space"')
    assert cmd_batch == ["cmd", "/c", r"C:\Program Files\npm\claude.cmd", "run", "--arg", "val with space"]

    # Unquoted .bat
    assert resolve_cmd(r"C:\bin\agent.bat --flag") == ["cmd", "/c", r"C:\bin\agent.bat", "--flag"]

    # Single-quoted path with spaces to .bat
    assert resolve_cmd(r"'C:\Program Files\tool.bat' arg") == ["cmd", "/c", r"C:\Program Files\tool.bat", "arg"]

    # Command resolved via which to .cmd
    assert resolve_cmd("claude --flag") == ["cmd", "/c", r"C:\Users\test\AppData\npm\claude.cmd", "--flag"]


def test_task_executor_uses_secret_free_environment(monkeypatch):
    import task_runner

    monkeypatch.setenv("PATH", r"C:\safe-bin")
    monkeypatch.setenv("GITHUB_TOKEN", "github-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    env = task_runner.executor_env()

    assert env["PATH"] == r"C:\safe-bin"
    assert "GITHUB_TOKEN" not in env
    assert "OPENAI_API_KEY" not in env


def test_executor_launch_error_records_truthful_fail(tmp_path):
    # A nonexistent executor raises OSError/FileNotFoundError at launch. The
    # runner must record a truthful FAIL (error_class=other, bounded trace),
    # honor tries, continue across tasks, and persist the requested result.
    json_path = tmp_path / "oserror.json"
    rc = run_task_suite(
        ["001-fix-div-zero", "002-add-validation"],
        executor_cmd="definitely-not-a-real-executable-xyz",
        tries=2,
        json_out=json_path,
        model="failing-model",
    )
    assert rc == 1
    doc = json.loads(json_path.read_text(encoding="utf-8"))
    assert doc["kind"] == "tasks"
    assert doc["total"] == 2
    assert doc["passed"] == 0
    assert len(doc["rows"]) == 2
    for row in doc["rows"]:
        assert row["verdict"] == "FAIL"
        assert len(row["attempts"]) == 2
        for attempt in row["attempts"]:
            assert attempt["verdict"] == "FAIL"
            assert attempt["error_class"] == "other"
            assert "trace_tail" in attempt


def test_run_task_suite_rejects_live_persistence_without_model(tmp_path):
    json_path = tmp_path / "nomodel.json"
    try:
        run_task_suite(
            ["001-fix-div-zero"],
            executor_cmd="python -m custom_exec",
            json_out=json_path,
            model=None,
        )
    except ValueError as exc:
        assert "model" in str(exc)
    else:
        raise AssertionError("live persistence without --model must raise ValueError")
    assert not json_path.exists()

    # dry-run with json and no model remains permitted (unspecified)
    dry_json = tmp_path / "dry.json"
    rc = run_task_suite(["001-fix-div-zero"], None, dry_run=True, json_out=dry_json)
    assert rc == 0
    assert json.loads(dry_json.read_text(encoding="utf-8"))["model"] == "unspecified"


def test_cli_rejects_live_json_without_model(tmp_path):
    out_json = tmp_path / "cli.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "task_runner.py"),
         "--executor", "claude -p", "--json", str(out_json)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 2
    assert "--model" in r.stderr
    assert not out_json.exists()


def test_verify_rejects_malicious_conftest_bypass(tmp_path):
    # A candidate that fixes calc.py but adds no regression test can, if the
    # oracle copies the whole sandbox and honors plugin autoload, plant a
    # conftest.py that manufactures "tests fail on pristine/reverted" via a
    # pytest startup hook. The hardened oracles copy only test_calc.py and
    # run --noconftest, so every task must reject this bypass with rc 1.
    fixed_calc = {
        "001-fix-div-zero": (
            'def divide(a, b):\n'
            '    if b == 0:\n'
            '        raise ValueError("division by zero")\n'
            '    return a / b\n\n'
            'def parse_int(s):\n'
            '    return int(s)\n\n'
            'def clamp(v, lo, hi):\n'
            '    if lo > v < hi:\n'
            '        return hi\n'
            '    return v\n'
        ),
        "002-add-validation": (
            'def divide(a, b):\n'
            '    return a / b\n\n'
            'def parse_int(s):\n'
            '    s = str(s).strip()\n'
            '    try:\n'
            '        return int(s)\n'
            '    except ValueError:\n'
            '        raise ValueError(f"not an integer: {s}")\n\n'
            'def clamp(v, lo, hi):\n'
            '    if lo > v < hi:\n'
            '        return hi\n'
            '    return v\n'
        ),
        "003-regression-guard": (
            'def divide(a, b):\n'
            '    return a / b\n\n'
            'def parse_int(s):\n'
            '    return int(s)\n\n'
            'def clamp(v, lo, hi):\n'
            '    if v < lo:\n'
            '        return lo\n'
            '    if v > hi:\n'
            '        return hi\n'
            '    return v\n'
        ),
    }
    evil_conftest = {
        "001-fix-div-zero": (
            'import importlib.util\n'
            'from pathlib import Path\n\n\n'
            'def pytest_configure(config):\n'
            '    calc = Path(__file__).resolve().parent / "calc.py"\n'
            '    spec = importlib.util.spec_from_file_location("calc", str(calc))\n'
            '    mod = importlib.util.module_from_spec(spec)\n'
            '    spec.loader.exec_module(mod)\n'
            '    try:\n'
            '        mod.divide(1, 0)\n'
            '    except ZeroDivisionError:\n'
            '        raise RuntimeError("manufactured failure: divide not fixed")\n'
            '    except ValueError:\n'
            '        pass\n'
        ),
        "002-add-validation": (
            'import importlib.util\n'
            'from pathlib import Path\n\n\n'
            'def pytest_configure(config):\n'
            '    calc = Path(__file__).resolve().parent / "calc.py"\n'
            '    spec = importlib.util.spec_from_file_location("calc", str(calc))\n'
            '    mod = importlib.util.module_from_spec(spec)\n'
            '    spec.loader.exec_module(mod)\n'
            '    try:\n'
            '        mod.parse_int("abc")\n'
            '    except ValueError as e:\n'
            '        if "not an integer" not in str(e):\n'
            '            raise RuntimeError("manufactured failure: parse_int not fixed")\n'
        ),
        "003-regression-guard": (
            'import importlib.util\n'
            'from pathlib import Path\n\n\n'
            'def pytest_configure(config):\n'
            '    calc = Path(__file__).resolve().parent / "calc.py"\n'
            '    spec = importlib.util.spec_from_file_location("calc", str(calc))\n'
            '    mod = importlib.util.module_from_spec(spec)\n'
            '    spec.loader.exec_module(mod)\n'
            '    if mod.clamp(-5, 0, 10) != 0:\n'
            '        raise RuntimeError("manufactured failure: clamp not fixed")\n'
        ),
    }

    for task, code in fixed_calc.items():
        sb = tmp_path / ("evil_" + task)
        shutil.copytree(ROOT / "eval" / "tasks" / "repo-fixture", sb)
        (sb / "calc.py").write_text(code, encoding="utf-8", newline="\n")
        (sb / "conftest.py").write_text(evil_conftest[task], encoding="utf-8", newline="\n")
        v = ROOT / "eval" / "tasks" / task / "verify.py"
        r = subprocess.run(
            [sys.executable, str(v), str(sb)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert r.returncode == 1, f"{task} must reject malicious conftest bypass: {r.stdout} {r.stderr}"

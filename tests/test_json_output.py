import json
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
import runner


def test_runner_dry_run_json(tmp_path):
    out = tmp_path / "r.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "runner.py"), "--json", str(out)],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["kind"] == "trap" and data["total"] >= 18
    assert data["passed"] == data["total"]  # dry-run: all scenarios valid
    assert data["schema_version"] == 1
    assert data["model"] == "unspecified"
    assert data["mode"] == "dry-run"
    assert data["duration_s_total"] == 0.0
    assert data["duration_s_mean"] == 0.0
    assert "reported_usage" not in data


def test_runner_live_json_persists_duration_and_reported_usage(tmp_path, monkeypatch):
    out_json = tmp_path / "live_usage.json"
    sc_file = tmp_path / "sc_usage.md"
    sc_file.write_text(
        "name: sc1\nskill: s1\ntrap: t1\nexpect: pass\n\nagent prompt body",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "run_prompt", lambda cmd, prompt, timeout=600: "answer")
    monkeypatch.setattr(runner, "judge_one", lambda cmd, exp, ans, timeout=600: "PASS")

    code = runner.run_scenarios(
        executor=["mock_exe"],
        judge=["mock_judge"],
        scenario_files=[sc_file],
        repeat=1,
        json_out=out_json,
        model="model-usage",
        reported_usage={"tokens_total": 123, "cost_usd": 0.42},
    )
    assert code == 0
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["reported_usage"] == {"tokens_total": 123, "cost_usd": 0.42}
    assert doc["duration_s_total"] >= 0
    assert doc["duration_s_mean"] >= 0
    assert doc["duration_s_total"] == doc["duration_s_mean"]


def test_runner_dry_run_never_attaches_reported_usage(tmp_path):
    sc_file = tmp_path / "sc_dry.md"
    sc_file.write_text(
        "name: d\nskill: s\ntrap: t\nexpect: pass\n\nbody",
        encoding="utf-8",
    )
    out_json = tmp_path / "dry_usage.json"
    code = runner.run_scenarios(
        executor=None,
        judge=None,
        scenario_files=[sc_file],
        json_out=out_json,
        reported_usage={"tokens_total": 1, "cost_usd": 0.5},
    )
    assert code == 0
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["mode"] == "dry-run"
    assert doc["duration_s_total"] == 0.0
    assert doc["duration_s_mean"] == 0.0
    assert "reported_usage" not in doc

def test_trigger_dry_run_json(tmp_path):
    out = tmp_path / "t.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "trigger_eval.py"),
         "--queries", str(ROOT / "eval" / "trigger_queries.json"),
         "--json", str(out)],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["kind"] == "trigger" and data["total"] == 80
    assert data["mode"] == "dry-run"


def test_auto_json_writes_shared_store(tmp_path, monkeypatch):
    # --json auto must land in eval/results with a timestamped name;
    # patch RESULTS_DIR via a temp copy is impossible cross-process,
    # so assert the file appears in the real store and clean up.
    before = set((ROOT / "eval" / "results").glob("*.json"))
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "runner.py"), "--json", "auto"],
        capture_output=True, text=True, encoding="utf-8")
    after = set((ROOT / "eval" / "results").glob("*.json"))
    new = set(after - before)
    try:
        assert r.returncode == 0, r.stderr
        assert len(new) == 1
        target = next(iter(new))
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["kind"] == "trap"
    finally:
        for p in new:
            p.unlink(missing_ok=True)


def test_runner_records_judge_fail_and_trace_tail(tmp_path, monkeypatch):
    out_json = tmp_path / "judge_fail.json"
    sc_file = tmp_path / "sc1.md"
    sc_file.write_text(
        "name: sc1\nskill: s1\ntrap: t1\nexpect: pass\n\nagent prompt body",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "run_prompt", lambda cmd, prompt, timeout=600: "agent answer text here")
    monkeypatch.setattr(runner, "judge_one", lambda cmd, exp, ans, timeout=600: "FAIL: agent hallucinated output")

    code = runner.run_scenarios(
        executor=["mock_exe"],
        judge=["mock_judge"],
        scenario_files=[sc_file],
        repeat=1,
        json_out=out_json,
        model="model-fail",
        executor_spec="mock_exe --api-key SECRET999",
    )
    assert code == 1
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["schema_version"] == 1
    assert doc["kind"] == "trap"
    assert doc["model"] == "model-fail"
    assert doc["executor_name"] == "mock_exe"
    assert "SECRET999" not in json.dumps(doc)
    assert doc["passed"] == 0
    assert doc["total"] == 1
    sc = doc["scenarios"][0]
    assert sc["name"] == "sc1"
    assert sc["verdict"] == "FAIL"
    assert len(sc["attempts"]) == 1
    att = sc["attempts"][0]
    assert att["verdict"] == "FAIL"
    assert att["duration_s"] >= 0
    assert "FAIL: agent hallucinated" in att["error"]
    assert att["trace_tail"] == "agent answer text here"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("PASS", True),
        ("PASS: reason", True),
        ("PASS - reason", True),
        ("pass: ok", True),
        ("PASS\nreason continues", True),
        ("PASSING", False),
        ("PASSENGER", False),
        ("PASSIVE", False),
        ("the answer passes", False),
        ("FAIL", False),
        ("FAIL: wrong answer", False),
        ("", False),
        ("   ", False),
        ("\n\n", False),
        ("PASS. with period", False),
    ],
)
def test_judge_passed_strict_parser(text, expected):
    assert runner.judge_passed(text) is expected


def test_runner_persists_malformed_judge_output_as_fail(tmp_path, monkeypatch):
    out_json = tmp_path / "malformed_judge.json"
    sc_file = tmp_path / "sc_malformed.md"
    sc_file.write_text(
        "name: sc_malformed\nskill: s\ntrap: t\nexpect: pass\n\nagent prompt body",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runner, "run_prompt", lambda cmd, prompt, timeout=600: "agent answer text here"
    )
    monkeypatch.setattr(
        runner, "judge_one", lambda cmd, exp, ans, timeout=600: "PASSING: looks right"
    )

    code = runner.run_scenarios(
        executor=["mock_exe"],
        judge=["mock_judge"],
        scenario_files=[sc_file],
        repeat=1,
        json_out=out_json,
        model="model-malformed",
    )
    assert code == 1
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["passed"] == 0
    sc = doc["scenarios"][0]
    assert sc["verdict"] == "FAIL"
    assert sc["attempts"][0]["verdict"] == "FAIL"


def test_runner_records_executor_exception_and_writes_json(tmp_path, monkeypatch):
    out_json = tmp_path / "exec_exc.json"
    sc_file = tmp_path / "sc2.md"
    sc_file.write_text(
        "name: sc2\nskill: s2\ntrap: t2\nexpect: pass\n\nbody text",
        encoding="utf-8",
    )

    def _broken_exec(*args, **kwargs):
        raise RuntimeError("Subprocess died unexpectedly")

    monkeypatch.setattr(runner, "run_prompt", _broken_exec)

    code = runner.run_scenarios(
        executor=["mock_exe"],
        judge=["mock_judge"],
        scenario_files=[sc_file],
        repeat=1,
        json_out=out_json,
        model="model-crash",
        executor_spec="mock_exe",
    )
    assert code == 1
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["schema_version"] == 1
    assert doc["kind"] == "trap"
    assert doc["passed"] == 0
    assert doc["total"] == 1
    sc = doc["scenarios"][0]
    assert sc["verdict"] == "FAIL"
    assert len(sc["attempts"]) == 1
    att = sc["attempts"][0]
    assert att["verdict"] == "FAIL"
    assert "Subprocess died unexpectedly" in att["error"]


def test_runner_all_repeat_semantics(tmp_path, monkeypatch):
    out_json = tmp_path / "repeat_flake.json"
    sc_file = tmp_path / "sc3.md"
    sc_file.write_text(
        "name: sc3\nskill: s3\ntrap: t3\nexpect: pass\n\nrepeat body",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "run_prompt", lambda cmd, prompt, timeout=600: "agent reply")

    judge_responses = iter(["PASS: attempt 1 good", "FAIL: attempt 2 flaky bug", "PASS: attempt 3 good"])
    monkeypatch.setattr(runner, "judge_one", lambda cmd, exp, ans, timeout=600: next(judge_responses))

    code = runner.run_scenarios(
        executor=["mock_exe"],
        judge=["mock_judge"],
        scenario_files=[sc_file],
        repeat=3,
        json_out=out_json,
        model="model-repeat",
    )
    assert code == 1
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["passed"] == 0
    sc = doc["scenarios"][0]
    assert sc["verdict"] == "FAIL"
    assert len(sc["attempts"]) == 3
    assert sc["attempts"][0]["verdict"] == "PASS"
    assert sc["attempts"][1]["verdict"] == "FAIL"
    assert "flaky bug" in sc["attempts"][1]["error"]
    assert sc["attempts"][2]["verdict"] == "PASS"


def test_runner_all_repeat_success(tmp_path, monkeypatch):
    out_json = tmp_path / "repeat_success.json"
    sc_file = tmp_path / "sc4.md"
    sc_file.write_text(
        "name: sc4\nskill: s4\ntrap: t4\nexpect: pass\n\nrepeat body",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "run_prompt", lambda cmd, prompt, timeout=600: "agent reply")
    monkeypatch.setattr(runner, "judge_one", lambda cmd, exp, ans, timeout=600: "PASS: all good")

    code = runner.run_scenarios(
        executor=["mock_exe"],
        judge=["mock_judge"],
        scenario_files=[sc_file],
        repeat=2,
        json_out=out_json,
        model="model-repeat-ok",
    )
    assert code == 0
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["passed"] == 1
    sc = doc["scenarios"][0]
    assert sc["verdict"] == "PASS"
    assert len(sc["attempts"]) == 2
    assert all(a["verdict"] == "PASS" for a in sc["attempts"])


def test_runner_model_executor_separation(tmp_path, monkeypatch):
    out_json = tmp_path / "separation.json"
    sc_file = tmp_path / "sc5.md"
    sc_file.write_text(
        "name: sc5\nskill: s5\ntrap: t5\nexpect: pass\n\nbody",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "run_prompt", lambda cmd, prompt, timeout=600: "agent reply")
    monkeypatch.setattr(runner, "judge_one", lambda cmd, exp, ans, timeout=600: "PASS: ok")

    code = runner.run_scenarios(
        executor=["custom-cli", "--auth=TOKEN123"],
        judge=["custom-cli", "--auth=TOKEN123"],
        scenario_files=[sc_file],
        repeat=1,
        json_out=out_json,
        model="gpt-4o",
        executor_spec="custom-cli --auth=TOKEN123",
    )
    assert code == 0
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["model"] == "gpt-4o"
    assert doc["executor_name"] == "custom-cli"
    assert "TOKEN123" not in json.dumps(doc)


def test_runner_no_json_does_not_persist(tmp_path, monkeypatch):
    sc_file = tmp_path / "sc6.md"
    sc_file.write_text(
        "name: sc6\nskill: s6\ntrap: t6\nexpect: pass\n\nbody",
        encoding="utf-8",
    )
    saved = []
    monkeypatch.setattr(runner, "save_result", lambda *args, **kwargs: saved.append(args))
    code = runner.run_scenarios(
        executor=None,
        judge=None,
        scenario_files=[sc_file],
        repeat=1,
        json_out=None,
    )
    assert code == 0
    assert len(saved) == 0


def test_runner_passes_timeout_to_executor_and_judge(tmp_path, monkeypatch):
    sc_file = tmp_path / "sc_to.md"
    sc_file.write_text(
        "name: sc_to\nskill: s_to\ntrap: t_to\nexpect: pass\n\nbody",
        encoding="utf-8",
    )
    seen_timeouts = []

    def fake_run_prompt(cmd, prompt, timeout=600):
        seen_timeouts.append(timeout)
        if "EXPECT:" in prompt:
            return "PASS: good"
        return "agent output"

    monkeypatch.setattr(runner, "run_prompt", fake_run_prompt)
    code = runner.run_scenarios(
        executor=["mock_exe"],
        judge=["mock_judge"],
        scenario_files=[sc_file],
        repeat=1,
        timeout=45,
    )
    assert code == 0
    assert seen_timeouts == [45, 45]


def test_runner_timeout_expired_records_trace_tail(tmp_path, monkeypatch):
    out_json = tmp_path / "timeout_tail.json"
    sc_file = tmp_path / "sc_tt.md"
    sc_file.write_text(
        "name: sc_tt\nskill: s_tt\ntrap: t_tt\nexpect: pass\n\nbody",
        encoding="utf-8",
    )

    def _timing_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 600), stderr="partial agent error tail")

    monkeypatch.setattr(runner, "run_prompt", _timing_out)
    code = runner.run_scenarios(
        executor=["mock_exe"],
        judge=["mock_judge"],
        scenario_files=[sc_file],
        repeat=1,
        json_out=out_json,
        timeout=30,
        model="timeout-model",
    )
    assert code == 1
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    sc = doc["scenarios"][0]
    assert sc["verdict"] == "FAIL"
    att = sc["attempts"][0]
    assert att["verdict"] == "FAIL"
    assert "TimeoutExpired" in att["error"]
    assert att["trace_tail"] == "partial agent error tail"


def test_runner_dry_run_cli_no_json_does_not_create_files(tmp_path):
    results_dir = ROOT / "eval" / "results"
    before = set(results_dir.glob("*.json")) if results_dir.exists() else set()
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "runner.py")],
        capture_output=True, text=True, encoding="utf-8",
    )
    after = set(results_dir.glob("*.json")) if results_dir.exists() else set()
    new = after - before
    try:
        assert r.returncode == 0, r.stderr
        assert len(new) == 0
    finally:
        for p in new:
            p.unlink(missing_ok=True)


def test_trigger_dry_run_cli_no_json_does_not_create_files(tmp_path):
    results_dir = ROOT / "eval" / "results"
    before = set(results_dir.glob("*.json")) if results_dir.exists() else set()
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "trigger_eval.py"),
         "--queries", str(ROOT / "eval" / "trigger_queries.json")],
        capture_output=True, text=True, encoding="utf-8",
    )
    after = set(results_dir.glob("*.json")) if results_dir.exists() else set()
    new = after - before
    try:
        assert r.returncode == 0, r.stderr
        assert len(new) == 0
    finally:
        for p in new:
            p.unlink(missing_ok=True)


def test_runner_resolve_cmd_windows_paths(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        runner.shutil,
        "which",
        lambda x: r"C:\Users\test\AppData\npm\claude.cmd" if x == "claude" else None,
    )

    # Empty / whitespace
    assert runner.resolve_cmd("") == []
    assert runner.resolve_cmd("   ") == []

    # Unquoted backslash path to exe
    assert runner.resolve_cmd(r"C:\tools\agent.exe --flag") == [r"C:\tools\agent.exe", "--flag"]

    # Quoted path with spaces to exe
    cmd_exe = runner.resolve_cmd(r'"C:\Program Files\My Agent\agent.exe" --model gpt-4')
    assert cmd_exe == [r"C:\Program Files\My Agent\agent.exe", "--model", "gpt-4"]

    # Quoted path with spaces to .cmd -> cmd /c with quotes removed
    cmd_batch = runner.resolve_cmd(r'"C:\Program Files\npm\claude.cmd" run --arg "val with space"')
    assert cmd_batch == ["cmd", "/c", r"C:\Program Files\npm\claude.cmd", "run", "--arg", "val with space"]

    # Unquoted .bat
    assert runner.resolve_cmd(r"C:\bin\agent.bat --flag") == ["cmd", "/c", r"C:\bin\agent.bat", "--flag"]

    # Single-quoted path with spaces to .bat
    assert runner.resolve_cmd(r"'C:\Program Files\tool.bat' arg") == ["cmd", "/c", r"C:\Program Files\tool.bat", "arg"]

    # Command resolved via which to .cmd
    assert runner.resolve_cmd("claude --flag") == ["cmd", "/c", r"C:\Users\test\AppData\npm\claude.cmd", "--flag"]


def test_executor_env_keeps_runtime_paths_and_drops_secrets(monkeypatch):
    monkeypatch.setenv("PATH", r"C:\safe-bin")
    monkeypatch.setenv("USERPROFILE", r"C:\Users\safe")
    monkeypatch.setenv("GITHUB_TOKEN", "github-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")

    env = runner.executor_env()

    assert env["PATH"] == r"C:\safe-bin"
    assert env["USERPROFILE"] == r"C:\Users\safe"
    assert "GITHUB_TOKEN" not in env
    assert "OPENAI_API_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env


def test_run_prompt_raises_on_nonzero_exit(monkeypatch):
    class FakeCompleted:
        returncode = 1
        stdout = "partial answer text"
        stderr = "executor trace tail"

    monkeypatch.setattr(runner.subprocess, "run",
                        lambda *a, **k: FakeCompleted())
    with pytest.raises(runner.ExecutorError) as ei:
        runner.run_prompt(["fake"], "prompt")
    assert "code 1" in str(ei.value)
    assert ei.value.stdout == "partial answer text"
    assert ei.value.stderr == "executor trace tail"


def test_runner_nonzero_executor_never_passes(tmp_path, monkeypatch):
    out_json = tmp_path / "nonzero.json"
    sc_file = tmp_path / "sc_nz.md"
    sc_file.write_text(
        "name: sc_nz\nskill: s_nz\ntrap: t_nz\nexpect: pass\n\nbody",
        encoding="utf-8",
    )

    def _nonzero(*args, **kwargs):
        raise runner.ExecutorError(
            "subprocess exited with code 1", stdout="", stderr="executor trace tail")

    monkeypatch.setattr(runner, "run_prompt", _nonzero)
    code = runner.run_scenarios(
        executor=["mock_exe"],
        judge=["mock_judge"],
        scenario_files=[sc_file],
        repeat=3,
        json_out=out_json,
        model="model-nonzero",
    )
    assert code == 1
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    sc = doc["scenarios"][0]
    assert sc["verdict"] == "FAIL"
    assert len(sc["attempts"]) == 3
    assert all(a["verdict"] == "FAIL" for a in sc["attempts"])
    assert sc["attempts"][0]["trace_tail"] == "executor trace tail"


def test_run_scenarios_live_json_requires_model(tmp_path, monkeypatch):
    sc_file = tmp_path / "sc_m.md"
    sc_file.write_text(
        "name: sc_m\nskill: s_m\ntrap: t_m\nexpect: pass\n\nbody",
        encoding="utf-8",
    )
    calls = []
    monkeypatch.setattr(runner, "run_prompt", lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match="explicit --model"):
        runner.run_scenarios(
            executor=["mock_exe"],
            judge=["mock_judge"],
            scenario_files=[sc_file],
            repeat=1,
            json_out=tmp_path / "m.json",
            model=None,
        )
    assert calls == []


def test_runner_live_json_requires_model_cli(tmp_path):
    out = tmp_path / "live_no_model.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "runner.py"),
         "--executor", "python", "--json", str(out)],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "requires an explicit --model" in r.stderr
    assert not out.exists()


def test_run_scenarios_disable_without_skills_root_raises_before_executor(tmp_path, monkeypatch):
    sc_file = tmp_path / "sc_disable.md"
    sc_file.write_text(
        "name: d\nskill: s\ntrap: t\nexpect: pass\n\nbody",
        encoding="utf-8",
    )
    calls = []
    monkeypatch.setattr(runner, "run_prompt",
                        lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match="disable-skill requires"):
        runner.run_scenarios(
            executor=["mock_exe"],
            judge=["mock_judge"],
            scenario_files=[sc_file],
            disable=frozenset({"yagni"}),
            skills_root=None,
        )
    assert calls == []


def test_runner_missing_scenario_cli_exit_2(tmp_path):
    r = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "runner.py"),
         "--scenario", "definitely-missing-scenario"],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "scenario not found" in r.stderr
    assert "Traceback" not in r.stderr

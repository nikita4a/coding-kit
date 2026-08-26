#!/usr/bin/env python3
"""eval/behavior_oracles.py — deterministic behavior oracles for always-on skills.

Trigger-eval's default signal (`trigger_eval.detect`) is: did the model name
the skill? Always-on skills are ambient (already loaded), so a correct answer
*applies* the skill's doctrine without naming it — naming only produces a
false zero-trigger rate (the dev-wiki 0.00 artifact; findings #54/#55).

For such skills the signal is instead: does the answer invoke the doctrine's
mandatory reflex? An oracle is a regex over the skill's verbatim reflex surface
(commands, paths from SKILL.md), never over the trigger queries' own words —
that is what keeps it from overfitting (trigger_eval.py anti-overfitting rule).

Free-text heuristics are a lower bound: a vague "I'll save it to memory" that
names no reflex command is conservatively treated as not-fired. Precise
behavioral judging stays the trap-suite's job (e.g. dev-wiki's
memory-routing scenario).
"""
import re

# skill slug -> doctrine reflex surface. Each alternative is a mandatory
# command/path from the skill's SKILL.md, so firing means the answer routed
# through that skill's machinery rather than merely acknowledging the request.
#
# Markers are precise command/path tokens only. `wiki`-ish markers are
# forbidden for the dev-wiki oracle because they collide with the skill's own
# slug — the oracle must never fire on the skill's name (that is exactly the
# signal that fails for ambient always-on skills).
BEHAVIOR_ORACLES: dict[str, str] = {
    # dev-wiki SKILL.md §Workflow (search + save): search_all.py / findings.py
    # / build.py / lint_wiki.py, and the memory root ~/.memory.
    "dev-wiki": (
        r"search_all\.py"
        r"|findings\.py"
        r"|build\.py"
        r"|lint_wiki\.py"
        r"|\.memory\b"
    ),
}


def has_oracle(skill: str) -> bool:
    """True when `skill` is an always-on skill measured by behavior, not name."""
    return skill in BEHAVIOR_ORACLES


def behavior_fired(skill: str, answer: str) -> bool:
    """Whether `answer` invokes `skill`'s mandated reflex (doctrine surface)."""
    pattern = BEHAVIOR_ORACLES[skill]
    return re.search(pattern, answer, re.IGNORECASE) is not None

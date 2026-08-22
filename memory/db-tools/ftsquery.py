#!/usr/bin/env python3

"""FTS5 query sanitizing — the single implementation.

Consumers: db-tools/search.py, db-tools/findings.py,
memory-scripts/memory-warmup.py (via the ~/.memory/db-tools junction).
Before v2.9 there were three drifting copies with three different
behaviors (audit 2026-08-22 M2); the quoted phrase-prefix semantics were
verified live against FTS5 (raw 'firmware*' and quoted '"firmware*"'
match the same rows — a trailing '*' INSIDE quotes keeps prefix meaning).
"""

OPS = {"AND", "OR", "NOT", "NEAR"}


def sanitize_query(query):
    """Escapes an FTS5 query: tokens with special characters (quotes,
    parens, hyphen — the known «agent-lsp» gotcha, asterisks) are wrapped
    in double quotes. Operators, NEAR(...) and ready-made quoted TOKENS
    (single-token, no inner spaces — tokenization is whitespace-based)
    are left untouched so boolean logic keeps working. A wrapped token
    keeps its trailing '*' as a phrase prefix (verified live 2026-08-22,
    tests/test_v29.py::test_quoted_prefix_still_matches)."""
    out = []
    for tok in query.split():
        upper = tok.upper()
        if upper in OPS or upper.startswith("NEAR(") or \
                (tok.startswith('"') and tok.endswith('"')):
            out.append(tok)
        elif tok.endswith("*") and any(c in tok[:-1] for c in '"-():^'):
            # prefix on a special-char body ('agent-lsp*'): quote the
            # body, keep the star outside (quoted '*' is a literal)
            out.append('"' + tok[:-1].replace('"', '""') + '"*')
        elif any(c in tok for c in '"-()*:^'):
            # wrap the whole token: raw hyphens/parens would be parsed
            # as FTS syntax (column filter / grouping) instead of text
            out.append('"' + tok.replace('"', '""') + '"')
        else:
            out.append(tok)
    return " ".join(out)

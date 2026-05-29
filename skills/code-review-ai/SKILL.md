---
name: code-review-ai
description: AI-powered code review with deep reasoning -- analyzes pull requests and commits for bugs, security issues, performance problems, and architectural concerns. Runs in CI or as a pre-commit hook.
version: 1.0.0
author: AI Agent Toolkit
license: MIT
tags: [code-review, pull-request, ci, security, static-analysis, quality]
platforms: [linux, macos]
metadata:
  hermes:
    category: development
    pricing: paid
---

# Code Review AI -- Deep Reasoning Code Review

Reviews code changes (pull requests, commits, staged diffs) with AI-powered deep reasoning. Detects bugs, security vulnerabilities, performance issues, logic errors, and architectural anti-patterns. Integrates into CI/CD pipelines or runs as a git hook.

## Triggers

- User says "review my code", "review this PR", "check my changes"
- User mentions "code review", "pull request review"
- CI pipeline triggers on PR open/push
- Pre-commit hook fires on `git commit`

## Steps

### 1. Gather Code Changes

```bash
# Review a specific commit
python3 scripts/review.py --commit HEAD

# Review staged changes (pre-commit)
python3 scripts/review.py --staged

# Review a PR branch against main
python3 scripts/review.py --branch feature/xyz --base main

# Review a file or directory
python3 scripts/review.py --path ./src/api/
```

### 2. Analyze Changes

The tool performs multi-layered analysis:

**Static Analysis (fast, rule-based):**
- Syntax errors
- Type errors (mypy, tsc, eslint)
- Unused imports/variables
- Code style violations
- Security linting (bandit, semgrep)

**Semantic Analysis (AI-powered):**
- Logic errors (off-by-one, inverted conditions)
- Race conditions and deadlocks
- Missing error handling
- SQL injection, XSS, CSRF
- Resource leaks (file handles, connections)
- Incorrect API usage
- Missing edge cases

**Architectural Review:**
- SOLID violations
- Tight coupling
- Circular dependencies
- Missing abstractions
- God objects / classes

### 3. Review Output

Generates structured review with severity levels:

```
=== Code Review: feature/xyz (3 commits) ===

CRITICAL (2)
  [src/api/auth.py:42] SQL Injection: raw string concatenation in query
    > query = f"SELECT * FROM users WHERE id = '{user_id}'"
    Fix: Use parameterized queries

  [src/api/payments.py:156] Missing authorization check
    > No auth check before processing payment
    Fix: Add @require_auth decorator

HIGH (3)
  [src/utils/db.py:89] Connection leak: cursor not closed
    > conn.cursor() called without finally block
    Fix: Use context manager

  [src/models/user.py:23] Missing index on foreign key
    > orders.user_id has FK but no index
    Impact: Full table scans on JOIN

MEDIUM (5)
  [src/services/email.py:44] Unhandled exception: SMTPAuthenticationError
  [src/api/orders.py:201] N+1 query detected
  [src/config.py:12] Secret in code: API key hardcoded

LOW (8)
  [src/utils/helpers.py:15] Unused variable: 'temp_data'
  [src/models/base.py:5] Missing docstring
  [tests/test_auth.py:30] Test doesn't assert anything

SUMMARY
  Files changed: 12
  Lines: +234 -89
  Critical: 2 | High: 3 | Medium: 5 | Low: 8
  Recommendation: FIX CRITICAL ISSUES BEFORE MERGE
```

### 4. Auto-Fix (Optional)

```bash
# Suggest fixes as patches
python3 scripts/review.py --commit HEAD --suggest-fixes

# Auto-apply safe fixes (style, imports, formatting)
python3 scripts/review.py --staged --auto-fix --safe-only
```

### 5. CI Integration

```yaml
# .github/workflows/code-review.yml
name: AI Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: AI Code Review
        run: |
          python3 scripts/review.py --pr ${{ github.event.number }} --github-token ${{ secrets.GITHUB_TOKEN }}
```

### 6. Review Rules Configuration

```yaml
# .code-review.yaml
severity_threshold: medium  # Only report medium and above

# Custom rules
rules:
  - pattern: "exec\(|eval\(|os\.system\("
    severity: critical
    message: "Dangerous function call detected"

  - pattern: "password\s*=\s*['"]"
    severity: critical
    message: "Hardcoded credential"

  - pattern: "TODO|FIXME|HACK"
    severity: low
    message: "Technical debt marker"

# Ignore patterns
ignore:
  - "tests/"
  - "migrations/"
  - "vendor/"
  - "node_modules/"

# Reviewer suggestions
suggest_reviewers: true  # Suggest specific reviewers based on changed files

# Required approvals
required:
  critical_fix: true
  security_scan: true
```

## Pitfalls

- **False positives happen** -- especially for complex logic. Review AI suggestions critically.
- **Don't rely solely on automated review** -- it complements but doesn't replace human review.
- **Large PRs overwhelm the analyzer** -- keep PRs under 500 lines.
- **Generated code** (protobuf, GraphQL types) produces noise -- add to `ignore:` list.
- **Secrets in environment variables** not in files won't be caught -- use secret scanning tools.
- **Custom frameworks** may need custom rules for accurate analysis.

## Verification

1. All critical and high issues are addressed before merge
2. Review output includes file paths and line numbers
3. CI pipeline passes review check
4. False positive rate is monitored and rules are tuned

## Scripts

- `scripts/review.py` -- Main orchestrator: gather changes, analyze, report
- `scripts/analyzer.py` -- Static + semantic analysis engine
- `scripts/rules_engine.py` -- Custom rules matching
- `scripts/github_bot.py` -- GitHub PR integration (post comments, request changes)

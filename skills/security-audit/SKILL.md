---
name: security-audit
description: Automated security auditing for codebases — vulnerability scanning, CWE mapping, and fix suggestions. Covers SAST (bandit/semgrep), dependency scanning (pip-audit/safety), and secret detection (gitleaks/detect-secrets).
version: 1.0.0
author: Armosis Agent SDK (freshtemp-labs)
license: MIT
tags: [security, audit, sast, vulnerabilities, cwe, owasp, code-scanning]
platforms: [linux, macos]
metadata:
  hermes:
    category: security
    pricing: paid
---

# Security Audit — Automated Code Security Scanner

Scans your codebase for security vulnerabilities across multiple dimensions: static analysis (SAST), dependency vulnerabilities, hardcoded secrets, and misconfigurations. Produces a detailed report with CWE classifications, severity ratings, and actionable fix suggestions.

## Triggers

- User asks to "scan for vulnerabilities", "security audit", "check security"
- User says "is my code secure?", "find security issues"
- CI/CD pipeline triggers a security check on PR
- Pre-commit hook for security validation

## Steps

### 1. Discovery — Understand the Codebase

```
Tree-sitter or glob patterns to identify:
- Source files (.py, .js, .ts, .go, .java, .rb, .php)
- Config files (Dockerfile, docker-compose.yml, k8s manifests, .env)
- Dependency manifests (requirements.txt, package.json, go.mod, Gemfile)
- CI/CD configs (.github/workflows/, .gitlab-ci.yml)
```

### 2. Static Analysis (SAST)

Run multiple SAST tools in parallel:

```bash
# Python: bandit (OWASP-focused)
bandit -r . -f json -o bandit_report.json

# Multi-language: semgrep with OWASP Top 10 rules
semgrep scan --config=auto --json -o semgrep_report.json

# Infrastructure: checkov for IaC scanning
checkov -d . -o json > checkov_report.json

# Hardcoded secrets: gitleaks
gitleaks detect -s . -f json -r gitleaks_report.json
```

### 3. Dependency Scanning

```bash
# Python dependencies
pip-audit --format json -o pip_audit.json

# Node.js dependencies
npm audit --json > npm_audit.json

# Generic: trivy filesystem
trivy fs --format json -o trivy_report.json .
```

### 4. Analyze and Correlate Findings

Run `scripts/audit.py` to merge all reports:
- De-duplicate findings across tools
- Map to CWE IDs and OWASP categories
- Score severity (Critical/High/Medium/Low/Info)
- Generate fix suggestions with code snippets
- Produce a prioritized remediation plan

```bash
python3 scripts/audit.py --target ./my-project --output security_report.md
```

### 5. Generate Report

Produces a structured report:
- **Executive Summary**: risk score, top issues, recommended actions
- **Detailed Findings**: CWE-ID, severity, file location, vulnerable code, fix
- **Dependency Issues**: CVE list, upgrade paths, breaking change warnings
- **Remediation Plan**: prioritized by severity and effort

## Key Tools Required

| Tool | Purpose | Install |
|------|---------|---------|
| bandit | Python SAST | `pip install bandit` |
| semgrep | Multi-lang SAST | `pip install semgrep` |
| checkov | IaC scanning | `pip install checkov` |
| gitleaks | Secret detection | `brew install gitleaks` |
| pip-audit | Python deps | `pip install pip-audit` |
| trivy | Container/filesystem | `brew install trivy` |

## Pitfalls

- **False positives are common** — always review findings before blocking CI. The report marks confidence levels; focus on high-confidence issues first.
- **Large codebases (>100K lines)** may need chunked scanning. Use the `--chunk-size` flag on audit.py.
- **Some tools require network access** (dependency scanners check live databases). Run offline with `--offline` mode for air-gapped environments.
- **Secret detection has false positives on test fixtures** — configure `.gitleaks.toml` to exclude test directories.
- **Don't blindly apply auto-fixes** — review each fix suggestion for correctness in your context.

## Verification

After running the audit:
1. All findings have a CWE mapping and severity score
2. The report includes line-numbered code snippets for each finding
3. Fix suggestions are syntactically valid for the target language
4. No duplicate findings (same issue reported by multiple tools is merged)
5. The remediation plan sorts by (severity × exploitability) / effort

## Output Example

```
=== Security Audit Report ===
Target: ./my-project (Python 3.11, 45 files, 8,234 LOC)
Date: 2026-05-18

Risk Score: 72/100 (HIGH)

Critical: 2  High: 5  Medium: 12  Low: 8

=== Critical Findings ===

[CWE-89] SQL Injection in api/users.py:45
  Severity: Critical | Confidence: High
  Code: query = f"SELECT * FROM users WHERE id={user_id}"
  Fix: Use parameterized queries
  Suggested:
    query = "SELECT * FROM users WHERE id=?"
    cursor.execute(query, (user_id,))

[CWE-798] Hardcoded Credential in config/secrets.py:12
  Severity: Critical | Confidence: High
  Code: DATABASE_PASSWORD = "admin123"
  Fix: Use environment variables
  Suggested:
    DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")
```

## Configuration

Create `~/.hermes/security-audit.yaml`:

```yaml
# Directories to exclude
exclude:
  - "*.min.js"
  - node_modules/
  - vendor/
  - __pycache__/
  - tests/fixtures/

# Severity thresholds
fail_on: Critical  # CI fails on Critical only

# Custom rules
custom_rules:
  - path: ./rules/company-policy.yaml
  - path: ./rules/finance-compliance.yaml

# False positive allowlist
allowlist:
  - cwe: "CWE-798"
    file: "tests/test_secrets.py"
    reason: "Test fixtures"
```

## Scripts

- `scripts/audit.py` — Main orchestrator: runs all scanners, merges results, generates report
- `scripts/merge_findings.py` — Deduplication and correlation engine
- `scripts/cwe_mapper.py` — Maps tool findings to CWE IDs

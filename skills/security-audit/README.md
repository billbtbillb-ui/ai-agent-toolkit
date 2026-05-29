# Security Audit Skill

> Premium AI Agent Skill — Automated code security scanning with actionable fix suggestions

## Overview

The Security Audit skill transforms your AI agent into a comprehensive security scanner. It runs multiple SAST tools, dependency scanners, and secret detectors in parallel, then intelligently merges results into a single actionable report with CWE classifications, severity ratings, and code-level fix suggestions.

## Key Features

- 🔍 **Multi-tool scanning** — bandit, semgrep, checkov, gitleaks, trivy, pip-audit
- 🎯 **CWE/OWASP mapping** — every finding classified by industry standards
- 🔧 **Auto-fix suggestions** — not just "what's wrong" but "how to fix it"
- 📊 **Risk scoring** — overall risk score with prioritized remediation plan
- 🚫 **False positive management** — allowlist, confidence ratings, custom exclusion rules

## Quick Start

```bash
# Install the skill
hermes skills install freshtemp-labs/ai-agent-toolkit/security-audit

# Run a security audit
hermes skill run security-audit --target ./my-project

# Or just ask your agent
"Run a security audit on my codebase"
```

## Requirements

- Python 3.10+
- Git (for gitleaks)
- Network access (for dependency vulnerability databases)

Install all scanners:
```bash
pip install bandit semgrep checkov pip-audit
brew install gitleaks trivy  # macOS
```

## What Gets Scanned

| Category | Tools | What it finds |
|----------|-------|---------------|
| Code vulnerabilities | bandit, semgrep | SQL injection, XSS, path traversal, deserialization |
| Infrastructure as Code | checkov | Misconfigured S3 buckets, open security groups, exposed ports |
| Secrets & credentials | gitleaks | API keys, tokens, passwords, private keys |
| Dependencies | pip-audit, trivy | CVE vulnerabilities, outdated packages, breaking changes |
| Container images | trivy | OS-level vulnerabilities, misconfigurations |

## Pricing

$9.99 — One-time purchase, includes all updates.

[Get License →](https://ai-agent-toolkit.dev/buy/security-audit)

## Support

- 📖 [Full Documentation](https://docs.ai-agent-toolkit.dev/skills/security-audit)
- 💬 [Discord Community](https://discord.gg/ai-agent-toolkit)
- 📧 support@ai-agent-toolkit.dev

## License

MIT License — see [LICENSE](../../LICENSE)

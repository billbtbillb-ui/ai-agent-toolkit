# Code Review AI Skill

> Premium AI Agent Skill -- Deep reasoning code review that catches what linters miss

## Overview

Most code review tools just run static analysis. Code Review AI uses deep reasoning to find logic errors, race conditions, security flaws, and architectural issues that rule-based tools can't detect. Integrates directly into your GitHub PR workflow or git hooks.

## Key Features

- Deep reasoning -- catches logic bugs, race conditions, edge cases
- Multi-layer -- static analysis + semantic AI + architectural review
- Security -- SQL injection, XSS, auth bypass, hardcoded secrets
- Performance -- N+1 queries, missing indexes, inefficient patterns
- CI/CD native -- GitHub Actions, GitLab CI, CircleCI, Jenkins
- Auto-fix -- suggest and apply safe fixes automatically
- Custom rules -- define project-specific review rules

## Quick Start

```bash
# Install
hermes skills install freshtemp-labs/ai-agent-toolkit/code-review-ai

# Review staged changes
hermes skill run code-review-ai --staged

# Review a PR
hermes skill run code-review-ai --pr 42 --github-token $GITHUB_TOKEN
```

## Review Categories

| Severity | Examples |
|----------|---------|
| Critical | SQL injection, auth bypass, data loss, security vulnerability |
| High | Missing error handling, connection leaks, race conditions |
| Medium | N+1 queries, unhandled exceptions, missing validation |
| Low | Style issues, unused imports, missing docstrings |

## CI Integration

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          hermes skill run code-review-ai --pr ${{ github.event.number }}
```

## Pricing

$14.99 -- One-time purchase, includes all updates.

[Get License](https://ai-agent-toolkit.dev/buy/code-review-ai)

## License

MIT License -- see [LICENSE](../../LICENSE)

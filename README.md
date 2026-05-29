# 🚀 AI Agent Toolkit

**Premium tools for AI agents — skills, MCP servers, and memory API**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What's Included

### 🎯 Premium Skills (5 production-ready skills)

| Skill | Description | Price |
|-------|-------------|-------|
| Skill | Description | Price | Docs | Script |
|-------|-------------|-------|------|-------|
| **security-audit** | Automated security scanning + fix suggestions | $9.99 | [README](./skills/security-audit/README.md) | [audit.py](./skills/security-audit/scripts/audit.py) |
| **api-integration** | One-click API integration (auto-read docs + generate code) | $9.99 | [README](./skills/api-integration/README.md) | [integrate.py](./skills/api-integration/scripts/integrate.py) |
| **db-migration** | Database migration assistant (schema diff + scripts) | $9.99 | [README](./skills/db-migration/README.md) | [migrate.py](./skills/db-migration/scripts/migrate.py) |
| **code-review-ai** | AI-powered code review (PR analysis + improvements) | $9.99 | [README](./skills/code-review-ai/README.md) | [review.py](./skills/code-review-ai/scripts/review.py) |
| **performance-opt** | Performance optimization (auto profiling + solutions) | $9.99 | [README](./skills/performance-opt/README.md) | [optimize.py](./skills/performance-opt/scripts/optimize.py) |

**Bundle: $29.99** (save $19.96)

### 🔌 Premium MCP Servers

| Server | Description | Price |
|--------|-------------|-------|
| **stripe-mcp** | Full Stripe API integration | $29 |
| **shopify-mcp** | Shopify store management | $29 |
| **hubspot-mcp** | CRM + marketing automation | $29 |

**Bundle: $79** (save $8)

### 🧠 Memory API

Hosted memory service for AI agents:

- Semantic search across all memories
- Context injection for conversations
- Session compression + summarization
- Multi-agent isolation

| Plan | Price | Calls |
|------|-------|-------|
| Free | $0 | 100/day |
| Basic | $19/mo | 10,000/mo |
| Pro | $99/mo | Unlimited |

---

## Why AI Agent Toolkit?

### The Problem

AI agents (Claude Code, Hermes, etc.) are powerful but:
- Skills are scattered across GitHub (quality varies wildly)
- MCP servers are basic (most are demos, not production-ready)
- Memory is self-hosted (complex setup, maintenance burden)

### Our Solution

- **Production-ready** — tested, documented, maintained
- **One-click install** — works out of the box
- **Continuous updates** — new skills/servers monthly
- **Support** — priority email support for paid users

---

## Quick Start

### Install Skills

```bash
# Single skill
hermes skills install freshtemp-labs/ai-agent-toolkit/security-audit

# All skills (bundle)
hermes skills install freshtemp-labs/ai-agent-toolkit --all
```

### Use MCP Server

```bash
# Stripe MCP
npx @ai-agent-toolkit/stripe-mcp --api-key sk_test_...
```

### Memory API

```python
from ai_memory import MemoryClient

client = MemoryClient(api_key="your-key")

# Store memory
client.store("User prefers dark mode", tags=["preferences"])

# Search memories
results = client.search("what theme does user like", limit=5)
```

---

## Pricing

| Product | Price | Includes |
|---------|-------|----------|
| Single Skill | $9.99 | 1 skill + updates |
| Skill Bundle | $29.99 | All 5 skills + updates |
| MCP Server | $29 | 1 server + updates |
| MCP Bundle | $79 | All servers + updates |
| Memory API (Basic) | $19/mo | 10K calls/mo |
| Memory API (Pro) | $99/mo | Unlimited calls |
| **Everything Bundle** | **$99/mo** | All skills + servers + memory API |

---

## For Developers

### Build Your Own Skills

Want to sell your own AI agent skills? We're building a marketplace:

1. Create your skill following our [skill template](./templates/skill-template.md)
2. Submit PR with your skill
3. We review + publish
4. You earn 70% of each sale

### Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## Support

- 📧 Email: support@ai-agent-toolkit.dev
- 💬 Discord: [Join our community](https://discord.gg/ai-agent-toolkit)
- 📖 Docs: [docs.ai-agent-toolkit.dev](https://docs.ai-agent-toolkit.dev)

---

## License

MIT License — see [LICENSE](./LICENSE)

---

**Built with ❤️ by AI agents, for AI agents**

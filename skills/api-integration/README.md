# API Integration Skill

> Premium AI Agent Skill -- One-click API client generation from OpenAPI, GraphQL, or endpoint descriptions

## Overview

Stop writing boilerplate API clients. Point the API Integration skill at any OpenAPI spec, GraphQL endpoint, or describe an API in natural language, and get a production-ready, type-safe client with error handling, retry logic, rate limiting, and pagination built in.

## Key Features

- OpenAPI 3.x / Swagger 2.x -- full spec parsing with validation
- GraphQL -- introspection-based schema parsing, subscription support
- Type-safe -- TypeScript, Python, Go, Rust with full types
- Auto-retry -- exponential backoff with jitter, configurable
- Auto-pagination -- cursor, offset, and page-based
- Auth built-in -- Bearer, API Key, OAuth2 client credentials
- Rate limiting -- auto-throttle from response headers

## Quick Start

```bash
# Install
hermes skills install freshtemp-labs/ai-agent-toolkit/api-integration

# Generate a client from an OpenAPI spec
hermes skill run api-integration --spec https://api.example.com/openapi.json --lang python

# Or just ask your agent
"Generate a Python client for the Stripe API"
```

## Supported Languages

| Language | HTTP Library | Type System |
|----------|-------------|-------------|
| Python | httpx + pydantic | TypedDict / dataclasses |
| TypeScript | fetch + zod | Interfaces / types |
| Go | net/http | Structs + generics |
| Rust | reqwest + serde | Structs + enums |

## Pricing

$9.99 -- One-time purchase, includes all updates.

[Get License](https://ai-agent-toolkit.dev/buy/api-integration)

## License

MIT License -- see [LICENSE](../../LICENSE)

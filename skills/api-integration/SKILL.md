---
name: api-integration
description: One-click API integration — reads OpenAPI/Swagger docs, GraphQL schemas, or raw HTTP endpoints and generates type-safe client code with error handling, retry logic, and authentication.
version: 1.0.0
author: AI Agent Toolkit
license: MIT
tags: [api, integration, openapi, swagger, graphql, rest, client-generation]
platforms: [linux, macos]
metadata:
  hermes:
    category: development
    pricing: paid
---

# API Integration — One-Click Client Generation

Reads API documentation (OpenAPI 3.x, Swagger 2.x, GraphQL introspection, or raw endpoint descriptions) and generates production-ready client code. Supports TypeScript, Python, Go, and Rust output with full type safety, error handling, retry logic, and authentication.

## Triggers

- User says "integrate with API", "connect to this API", "generate API client"
- User provides an OpenAPI/Swagger URL or file
- User describes an API endpoint they want to call

## Steps

### 1. API Discovery

```bash
# From OpenAPI spec (URL or local file)
python3 scripts/integrate.py --spec https://api.example.com/openapi.json --lang python

# From GraphQL endpoint (introspection query)
python3 scripts/integrate.py --graphql https://api.example.com/graphql --lang typescript
```

### 2. Schema Analysis

The tool parses the API spec and extracts:
- Endpoints (path, method, parameters, request/response schemas)
- Authentication requirements (Bearer, API Key, OAuth2)
- Rate limiting headers
- Error response formats
- Pagination patterns

### 3. Client Code Generation

Generates language-specific client code with:

**Python (httpx-based):**
```python
from generated_client import ExampleAPIClient

client = ExampleAPIClient(api_key="sk_xxx")
users = await client.get_users(limit=50)
```

**TypeScript (fetch-based):**
```typescript
import { ExampleAPIClient } from "./generated";

const client = new ExampleAPIClient({ apiKey: "sk_xxx" });
const users = await client.getUsers({ limit: 50 });
```

### 4. Features Included

Every generated client includes:
- **Type safety**: Full TypeScript interfaces / Python TypedDict / Go structs
- **Error handling**: Typed errors with HTTP status code mapping
- **Retry logic**: Configurable exponential backoff with jitter
- **Rate limiting**: Auto-throttle based on response headers
- **Pagination**: Automatic cursor/offset/page iteration
- **Authentication**: Bearer token, API key header/query, OAuth2 client credentials
- **Request/response validation**: Validate against OpenAPI schema (optional)

## Configuration

Create `.api-client.yaml` in your project root:

```yaml
# Default settings
default_language: python
output_dir: ./src/api/

# API specs to track
apis:
  - name: payments
    spec: https://api.payments.com/openapi.json
  - name: users
    spec: ./docs/users-api.yaml

# Auth profiles
auth:
  payments:
    type: bearer
    env_var: PAYMENTS_API_KEY
```

## Pitfalls

- **OpenAPI specs vary in quality** -- validate the spec first. Bad specs produce warnings but best-effort output.
- **Recursive schemas** (e.g., tree structures) may cause infinite type generation. The tool caps recursion at 5 levels.
- **Streaming endpoints** (SSE, WebSocket) need manual handling after generated stubs.
- **Don't commit generated code** -- regenerate from spec on each build. Use `.gitignore`.
- **Rate limit values in headers** may be inaccurate -- test with a dry run before production load.

## Verification

After generation:
1. All endpoints from the spec have corresponding methods
2. Request/response types compile without errors
3. Error handling covers all documented HTTP error codes
4. Auth header/parameter is included in every request
5. Generated code passes `mypy --strict` / `tsc --strict` / `go vet`

## Scripts

- `scripts/integrate.py` — Main orchestrator: parse spec, generate client, validate output

#!/usr/bin/env python3
"""API Integration - generate type-safe client code from OpenAPI/GraphQL specs."""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path


def fetch_spec(url: str) -> dict:
    """Fetch OpenAPI/GraphQL spec from URL."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json, application/yaml")
    req.add_header("User-Agent", "ai-agent-toolkit-api-integration/1.0")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read().decode()
    return json.loads(data)


def resolve_schema_ref(schema: dict, spec: dict) -> dict:
    """Resolve $ref references in schema."""
    if "$ref" in schema:
        ref_path = schema["$ref"]
        parts = ref_path.split("/")
        current = spec
        for part in parts[1:]:  # Skip '#'
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return {"type": "object", "description": f"Unresolved ref: {ref_path}"}
        if isinstance(current, dict) and "$ref" in current:
            return resolve_schema_ref(current, spec)
        return current
    return schema


def parse_openapi(spec: dict) -> dict:
    """Parse OpenAPI 3.x / Swagger 2.x spec into intermediate representation."""
    info = spec.get("info", {})
    is_v3 = "openapi" in spec
    is_v2 = "swagger" in spec

    endpoints = []
    schemas = {}

    # Extract paths
    paths = spec.get("paths", {})
    base_url = ""
    if is_v3:
        base_url = spec.get("servers", [{}])[0].get("url", "")
    elif is_v2:
        scheme = spec.get("schemes", ["https"])[0]
        host = spec.get("host", "localhost")
        base_path = spec.get("basePath", "/")
        base_url = f"{scheme}://{host}{base_path}"

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"):
                continue

            endpoint = {
                "path": path,
                "method": method.upper(),
                "summary": details.get("summary", ""),
                "description": details.get("description", ""),
                "operation_id": details.get("operationId",
                    f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"),
                "parameters": [],
                "request_body": None,
                "responses": {},
                "tags": details.get("tags", []),
            }

            # Parameters
            for param in details.get("parameters", []):
                if isinstance(param, dict):
                    endpoint["parameters"].append({
                        "name": param.get("name", ""),
                        "in": param.get("in", "query"),
                        "required": param.get("required", False),
                        "description": param.get("description", ""),
                    })

            # Request body (v3 only)
            if "requestBody" in details:
                content = details["requestBody"].get("content", {})
                if "application/json" in content:
                    schema_ref = content["application/json"].get("schema", {})
                    endpoint["request_body"] = resolve_schema_ref(schema_ref, spec)

            # Responses
            for status_code, response in details.get("responses", {}).items():
                if status_code.startswith("2") or status_code.startswith("4"):
                    content = response.get("content", {}) if isinstance(response, dict) else {}
                    if "application/json" in content:
                        schema_ref = content["application/json"].get("schema", {})
                        endpoint["responses"][status_code] = {
                            "description": response.get("description", "") if isinstance(response, dict) else "",
                            "schema": resolve_schema_ref(schema_ref, spec),
                        }

            endpoints.append(endpoint)

    # Extract schemas
    if is_v3:
        schemas = spec.get("components", {}).get("schemas", {})
    elif is_v2:
        schemas = spec.get("definitions", {})

    return {
        "title": info.get("title", "API"),
        "version": info.get("version", "1.0.0"),
        "base_url": base_url,
        "endpoints": endpoints,
        "schemas": schemas,
        "auth": detect_auth(spec),
    }


def detect_auth(spec: dict) -> dict:
    """Detect authentication requirements."""
    security = spec.get("security", [])
    components = spec.get("components", {}) or spec
    schemes = components.get("securitySchemes", {}) or spec.get("securityDefinitions", {})

    auth = {"type": "none", "header": None, "env_var": None}

    for sec_req in security:
        if not isinstance(sec_req, dict):
            continue
        for scheme_name in sec_req:
            if scheme_name in schemes:
                scheme = schemes[scheme_name]
                auth_type = scheme.get("type", "").lower()
                if auth_type == "http" and scheme.get("scheme") == "bearer":
                    auth = {"type": "bearer", "header": "Authorization", "env_var": "API_KEY"}
                elif auth_type == "apikey":
                    auth = {
                        "type": "api_key",
                        "header": scheme.get("name", "X-API-Key"),
                        "in": scheme.get("in", "header"),
                        "env_var": "API_KEY",
                    }
                elif auth_type == "oauth2":
                    auth = {"type": "oauth2", "env_var": "OAUTH_TOKEN"}
                return auth

    return auth


def generate_python_client(api: dict) -> str:
    """Generate a Python httpx client."""
    title_snake = re.sub(r'[^a-zA-Z0-9]', '_', api["title"]).lower().strip('_')
    class_name = ''.join(w.capitalize() for w in title_snake.split('_')) + "Client"

    lines = [
        f'"""',
        f'{api["title"]} API Client - Auto-generated by AI Agent Toolkit',
        f'Version: {api["version"]}',
        f'Base URL: {api["base_url"]}',
        f'"""',
        '',
        'import httpx',
        'import time',
        'import random',
        'import logging',
        'import asyncio',
        'from typing import Optional, Any',
        'from dataclasses import dataclass, field',
        '',
        'logger = logging.getLogger(__name__)',
        '',
        '',
        '@dataclass',
        f'class {class_name}:',
        f'    """Client for {api["title"]} API."""',
        '',
        f'    api_key: str',
        f'    base_url: str = "{api["base_url"]}"',
        '    timeout: float = 30.0',
        '    max_retries: int = 3',
        '    _client: Optional[httpx.AsyncClient] = field(default=None, repr=False)',
        '',
        '    async def _get_client(self) -> httpx.AsyncClient:',
        '        if self._client is None:',
        '            headers = {}',
    ]

    auth = api["auth"]
    if auth["type"] == "bearer":
        lines.append('            headers["Authorization"] = f"Bearer {self.api_key}"')
    elif auth["type"] == "api_key":
        if auth.get("in") == "header":
            lines.append(f'            headers["{auth["header"]}"] = self.api_key')
        else:
            lines.append(f'            # API key in {auth["in"]}: {auth["header"]}')

    lines.extend([
        '            self._client = httpx.AsyncClient(',
        '                base_url=self.base_url,',
        '                headers=headers,',
        '                timeout=httpx.Timeout(self.timeout),',
        '            )',
        '        return self._client',
        '',
        '    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:',
        '        client = await self._get_client()',
        '        for attempt in range(self.max_retries):',
        '            try:',
        '                resp = await client.request(method, path, **kwargs)',
        '                if resp.status_code == 429:',
        '                    retry_after = int(resp.headers.get("Retry-After", 1))',
        '                    logger.warning(f"Rate limited. Retry after {retry_after}s")',
        '                    await asyncio.sleep(retry_after)',
        '                    continue',
        '                resp.raise_for_status()',
        '                return resp',
        '            except httpx.TimeoutException:',
        '                if attempt == self.max_retries - 1:',
        '                    raise',
        '                wait = (2 ** attempt) + random.uniform(0, 1)',
        '                logger.warning(f"Timeout. Retry in {wait:.1f}s (attempt {attempt+1}/{self.max_retries})")',
        '                await asyncio.sleep(wait)',
        '            except httpx.HTTPStatusError:',
        '                raise',
        '        raise RuntimeError("Max retries exceeded")',
        '',
        '    async def close(self):',
        '        if self._client:',
        '            await self._client.aclose()',
        '            self._client = None',
    ])

    # Generate endpoint methods
    for ep in api["endpoints"]:
        op_id = ep["operation_id"]
        method = ep["method"].lower()
        path = ep["path"]
        summary = ep.get("summary", op_id)

        # Build method signature
        params = []
        for param in ep["parameters"]:
            default = " = None" if not param["required"] else ""
            params.append(f'{param["name"]}{default}')

        if ep.get("request_body"):
            params.append("body: dict = None")

        param_str = ", ".join(params)

        lines.extend([
            f'    async def {op_id}(self{f", {param_str}" if param_str else ""}):',
            f'        """{summary}"""',
        ])

        # Build query params
        query_params = [p for p in ep["parameters"] if p["in"] == "query"]
        if query_params:
            param_exprs = ", ".join(f'"{p["name"]}": {p["name"]}' for p in query_params)
            lines.append(f'        params = {{{param_exprs}}}')
            lines.append('        params = {k: v for k, v in params.items() if v is not None}')
            lines.append(f'        return await self._request("{method}", f"{path}", params=params)')
        elif ep.get("request_body"):
            lines.append(f'        return await self._request("{method}", f"{path}", json=body)')
        else:
            lines.append(f'        return await self._request("{method}", f"{path}")')

        lines.append('')

    return '\n'.join(lines)


def generate_typescript_client(api: dict) -> str:
    """Generate a TypeScript fetch client."""
    class_name = ''.join(w.capitalize() for w in re.sub(r'[^a-zA-Z0-9]', '_', api["title"]).lower().split('_')) + "Client"

    lines = [
        '/**',
        f' * {api["title"]} API Client - Auto-generated by AI Agent Toolkit',
        f' * Version: {api["version"]}',
        f' * Base URL: {api["base_url"]}',
        ' */',
        '',
        f'export class {class_name} {{',
        f'  private baseUrl: string;',
        f'  private headers: Record<string, string>;',
        f'  private maxRetries: number;',
        '',
        f'  constructor(config: {{ apiKey: string; baseUrl?: string; maxRetries?: number }}) {{',
        f'    this.baseUrl = config.baseUrl || "{api["base_url"]}";',
        f'    this.maxRetries = config.maxRetries || 3;',
    ]

    auth = api["auth"]
    if auth["type"] == "bearer":
        lines.append('    this.headers = { "Authorization": `Bearer ${config.apiKey}`, "Content-Type": "application/json" };')
    elif auth["type"] == "api_key":
        if auth.get("in") == "header":
            lines.append(f'    this.headers = {{ "{auth["header"]}": config.apiKey, "Content-Type": "application/json" }};')
        else:
            lines.append(f'    this.headers = {{ "Content-Type": "application/json" }};')

    lines.extend([
        '  }',
        '',
        '  private async request(method: string, path: string, body?: unknown): Promise<Response> {',
        '    for (let attempt = 0; attempt < this.maxRetries; attempt++) {',
        '      try {',
        '        const resp = await fetch(`${this.baseUrl}${path}`, {',
        '          method,',
        '          headers: this.headers,',
        '          body: body ? JSON.stringify(body) : undefined,',
        '        });',
        '        if (resp.status === 429) {',
        '          const retryAfter = parseInt(resp.headers.get("Retry-After") || "1");',
        '          await new Promise(r => setTimeout(r, retryAfter * 1000));',
        '          continue;',
        '        }',
        '        if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);',
        '        return resp;',
        '      } catch (e) {',
        '        if (attempt === this.maxRetries - 1) throw e;',
        '        const wait = Math.pow(2, attempt) * 1000 + Math.random() * 1000;',
        '        await new Promise(r => setTimeout(r, wait));',
        '      }',
        '    }',
        '    throw new Error("Max retries exceeded");',
        '  }',
    ])

    for ep in api["endpoints"]:
        op_id = ep["operation_id"]
        method = ep["method"].lower()
        path = ep["path"]
        summary = ep.get("summary", "")

        ts_params = []
        for param in ep["parameters"]:
            optional = "?" if not param["required"] else ""
            ts_params.append(f'{param["name"]}{optional}: string')

        if ep.get("request_body"):
            ts_params.append("body?: Record<string, unknown>")

        param_str = ", ".join(ts_params)

        lines.extend([
            f'  /** {summary} */',
            f'  async {op_id}({{ {param_str} }}{{}}: {{ {param_str} }}): Promise<Response> {{',
        ])

        query_params = [p for p in ep["parameters"] if p["in"] == "query"]
        if query_params:
            qs_parts = "&".join(f'{p["name"]}=${{{p["name"]}}}' for p in query_params)
            lines.append(f'    const qs = `{qs_parts}`;')
            lines.append(f'    return this.request("{method}", `{path}${{qs ? "?" + qs : ""}}`);')
        else:
            body_arg = ", body" if ep.get("request_body") else ""
            lines.append(f'    return this.request("{method}", "{path}"{body_arg});')
        lines.append('  }')
        lines.append('')

    lines.append('}')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="AI Agent Toolkit - API Integration")
    parser.add_argument("--spec", help="URL or path to OpenAPI/Swagger spec")
    parser.add_argument("--graphql", help="GraphQL endpoint URL")
    parser.add_argument("--describe", help="Natural language API description")
    parser.add_argument("--lang", default="python", choices=["python", "typescript", "go", "rust"])
    parser.add_argument("--output", "-o", default="./api_client")
    parser.add_argument("--client-name", help="Custom client class name")
    parser.add_argument("--base-url", help="Override base URL")

    args = parser.parse_args()

    if not args.spec and not args.graphql and not args.describe:
        parser.error("Must specify --spec, --graphql, or --describe")

    if args.spec:
        # Fetch spec
        if args.spec.startswith("http://") or args.spec.startswith("https://"):
            spec = fetch_spec(args.spec)
        else:
            with open(args.spec) as f:
                spec = json.load(f)

        api = parse_openapi(spec)
        if args.base_url:
            api["base_url"] = args.base_url
        if args.client_name:
            api["title"] = args.client_name

        # Generate client
        generators = {"python": generate_python_client, "typescript": generate_typescript_client}
        if args.lang not in generators:
            print(f"Language '{args.lang}' not yet implemented. Available: {list(generators.keys())}")
            sys.exit(1)

        code = generators[args.lang](api)

        # Write output
        os.makedirs(args.output, exist_ok=True)
        ext = {"python": "py", "typescript": "ts", "go": "go", "rust": "rs"}[args.lang]
        outfile = os.path.join(args.output, f"client.{ext}")
        with open(outfile, "w") as f:
            f.write(code)

        print("=" * 40)
        print("API Integration Report")
        print("=" * 40)
        print(f"Spec: {args.spec}")
        print(f"Language: {args.lang}")
        print(f"Generated: {outfile}")
        print(f"Endpoints: {len(api['endpoints'])}")
        for ep in api["endpoints"]:
            print(f"  {ep['method']:6s} {ep['path']}")
        print(f"Auth: {api['auth']['type']}")
        print()
        print("Next steps:")
        if api['auth']['type'] == 'bearer':
            print("  1. export API_KEY=your_key")
        print(f"  2. Use the generated client in your code")


if __name__ == "__main__":
    main()

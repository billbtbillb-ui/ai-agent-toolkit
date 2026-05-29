#!/usr/bin/env python3
"""Security Audit Orchestrator — runs multiple SAST tools, merges findings, generates report."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Finding:
    tool: str
    rule_id: str
    message: str
    severity: str  # Critical, High, Medium, Low, Info
    confidence: str  # High, Medium, Low
    file_path: str
    line: int
    cwe_id: str = ""
    owasp_category: str = ""
    fix_suggestion: str = ""
    code_snippet: str = ""


@dataclass
class AuditResult:
    target: str
    scan_time: float
    total_files: int = 0
    total_lines: int = 0
    findings: list = field(default_factory=list)
    tool_outputs: dict = field(default_factory=dict)


# CWE mapping rules: (tool, rule_pattern) -> (cwe_id, owasp_category, fix_template)
CWE_MAP = {
    # bandit rules
    ("bandit", "B608"): ("CWE-89", "A03:2021-Injection", "Use parameterized queries instead of string formatting."),
    ("bandit", "B609"): ("CWE-22", "A01:2021-Broken Access Control", "Sanitize file paths with os.path.abspath and validate against allowed directories."),
    ("bandit", "B105"): ("CWE-798", "A07:2021-Identification Failures", "Use environment variables or a secrets manager instead of hardcoded credentials."),
    ("bandit", "B106"): ("CWE-798", "A07:2021-Identification Failures", "Move secrets to environment variables or a vault."),
    ("bandit", "B301"): ("CWE-502", "A08:2021-Software Integrity Failures", "Never unpickle untrusted data. Use JSON or a safer serialization format."),
    ("bandit", "B303"): ("CWE-327", "A02:2021-Cryptographic Failures", "Use SHA-256 or stronger. MD5 is cryptographically broken."),
    ("bandit", "B307"): ("CWE-78", "A03:2021-Injection", "Use subprocess.run with shell=False and a list of args."),
    ("bandit", "B108"): ("CWE-22", "A01:2021-Broken Access Control", "Validate paths and use secure file handling."),
    ("bandit", "B113"): ("CWE-400", "A05:2021-Security Misconfiguration", "Set request timeouts to prevent hanging connections."),
    # semgrep patterns
    ("semgrep", "sql-injection"): ("CWE-89", "A03:2021-Injection", "Use parameterized queries or an ORM."),
    ("semgrep", "xss"): ("CWE-79", "A03:2021-Injection", "Use proper output encoding (html.escape, DOMPurify)."),
    ("semgrep", "path-traversal"): ("CWE-22", "A01:2021-Broken Access Control", "Validate and sanitize file paths."),
    ("semgrep", "deserialization"): ("CWE-502", "A08:2021-Software Integrity Failures", "Use safe serialization (JSON) and validate input."),
    # gitleaks
    ("gitleaks", "aws-access-key"): ("CWE-798", "A07:2021-Identification Failures", "Rotate the exposed key immediately. Use IAM roles or environment variables."),
    ("gitleaks", "generic-api-key"): ("CWE-798", "A07:2021-Identification Failures", "Store API keys in a secrets manager. Rotate exposed keys."),
    # trivy / pip-audit
    ("pip-audit", "CVE"): ("CWE-937", "A06:2021-Vulnerable Components", "Upgrade to a patched version. Check changelog for breaking changes."),
    ("trivy", "CVE"): ("CWE-937", "A06:2021-Vulnerable Components", "Update the affected package or container base image."),
    ("checkov", "CKV_AWS"): ("CWE-284", "A01:2021-Broken Access Control", "Review IAM policies and apply least-privilege principle."),
}


def count_codebase(target: str) -> tuple:
    """Count total files and lines of code."""
    total_files = 0
    total_lines = 0
    code_extensions = {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".php", ".c", ".cpp", ".h", ".cs"}
    exclude_dirs = {"node_modules", "__pycache__", ".git", "vendor", ".venv", "venv", "dist", "build"}
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if any(f.endswith(ext) for ext in code_extensions):
                total_files += 1
                try:
                    with open(os.path.join(root, f), "r", errors="ignore") as fh:
                        total_lines += sum(1 for _ in fh)
                except Exception:
                    pass
    return total_files, total_lines


def run_tool(cmd: list, tool_name: str, cwd: str) -> Optional[dict]:
    """Run a scanning tool and return its JSON output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=cwd)
        if result.returncode not in (0, 1):  # 1 often means "found issues", not error
            return None
        try:
            return json.loads(result.stdout) if result.stdout.strip() else {"results": []}
        except json.JSONDecodeError:
            return {"raw_output": result.stdout[:10000]}
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def parse_bandit(output: dict) -> list:
    findings = []
    for issue in output.get("results", []):
        f = Finding(
            tool="bandit",
            rule_id=issue.get("test_id", ""),
            message=issue.get("issue_text", ""),
            severity=issue.get("issue_severity", "Low"),
            confidence=issue.get("issue_confidence", "Low"),
            file_path=issue.get("filename", ""),
            line=issue.get("line_number", 0),
        )
        # Get code snippet if available
        code = issue.get("code", "")
        if code:
            f.code_snippet = code.strip()
        findings.append(f)
    return findings


def parse_semgrep(output: dict) -> list:
    findings = []
    for issue in output.get("results", []):
        f = Finding(
            tool="semgrep",
            rule_id=issue.get("check_id", ""),
            message=issue.get("extra", {}).get("message", ""),
            severity=issue.get("extra", {}).get("severity", "Low"),
            confidence="High",
            file_path=issue.get("path", ""),
            line=issue.get("start", {}).get("line", 0),
        )
        lines = issue.get("extra", {}).get("lines", "")
        if lines:
            f.code_snippet = lines.strip()
        findings.append(f)
    return findings


def parse_gitleaks(output: dict) -> list:
    findings = []
    for leak in output if isinstance(output, list) else []:
        f = Finding(
            tool="gitleaks",
            rule_id=leak.get("RuleID", leak.get("rule_id", "")),
            message=f"Hardcoded {leak.get('Description', 'secret')} detected",
            severity="Critical",
            confidence="High",
            file_path=leak.get("File", leak.get("file", "")),
            line=leak.get("StartLine", leak.get("line", 0)),
            code_snippet=leak.get("Match", leak.get("match", ""))[:200],
        )
        findings.append(f)
    return findings


def parse_pip_audit(output: dict | list) -> list:
    findings = []
    deps = output if isinstance(output, list) else output.get("dependencies", [])
    for dep in deps:
        for vuln in dep.get("vulns", []):
            f = Finding(
                tool="pip-audit",
                rule_id=vuln.get("id", "CVE-UNKNOWN"),
                message=f"{dep.get('name')}=={dep.get('version')}: {vuln.get('description', 'Vulnerable dependency')}",
                severity="High",
                confidence="High",
                file_path="requirements.txt",
                line=0,
                fix_suggestion=vuln.get("fix_versions", ["Upgrade to latest"])[0] if vuln.get("fix_versions") else "Upgrade to latest",
            )
            findings.append(f)
    return findings


def map_cwe(findings: list) -> list:
    """Map each finding to CWE and OWASP category."""
    for f in findings:
        matched = False
        for (tool_prefix, rule_pattern), (cwe, owasp, fix) in CWE_MAP.items():
            if f.tool == tool_prefix and rule_pattern.lower() in f.rule_id.lower():
                f.cwe_id = cwe
                f.owasp_category = owasp
                f.fix_suggestion = fix
                matched = True
                break
        if not matched:
            f.cwe_id = "CWE-Unknown"
            f.owasp_category = "Unknown"
    return findings


def generate_report(result: AuditResult) -> str:
    """Generate a Markdown security audit report."""
    findings = result.findings

    # Count by severity
    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in findings:
        sev = f.severity if f.severity in severity_counts else "Info"
        severity_counts[sev] += 1

    # Risk score (heuristic)
    risk_weights = {"Critical": 25, "High": 10, "Medium": 3, "Low": 1, "Info": 0}
    risk_score = sum(risk_weights.get(f.severity, 0) for f in findings)
    risk_score = min(100, risk_score)

    lines = [
        "# 🔒 Security Audit Report",
        "",
        f"**Target**: `{result.target}`",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Files Scanned**: {result.total_files}  |  **Lines of Code**: {result.total_lines:,}",
        f"**Scan Duration**: {result.scan_time:.1f}s",
        "",
        f"## Risk Score: {risk_score}/100",
        "",
        f"| Severity | Count |",
        f"|----------|-------|",
    ]
    for sev in ["Critical", "High", "Medium", "Low", "Info"]:
        if severity_counts[sev]:
            lines.append(f"| {sev} | {severity_counts[sev]} |")
    lines.append("")

    # Findings by severity
    for sev in ["Critical", "High", "Medium", "Low"]:
        sev_findings = [f for f in findings if f.severity == sev]
        if not sev_findings:
            continue
        lines.append(f"## {sev} Findings ({len(sev_findings)})")
        lines.append("")
        for f in sev_findings[:20]:  # Limit per section
            lines.extend([
                f"### [{f.cwe_id}] {f.rule_id} — `{f.file_path}:{f.line}`",
                "",
                f"**Severity**: {f.severity}  |  **Confidence**: {f.confidence}  |  **Tool**: {f.tool}",
                f"**OWASP**: {f.owasp_category}",
                "",
                f"> {f.message}",
                "",
            ])
            if f.code_snippet:
                lines.extend([
                    "```",
                    f.code_snippet,
                    "```",
                    "",
                ])
            if f.fix_suggestion:
                lines.extend([
                    f"**Fix**: {f.fix_suggestion}",
                    "",
                ])
            lines.append("---")
            lines.append("")

    # Summary
    lines.extend([
        "## Summary",
        "",
        f"- **Total Findings**: {len(findings)}",
        f"- **Critical**: {severity_counts['Critical']}",
        f"- **High**: {severity_counts['High']}",
        f"- **Medium**: {severity_counts['Medium']}",
        f"- **Low**: {severity_counts['Low']}",
        "",
        "### Recommended Actions",
        "",
        "1. Fix all Critical findings immediately",
        "2. Address High findings within 7 days",
        "3. Resolve Medium findings within 30 days",
        "4. Review Low findings as part of regular maintenance",
        "",
        "---",
        "*Generated by AI Agent Toolkit — Security Audit Skill*",
    ])

    return "\n".join(lines)


def run_audit(target: str, tools: list = None, chunk_size: int = None, offline: bool = False) -> AuditResult:
    """Run the full security audit."""
    target = os.path.abspath(target)
    if not os.path.isdir(target):
        print(f"Error: {target} is not a directory")
        sys.exit(1)

    result = AuditResult(target=target, scan_time=0)
    start_time = time.time()

    # Count files
    result.total_files, result.total_lines = count_codebase(target)
    print(f"Scanning {result.total_files} files ({result.total_lines:,} lines)...")

    # Define tools to run
    tool_configs = {
        "bandit": (["bandit", "-r", target, "-f", "json", "-q"], parse_bandit),
        "semgrep": (["semgrep", "scan", "--config=auto", "--json", "-q", target], parse_semgrep),
        "gitleaks": (["gitleaks", "detect", "-s", target, "-f", "json", "--no-git"], parse_gitleaks),
        "pip-audit": (["pip-audit", "--format", "json", "-r", os.path.join(target, "requirements.txt")], parse_pip_audit),
    }

    # Filter to requested tools
    if tools:
        tool_configs = {k: v for k, v in tool_configs.items() if k in tools}

    # Run tools in parallel
    all_findings = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for name, (cmd, parser) in tool_configs.items():
            futures[executor.submit(run_tool, cmd, name, target)] = (name, parser)

        for future in as_completed(futures):
            name, parser = futures[future]
            try:
                output = future.result()
                if output:
                    result.tool_outputs[name] = output
                    parsed = parser(output)
                    all_findings.extend(parsed)
                    print(f"  {name}: {len(parsed)} findings")
                else:
                    print(f"  {name}: skipped (tool not available or no output)")
            except Exception as e:
                print(f"  {name}: error — {e}")

    # Map to CWE
    all_findings = map_cwe(all_findings)

    # Sort by severity
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
    all_findings.sort(key=lambda f: (severity_order.get(f.severity, 99), f.file_path, f.line))

    result.findings = all_findings
    result.scan_time = time.time() - start_time

    return result


def main():
    parser = argparse.ArgumentParser(description="AI Agent Toolkit — Security Audit")
    parser.add_argument("--target", "-t", default=".", help="Target directory to scan")
    parser.add_argument("--output", "-o", default="security_report.md", help="Output report file")
    parser.add_argument("--tools", nargs="+", choices=["bandit", "semgrep", "gitleaks", "pip-audit"],
                        help="Specific tools to run (default: all available)")
    parser.add_argument("--chunk-size", type=int, help="Max files per chunk for large codebases")
    parser.add_argument("--offline", action="store_true", help="Skip tools that require network access")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")

    args = parser.parse_args()

    tools = args.tools
    if args.offline:
        tools = [t for t in (tools or ["bandit", "semgrep", "gitleaks"]) if t != "pip-audit"]

    result = run_audit(args.target, tools=tools, chunk_size=args.chunk_size, offline=args.offline)

    if args.json:
        output = json.dumps({
            "target": result.target,
            "files_scanned": result.total_files,
            "lines_of_code": result.total_lines,
            "scan_duration_seconds": result.scan_time,
            "findings": [{"tool": f.tool, "rule_id": f.rule_id, "severity": f.severity,
                          "cwe": f.cwe_id, "file": f.file_path, "line": f.line,
                          "message": f.message, "fix": f.fix_suggestion} for f in result.findings]
        }, indent=2)
        print(output)
    else:
        report = generate_report(result)
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {args.output}")
        print(f"Total findings: {len(result.findings)}")


if __name__ == "__main__":
    main()

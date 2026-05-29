#!/usr/bin/env python3
"""Code Review AI - deep reasoning code review for PRs, commits, and staged changes."""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Finding:
    severity: str  # critical, high, medium, low
    file: str
    line: int
    category: str  # security, bug, performance, style, architecture
    message: str
    suggestion: str = ""
    code_snippet: str = ""


# Built-in security patterns
SECURITY_PATTERNS = [
    (re.compile(r'(?:exec|eval)\s*\('), "critical", "Dangerous function call: exec/eval"),
    (re.compile(r'os\.system\s*\('), "high", "Shell command injection risk"),
    (re.compile(r'(?:password|passwd|secret|token|api_key|apikey)\s*=\s*["']'), "critical", "Hardcoded credential detected"),
    (re.compile(r'(?:SELECT|INSERT|UPDATE|DELETE).+?\%s'), "critical", "Potential SQL injection: string formatting in query"),
    (re.compile(r'f["'].*?(?:SELECT|INSERT|UPDATE|DELETE)'), "critical", "Potential SQL injection: f-string in SQL query"),
    (re.compile(r'subprocess\.(?:call|Popen|run)\s*\([^)]*shell\s*=\s*True'), "high", "Shell=True subprocess call"),
    (re.compile(r'pickle\.(?:loads?|dumps?)\s*\('), "high", "Unsafe deserialization with pickle"),
    (re.compile(r'xml\.etree\.ElementTree\.parse\s*\('), "medium", "XML parsing without defusedxml (XXE risk)"),
    (re.compile(r'yaml\.load\s*\((?!.*Loader=yaml\.SafeLoader)'), "high", "Unsafe YAML loading (use SafeLoader)"),
]

PERFORMANCE_PATTERNS = [
    (re.compile(r'for\s+\w+\s+in\s+(?:range|list).*:\s*
\s*\w+\.append\('), "medium", "List comprehension could be faster"),
    (re.compile(r'\.count\(\)\s+in\s+for'), "high", "N+1 query pattern: .count() inside loop"),
    (re.compile(r'\.all\(\)\s+in\s+for'), "high", "N+1 query pattern: .all() inside loop"),
    (re.compile(r'open\([^)]*\)(?!.*with)'), "medium", "File opened without context manager (potential resource leak)"),
    (re.compile(r'cursor\(\)(?!.*\.close\()'), "medium", "Database cursor potentially not closed"),
]

BUG_PATTERNS = [
    (re.compile(r'(?:==\s*None|!=\s*None)\s*and'), "low", "Consider 'is None' instead of '== None'"),
    (re.compile(r'except\s*:\s*$'), "high", "Bare except clause catches too much"),
    (re.compile(r'except\s+Exception\s*:\s*
\s*pass'), "medium", "Exception silently swallowed"),
    (re.compile(r'assert\s+(?!.*test)'), "medium", "Assert used outside tests (stripped with -O flag)"),
    (re.compile(r'mutable default arg'), "medium", "Mutable default argument detected"),
    (re.compile(r'lambda\s+\w+\s*:\s*\w+\.\w+\(.*\)\s*,'), "low", "Lambda assignment to variable"),
]

STYLE_PATTERNS = [
    (re.compile(r'TODO|FIXME|HACK|XXX'), "low", "Technical debt marker"),
    (re.compile(r'print\s*\((?!.*f?["'])'), "low", "Debug print statement"),
    (re.compile(r'import\s+\*\s+from'), "low", "Wildcard import"),
]


def run_git_diff(target: str, base: str = None) -> str:
    """Get git diff for the target."""
    cmd = ["git"]
    if target == "--staged":
        cmd.extend(["diff", "--cached"])
    elif target == "HEAD":
        cmd.extend(["diff", "HEAD~1..HEAD"])
    elif base:
        cmd.extend(["diff", f"{base}..{target}"])
    else:
        cmd.extend(["diff", target])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout
    except subprocess.TimeoutExpired:
        return ""
    except FileNotFoundError:
        return ""


def parse_diff(diff_text: str) -> list:
    """Parse git diff into per-file changes."""
    files = []
    current_file = None
    current_changes = []
    
    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            if current_file:
                files.append({"file": current_file, "changes": "\n".join(current_changes)})
            current_file = line.split()[-1].lstrip("b/")
            current_changes = []
        elif current_file:
            current_changes.append(line)
    
    if current_file:
        files.append({"file": current_file, "changes": "\n".join(current_changes)})
    
    return files


def analyze_file(file_path: str, content: str, rules: dict = None) -> list:
    """Analyze a single file for issues."""
    findings = []
    lines = content.split("\n")
    
    all_patterns = []
    if rules and rules.get("security", True):
        all_patterns.extend(SECURITY_PATTERNS)
    if rules and rules.get("performance", True):
        all_patterns.extend(PERFORMANCE_PATTERNS)
    if rules and rules.get("bug", True):
        all_patterns.extend(BUG_PATTERNS)
    if rules and rules.get("style", True):
        all_patterns.extend(STYLE_PATTERNS)
    
    for i, line in enumerate(lines, 1):
        for pattern, severity, message in all_patterns:
            if pattern.search(line):
                # Skip if in ignore list
                if rules and "ignore_patterns" in rules:
                    skip = False
                    for ignore_pat in rules["ignore_patterns"]:
                        if re.search(ignore_pat, line):
                            skip = True
                            break
                    if skip:
                        continue
                
                category = "security" if severity in ("critical",) else \
                          "performance" if "performance" in str(all_patterns) else \
                          "bug" if severity in ("high", "medium") else "style"
                
                findings.append(Finding(
                    severity=severity,
                    file=file_path,
                    line=i,
                    category=category,
                    message=message,
                    code_snippet=line.strip()[:100],
                ))
    
    return findings


def format_review(findings: list, branch_name: str = "") -> str:
    """Format findings into Markdown review."""
    by_severity = defaultdict(list)
    for f in findings:
        by_severity[f.severity].append(f)
    
    order = ["critical", "high", "medium", "low"]
    
    lines = [
        f"# AI Code Review{f': {branch_name}' if branch_name else ''}",
        "",
    ]
    
    # Summary
    total = len(findings)
    lines.append("## Summary")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    for sev in order:
        if by_severity[sev]:
            lines.append(f"| {sev.upper()} | {len(by_severity[sev])} |")
    lines.append(f"| **Total** | **{total}** |")
    lines.append("")
    
    # Recommendations
    criticals = len(by_severity["critical"])
    highs = len(by_severity["high"])
    if criticals > 0:
        lines.append(f"> CRITICAL issues found. Fix before merge.")
    elif highs > 0:
        lines.append(f"> {highs} high-severity issues. Review before merge.")
    elif total > 0:
        lines.append(f"> {total} minor issues. Consider addressing.")
    else:
        lines.append(f"> No issues found. Good job!")
    
    lines.append("")
    
    # Detailed findings
    for sev in order:
        if not by_severity[sev]:
            continue
        emoji = {"critical": "red_circle", "high": "orange_circle", "medium": "yellow_circle", "low": "green_circle"}
        lines.append(f"## :{emoji.get(sev, 'white_circle')}: {sev.upper()} ({len(by_severity[sev])})")
        lines.append("")
        
        for f in by_severity[sev]:
            lines.append(f"### `{f.file}:{f.line}` -- {f.message}")
            lines.append("")
            if f.code_snippet:
                lines.append(f"```")
                lines.append(f.code_snippet)
                lines.append(f"```")
            if f.suggestion:
                lines.append(f"**Suggestion**: {f.suggestion}")
            lines.append("")
    
    lines.append("---")
    lines.append("*Generated by AI Agent Toolkit - Code Review AI*")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AI Agent Toolkit - Code Review AI")
    parser.add_argument("--commit", help="Review a specific commit")
    parser.add_argument("--staged", action="store_true", help="Review staged changes")
    parser.add_argument("--branch", help="Branch to review")
    parser.add_argument("--base", default="main", help="Base branch for comparison")
    parser.add_argument("--path", help="Review specific file/directory")
    parser.add_argument("--output", "-o", default="review_report.md", help="Output report file")
    parser.add_argument("--suggest-fixes", action="store_true", help="Suggest fix patches")
    parser.add_argument("--auto-fix", action="store_true", help="Auto-apply safe fixes")
    parser.add_argument("--safe-only", action="store_true", help="Only apply safe (low severity) fixes")
    parser.add_argument("--pr", help="PR number for GitHub integration")
    parser.add_argument("--github-token", help="GitHub token for PR comments")
    
    args = parser.parse_args()
    
    # Get code changes
    diff_content = ""
    branch_name = ""
    
    if args.staged:
        diff_content = run_git_diff("--staged")
        branch_name = "staged changes"
    elif args.commit:
        diff_content = run_git_diff(args.commit)
        branch_name = args.commit[:8]
    elif args.branch:
        diff_content = run_git_diff(args.branch, args.base)
        branch_name = args.branch
    elif args.path:
        # Read files directly
        findings = []
        base_path = args.path
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.go', '.rs', '.java', '.rb', '.php')):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path) as f:
                            content = f.read()
                        findings.extend(analyze_file(full_path, content))
                    except Exception as e:
                        print(f"Warning: couldn't read {full_path}: {e}")
    else:
        parser.error("Must specify --commit, --staged, --branch, or --path")
    
    if diff_content and not args.path:
        # Parse diff and analyze
        files = parse_diff(diff_content)
        
        findings = []
        for file_info in files:
            # Extract only added/modified lines from diff
            changed_lines = []
            current_line = 0
            for line in file_info["changes"].split("\n"):
                if line.startswith("@@"):
                    match = re.search(r'\+(\d+)', line)
                    if match:
                        current_line = int(match.group(1)) - 1
                elif line.startswith("+") and not line.startswith("+++"):
                    current_line += 1
                    changed_lines.append((current_line, line[1:]))
                elif not line.startswith("-"):
                    current_line += 1
            
            # Reconstruct a minimal file for analysis
            content = "\n".join(l[1] for l in changed_lines)
            if content.strip():
                file_findings = analyze_file(file_info["file"], content)
                # Adjust line numbers
                line_map = {i+1: l[0] for i, l in enumerate(changed_lines)}
                for f in file_findings:
                    f.line = line_map.get(f.line, f.line)
                findings.extend(file_findings)
    
    # Generate report
    report = format_review(findings, branch_name)
    with open(args.output, "w") as f:
        f.write(report)
    
    # Print summary
    by_severity = defaultdict(int)
    for f in findings:
        by_severity[f.severity] += 1
    
    print("=" * 50)
    print("AI Code Review Report")
    print("=" * 50)
    for sev in ["critical", "high", "medium", "low"]:
        if by_severity[sev]:
            print(f"  {sev.upper()}: {by_severity[sev]}")
    print(f"  Total: {len(findings)}")
    print(f"\nFull report: {args.output}")
    
    # Print critical findings immediately
    critical_findings = [f for f in findings if f.severity == "critical"]
    if critical_findings:
        print("\nCRITICAL ISSUES:")
        for f in critical_findings:
            print(f"  {f.file}:{f.line} -- {f.message}")


if __name__ == "__main__":
    main()

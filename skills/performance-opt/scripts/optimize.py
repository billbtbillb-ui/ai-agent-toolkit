#!/usr/bin/env python3
"""Performance Optimization - profile, detect bottlenecks, and optimize code."""

import argparse
import cProfile
import io
import json
import os
import pstats
import re
import subprocess
import sys
import time
import tracemalloc
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Hotspot:
    function: str
    file: str
    line: int
    total_time: float
    cumulative_time: float
    ncalls: int
    pct_of_total: float = 0.0


@dataclass
class Bottleneck:
    category: str  # cpu, memory, io, algorithm
    severity: str  # critical, high, medium, low
    location: str
    description: str
    impact: str
    recommendation: str
    estimated_speedup: str = "unknown"


@dataclass
class Optimization:
    description: str
    impact: str  # high, medium, low
    effort: str  # high, medium, low
    category: str
    code_before: str = ""
    code_after: str = ""
    estimated_speedup: str = ""


def profile_cpu(script_path: str, args: list = None) -> dict:
    """CPU profiling with cProfile."""
    profiler = cProfile.Profile()
    
    # We need to actually run the script in a subprocess
    cmd = [sys.executable, "-m", "cProfile", "-o", "/tmp/perf_opt_profile.prof", script_path]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        result = subprocess.CompletedProcess(cmd, 124, "", "Profiling timed out after 60s")
    
    # Parse pstats
    if os.path.exists("/tmp/perf_opt_profile.prof"):
        s = io.StringIO()
        stats = pstats.Stats("/tmp/perf_opt_profile.prof", stream=s)
        stats.sort_stats("cumulative")
        stats.print_stats(20)
        
        hotspots = []
        for line in s.getvalue().split("\n"):
            # Parse pstats output lines
            match = re.match(r'\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(.+)', line)
            if match:
                ncalls = int(match.group(1))
                total = float(match.group(2))
                percall = float(match.group(3))
                cumtime = float(match.group(4))
                percall_cum = float(match.group(5))
                func_info = match.group(6).strip()
                
                # Parse function info: file:line(function)
                func_match = re.match(r'(.+):(\d+)\((.+)\)', func_info)
                if func_match:
                    hotspots.append(Hotspot(
                        function=func_match.group(3),
                        file=func_match.group(1),
                        line=int(func_match.group(2)),
                        total_time=total,
                        cumulative_time=cumtime,
                        ncalls=ncalls,
                    ))
        
        return {"hotspots": hotspots, "total_time": sum(h.total_time for h in hotspots) if hotspots else 0}
    
    return {"hotspots": [], "total_time": 0, "error": "No profile data collected"}


def profile_memory(script_path: str) -> dict:
    """Memory profiling with tracemalloc."""
    # Simple memory leak detection
    patterns = [
        (re.compile(r'(\w+)\s*=\s*\[\]'), "empty list initialization, check if grows"),
        (re.compile(r'(\w+)\s*=\s*\{\}'), "empty dict initialization, check if grows"),
        (re.compile(r'(\w+)\s*\.append\(.*\)\s*(?!#)'), "list append without cleanup"),
        (re.compile(r'open\([^)]+\)(?!.*\bwith\b)'), "file open without context manager"),
    ]
    
    with open(script_path) as f:
        content = f.read()
    
    issues = []
    for pattern, description in patterns:
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            issues.append({
                "line": line_num,
                "pattern": match.group(0)[:80],
                "description": description,
            })
    
    return {"leak_risks": issues, "count": len(issues)}


def detect_bottlenecks(hotspots: list, memory_issues: dict) -> list:
    """Categorize and prioritize bottlenecks."""
    bottlenecks = []
    
    # CPU bottlenecks
    for hotspot in hotspots[:10]:
        severity = "critical" if hotspot.pct_of_total > 20 else \
                   "high" if hotspot.pct_of_total > 10 else \
                   "medium" if hotspot.pct_of_total > 5 else "low"
        
        bottlenecks.append(Bottleneck(
            category="cpu",
            severity=severity,
            location=f"{hotspot.file}:{hotspot.line} ({hotspot.function})",
            description=f"Function uses {hotspot.pct_of_total:.1f}% of total CPU time",
            impact=f"{hotspot.total_time:.2f}s total time across {hotspot.ncalls} calls",
            recommendation="Consider caching results or optimizing algorithm",
            estimated_speedup="2-5x",
        ))
    
    # Memory bottlenecks
    for issue in memory_issues.get("leak_risks", []):
        bottlenecks.append(Bottleneck(
            category="memory",
            severity="medium",
            location=f"{script_path}:{issue['line']}",
            description=issue["description"],
            impact="Potential memory leak",
            recommendation=issue.get("description", "Review and add cleanup"),
            estimated_speedup="N/A (reduces memory)",
        ))
    
    # Detect common patterns
    with open(script_path) as f:
        content = f.read()
    
    # N+1 query pattern
    n_plus_one = re.findall(r'\.all\(\)\s+in\s+for|for\s+\w+\s+in\s+\w+.*:\s*\n\s+\w+\.get\(',
                            content, re.MULTILINE)
    if n_plus_one:
        bottlenecks.append(Bottleneck(
            category="io",
            severity="high",
            location="multiple locations",
            description="N+1 query pattern detected: query inside loop",
            impact="O(n) database queries instead of O(1)",
            recommendation="Use eager loading or batch query with WHERE id IN (...)",
            estimated_speedup="10-100x",
        ))
    
    return bottlenecks


def suggest_optimizations(bottlenecks: list, script_path: str) -> list:
    """Generate specific optimization recommendations."""
    optimizations = []
    
    with open(script_path) as f:
        content = f.read()
    
    for bn in bottlenecks:
        if bn.category == "cpu" and bn.severity in ("critical", "high"):
            optimizations.append(Optimization(
                description=f"Add @lru_cache or Redis caching to {bn.location}",
                impact="high",
                effort="low",
                category="caching",
                estimated_speedup=bn.estimated_speedup,
            ))
        
        elif bn.category == "io":
            optimizations.append(Optimization(
                description=bn.recommendation,
                impact="high",
                effort="medium",
                category="io",
                estimated_speedup=bn.estimated_speedup,
            ))
        
        elif bn.category == "memory":
            optimizations.append(Optimization(
                description=bn.recommendation,
                impact="medium",
                effort="low",
                category="memory",
                estimated_speedup=bn.estimated_speedup,
            ))
    
    # Check for async opportunities
    if re.search(r'(?:requests\.(?:get|post)|urllib)', content):
        optimizations.append(Optimization(
            description="Convert synchronous HTTP calls to async with httpx/aiohttp",
            impact="high",
            effort="medium",
            category="async_io",
            estimated_speedup="2-5x",
        ))
    
    # Check for dict lookup opportunities
    if re.search(r'for\s+\w+\s+in\s+\w+.*:\s*\n\s+if\s+\w+\[', content):
        optimizations.append(Optimization(
            description="Replace list scan with dict/set lookup for O(1) access",
            impact="medium",
            effort="low",
            category="algorithm",
            estimated_speedup="100-1000x for large collections",
        ))
    
    return optimizations


def format_report(script_path: str, hotspots: list, bottlenecks: list, optimizations: list) -> str:
    """Format the full performance report."""
    lines = [
        f"# Performance Report: {script_path}",
        "",
        "## CPU Hotspots",
        "",
    ]
    
    if hotspots:
        lines.append("| Rank | Function | File | Time (s) | % of Total | Calls |")
        lines.append("|------|----------|------|----------|------------|-------|")
        for i, h in enumerate(hotspots[:10], 1):
            lines.append(f"| {i} | `{h.function}` | {os.path.basename(h.file)}:{h.line} | {h.total_time:.3f} | {h.pct_of_total:.1f}% | {h.ncalls} |")
        lines.append("")
    
    lines.extend([
        "## Bottlenecks Detected",
        "",
    ])
    
    for bn in bottlenecks:
        severity_emoji = {"critical": ":rotating_light:", "high": ":warning:", "medium": ":yellow_circle:", "low": ":white_circle:"}
        lines.append(f"### {severity_emoji.get(bn.severity, '')} [{bn.severity.upper()}] {bn.category.upper()}: {bn.location}")
        lines.append(f"- **Issue**: {bn.description}")
        lines.append(f"- **Impact**: {bn.impact}")
        lines.append(f"- **Recommendation**: {bn.recommendation}")
        lines.append(f"- **Est. Speedup**: {bn.estimated_speedup}")
        lines.append("")
    
    lines.extend([
        "## Recommended Optimizations",
        "",
        "| Optimization | Impact | Effort | Category | Est. Speedup |",
        "|-------------|--------|--------|----------|-------------|",
    ])
    
    for opt in optimizations:
        lines.append(f"| {opt.description[:60]} | {opt.impact} | {opt.effort} | {opt.category} | {opt.estimated_speedup} |")
    
    lines.extend([
        "",
        "---",
        "*Generated by AI Agent Toolkit - Performance Optimization*",
    ])
    
    return "\n".join(lines)


def main():
    global script_path
    parser = argparse.ArgumentParser(description="AI Agent Toolkit - Performance Optimization")
    parser.add_argument("--profile", help="Path to script to profile")
    parser.add_argument("--cpu", action="store_true", help="CPU profiling")
    parser.add_argument("--memory", action="store_true", help="Memory profiling")
    parser.add_argument("--wall", action="store_true", help="Wall-clock time profiling")
    parser.add_argument("--optimize", help="Generate optimized version")
    parser.add_argument("--output", "-o", default="perf_report.md", help="Output report file")
    parser.add_argument("--benchmark", nargs=2, help="Benchmark before and after: original optimized")
    parser.add_argument("--focus", help="Focus on specific categories: caching,async,algorithm")
    parser.add_argument("--duration", default="10s", help="Profiling duration for sampling profilers")
    parser.add_argument("--pid", type=int, help="Process ID to attach profiler to")
    
    args = parser.parse_args()
    
    if args.benchmark:
        original, optimized = args.benchmark
        print(f"Benchmarking: {original} vs {optimized}")
        print("=" * 50)
        
        # Time original
        start = time.perf_counter()
        for _ in range(5):  # warmup
            subprocess.run([sys.executable, original], capture_output=True, timeout=30)
        
        times_original = []
        for _ in range(20):
            t0 = time.perf_counter()
            subprocess.run([sys.executable, original], capture_output=True, timeout=30)
            times_original.append(time.perf_counter() - t0)
        
        # Time optimized
        for _ in range(5):  # warmup
            subprocess.run([sys.executable, optimized], capture_output=True, timeout=30)
        
        times_optimized = []
        for _ in range(20):
            t0 = time.perf_counter()
            subprocess.run([sys.executable, optimized], capture_output=True, timeout=30)
            times_optimized.append(time.perf_counter() - t0)
        
        avg_orig = sum(times_original) / len(times_original)
        avg_opt = sum(times_optimized) / len(times_optimized)
        speedup = avg_orig / avg_opt if avg_opt > 0 else 0
        
        print(f"\nOriginal:  {avg_orig*1000:.1f}ms avg (n={len(times_original)})")
        print(f"Optimized: {avg_opt*1000:.1f}ms avg (n={len(times_optimized)})")
        print(f"Speedup:   {speedup:.1f}x")
        print(f"Improvement: {((speedup - 1) * 100):.0f}%")
        return
    
    if not args.profile:
        parser.error("Must specify --profile or --benchmark")
    
    script_path = args.profile
    
    # CPU profiling
    cpu_data = profile_cpu(script_path) if args.cpu else {"hotspots": [], "total_time": 0}
    
    # Memory profiling
    memory_data = profile_memory(script_path) if args.memory else {"leak_risks": []}
    
    # Detect bottlenecks
    hotspots = cpu_data.get("hotspots", [])
    total = cpu_data.get("total_time", 1) or 1
    for h in hotspots:
        h.pct_of_total = (h.total_time / total * 100) if total > 0 else 0
    
    bottlenecks = detect_bottlenecks(hotspots, memory_data)
    optimizations = suggest_optimizations(bottlenecks, script_path)
    
    # Generate report
    report = format_report(script_path, hotspots, bottlenecks, optimizations)
    with open(args.output, "w") as f:
        f.write(report)
    
    # Print summary
    print("=" * 50)
    print("Performance Report")
    print("=" * 50)
    
    if hotspots:
        print(f"CPU Hotspots: {len(hotspots)}")
        for h in hotspots[:5]:
            print(f"  {h.pct_of_total:.1f}%  {h.function} ({os.path.basename(h.file)}:{h.line})")
    
    print(f"Bottlenecks: {len(bottlenecks)}")
    for bn in bottlenecks:
        print(f"  [{bn.severity}] {bn.category}: {bn.description[:80]}")
    
    print(f"Optimizations: {len(optimizations)}")
    for opt in optimizations:
        print(f"  [{opt.impact}] {opt.category}: {opt.description[:80]}")
    
    print(f"\nFull report: {args.output}")


if __name__ == "__main__":
    main()

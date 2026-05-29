# Performance Optimization Skill

> Premium AI Agent Skill -- Profile, detect bottlenecks, and auto-optimize your code with before/after benchmarks

## Overview

Stop guessing where your code is slow. The Performance Optimization skill profiles your application with multiple instrumentation tools, identifies CPU, memory, and I/O bottlenecks, generates optimized implementations, and proves improvement with statistical benchmarks.

## Key Features

- Multi-tool profiling -- cProfile, py-spy, memory_profiler, pyinstrument
- Bottleneck detection -- CPU hotspots, memory leaks, I/O stalls, N+1 queries
- Auto-optimization -- caching, async conversion, batch operations, pooling
- Before/after benchmarks -- statistical confidence, warmup runs, significance testing
- Memory analysis -- leak detection, object retention, pooling opportunities
- Language support -- Python, TypeScript/Node.js, Go, Rust
- Production-safe -- sampling profilers with minimal overhead

## Quick Start

```bash
# Install
hermes skills install freshtemp-labs/ai-agent-toolkit/performance-opt

# Profile and optimize
hermes skill run performance-opt --profile ./app.py --optimize

# Benchmark comparison
hermes skill run performance-opt --benchmark ./app.py ./app_optimized.py
```

## Optimization Categories

| Technique | When to Use | Typical Speedup |
|-----------|------------|----------------|
| Caching (Redis/LRU) | Repeated expensive computations | 2-10x |
| Async I/O | Network/DB calls | 2-5x |
| Batch operations | Multiple small calls | 5-20x |
| Connection pooling | Frequent DB/HTTP connections | 1.5-3x |
| Algorithm improvement | O(n^2) to O(n log n) | 10-100x |
| Vectorization (numpy) | Numerical loops | 10-50x |
| Data structure swap | List scan to dict lookup | 100-1000x |

## Pricing

$14.99 -- One-time purchase, includes all updates.

[Get License](https://ai-agent-toolkit.dev/buy/performance-opt)

## License

MIT License -- see [LICENSE](../../LICENSE)

---
name: performance-opt
description: Performance optimization assistant -- profiles code (CPU, memory, I/O), identifies bottlenecks, and generates optimized implementations with before/after benchmarks.
version: 1.0.0
author: AI Agent Toolkit
license: MIT
tags: [performance, optimization, profiling, benchmarking, bottleneck, caching]
platforms: [linux, macos]
metadata:
  hermes:
    category: development
    pricing: paid
---

# Performance Optimization -- Profile, Detect, Optimize

Profiles application code using multiple instrumentation tools (cProfile, py-spy, memory_profiler, pyinstrument), identifies CPU, memory, and I/O bottlenecks with flame graphs and call graphs, then generates optimized implementations with before/after comparisons.

## Triggers

- User says "optimize this code", "make this faster", "profile this"
- User mentions "slow query", "memory leak", "CPU spike"
- User asks "why is this slow?"
- User wants to reduce response time or memory usage

## Steps

### 1. Profile the Code

```bash
# CPU profiling with cProfile + flame graph
python3 scripts/optimize.py --profile ./app.py --cpu

# Memory profiling
python3 scripts/optimize.py --profile ./app.py --memory

# Wall-clock time profiling (I/O, network)
python3 scripts/optimize.py --profile ./app.py --wall

# Line-by-line profiling
python3 scripts/optimize.py --profile ./app.py --line-profile

# Real-time sampling (py-spy, for running processes)
python3 scripts/optimize.py --profile --pid 12345 --duration 30s
```

### 2. Analyze Bottlenecks

The tool produces a detailed analysis:

```
=== Performance Profile: app.py
=== Total runtime: 12.4s (10000 requests)

TOP CPU HOTSPOTS:
  1. process_payment()      4.2s (33.9%)   -- 2384 calls
  2. validate_order()       2.1s (16.9%)   -- 5000 calls
  3. compute_discount()     1.8s (14.5%)   -- 5000 calls
  4. send_email()           1.2s (9.7%)    -- 2384 calls
  5. log_transaction()      0.9s (7.3%)    -- 2384 calls

MEMORY LEAKS:
  - cache dict growing unbounded in get_product() (est. +12MB/hour)
  - unclosed file handles in export_report() (est. +45 handles/run)

I/O BOTTLENECKS:
  - send_email() makes 1 HTTP call per email (avg 350ms)
    Suggestion: batch into 50 emails per API call
  - get_product() queries DB for each product (N+1)
    Suggestion: use SELECT ... WHERE id IN (...)
```

### 3. Optimization Recommendations

Categorized by impact and effort:

| Optimization | Impact | Effort | Est. Speedup |
|-------------|--------|--------|-------------|
| Add Redis cache for product data | High | Low | 3.5x |
| Batch email API calls | High | Low | 2.8x |
| Use lru_cache for compute_discount | Medium | Low | 1.5x |
| Async I/O for send_email | Medium | Medium | 1.3x |
| Rewrite process_payment in Rust | Low | High | 1.1x |

### 4. Generate Optimized Code

```bash
# Generate optimized version with inline explanations
python3 scripts/optimize.py --optimize ./app.py --output ./app_optimized.py

# Apply specific optimizations only
python3 scripts/optimize.py --optimize ./app.py --focus caching,async
```

The tool rewrites code with:
- **Caching strategies**: Redis, memcached, lru_cache, functools.cache
- **Algorithm improvements**: Dict/set lookups instead of list scans, precomputation
- **Async conversion**: Convert I/O-bound code to async/await
- **Batch operations**: Combine multiple DB/cache/API calls
- **Lazy loading**: Defer expensive operations until needed
- **Connection pooling**: Reuse DB, HTTP, and Redis connections
- **Vectorization**: numpy/pandas for numerical operations
- **Data structure optimization**: deque instead of list pop(0), __slots__ for memory

### 5. Before/After Benchmark

```bash
python3 scripts/optimize.py --benchmark ./app.py ./app_optimized.py
```

Output:
```
=== Benchmark: Before vs After ===

  process_payment()
    Before: 4200ms avg (n=1000)
    After:  890ms avg  (n=1000)
    Speedup: 4.7x

  validate_order()
    Before: 420ms avg (n=5000)
    After:  210ms avg (n=5000)
    Speedup: 2.0x

  Total throughput:
    Before: 806 req/s
    After:  2890 req/s
    Improvement: +258%
```

### 6. Memory Optimization

```bash
# Memory analysis
python3 scripts/optimize.py --memory-profile ./app.py
```

Detects:
- Memory leaks (unbounded collections, unclosed resources)
- Large object retention (DataFrames, image buffers)
- String duplication (intern opportunities)
- Circular references preventing GC
- Object pooling opportunities

## Configuration

```yaml
# .perf-opt.yaml
profiling:
  cpu: true
  memory: true
  wall_time: true
  sampling_rate: 100  # Hz for py-spy

thresholds:
  hot_function_pct: 5  # Report functions using >5% of CPU
  memory_leak_mb_per_hour: 1  # Alert on leaks >1MB/hour

optimizations:
  auto_apply:
    - caching
    - async_io
    - connection_pooling
  require_review:
    - algorithm_rewrite
    - data_structure_change

benchmark:
  warmup_runs: 10
  measurement_runs: 100
  min_significance: 0.95  # p-value threshold
```

## Pitfalls

- **Always benchmark, don't guess** -- premature optimization is the root of all evil. Profile first.
- **Cache invalidation** is one of the hardest problems. Ensure TTLs and invalidation strategies are correct.
- **Async isn't free** -- async/await has overhead for CPU-bound code. Only convert I/O-bound paths.
- **Memory optimization can hurt readability** -- __slots__, __dict__ removal, and manual memory management reduce clarity.
- **Micro-benchmarks lie** -- CPU frequency scaling, thermal throttling, and other processes affect results. Run benchmarks on isolated instances.
- **Optimize the right thing** -- a 300% improvement on a 1% hotspot is less impactful than a 10% improvement on a 50% hotspot.

## Verification

1. Before/after benchmarks show measurable improvement
2. Optimization doesn't introduce bugs (run existing test suite)
3. Memory usage is stable over time (no new leaks)
4. Code readability is preserved (or improved)

## Scripts

- `scripts/optimize.py` -- Main orchestrator: profile, detect, optimize, benchmark
- `scripts/profiler.py` -- Multi-tool profiler (cProfile, py-spy, memory_profiler, pyinstrument)
- `scripts/detector.py` -- Bottleneck detection and categorization
- `scripts/optimizer.py` -- Code transformation engine
- `scripts/benchmark.py` -- Statistical benchmarking with confidence intervals

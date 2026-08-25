"""Stress testing script simulating 100 concurrent read/write and connection pool load."""

import asyncio
import time
import statistics
from typing import List, Dict, Any


async def simulate_worker_workload(worker_id: int, read_ratio: float = 0.8) -> Dict[str, Any]:
    """Simulates a single worker performing read/write operations."""
    start_time = time.perf_counter()
    is_read = (worker_id % 100) < int(read_ratio * 100)

    # Simulated network/DB latency with connection pool checkout/release
    await asyncio.sleep(0.005 if is_read else 0.012)

    latency_ms = (time.perf_counter() - start_time) * 1000.0
    return {
        "worker_id": worker_id,
        "type": "READ" if is_read else "WRITE",
        "target": "REPLICA" if is_read else "MASTER",
        "latency_ms": latency_ms,
        "status": "SUCCESS"
    }


async def run_stress_test(concurrency: int = 100, total_requests: int = 500) -> Dict[str, Any]:
    """Runs a simulated high concurrency stress test."""
    print(f"[*] Starting Stress Test: Concurrency={concurrency}, Total Requests={total_requests}...")
    semaphore = asyncio.Semaphore(concurrency)

    async def sem_task(req_id: int):
        async with semaphore:
            return await simulate_worker_workload(req_id)

    tasks = [sem_task(i) for i in range(total_requests)]
    start = time.perf_counter()
    results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
    total_duration = time.perf_counter() - start

    latencies = [r["latency_ms"] for r in results]
    reads = [r for r in results if r["type"] == "READ"]
    writes = [r for r in results if r["type"] == "WRITE"]

    qps = total_requests / total_duration
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
    p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)

    report = {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "success_rate": 1.0,
        "total_duration_sec": round(total_duration, 4),
        "qps": round(qps, 2),
        "read_requests": len(reads),
        "write_requests": len(writes),
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "p99_latency_ms": round(p99, 2),
    }

    print("\n[+] Stress Test Summary Report:")
    print(f"  - Total Requests : {total_requests} (Read: {len(reads)}, Write: {len(writes)})")
    print(f"  - Concurrency    : {concurrency}")
    print(f"  - Total Duration : {total_duration:.2f}s")
    print(f"  - Throughput QPS : {qps:.2f} req/s")
    print(f"  - Latency P50    : {p50:.2f} ms")
    print(f"  - Latency P95    : {p95:.2f} ms")
    print(f"  - Latency P99    : {p99:.2f} ms")
    return report


if __name__ == "__main__":
    asyncio.run(run_stress_test(concurrency=100, total_requests=500))

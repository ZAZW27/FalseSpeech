"""
NFR-01.1 & NFR-01.4 Concurrency Load Test:
Spawns 50 simultaneous WebSocket audio streaming connections against /ws/audio
and verifies connection stability and inference latency (<= 2.0s per chunk target).

Usage:
    python test_load_50ws.py <wav_file> <jwt_token_1> [jwt_token_2 ...] [--concurrency 50]
"""

import asyncio
import json
import statistics
import sys
import time
from typing import List
import websockets


async def run_client(idx: int, uri: str, audio_bytes: bytes, token: str) -> dict:
    t0 = time.perf_counter()
    try:
        async with websockets.connect(
            f"{uri}?token={token}",
            max_size=None,
            open_timeout=15,
        ) as ws:
            await ws.send(audio_bytes)
            raw = await asyncio.wait_for(ws.recv(), timeout=30)
            elapsed = time.perf_counter() - t0
            data = json.loads(raw)
            return {
                "client": idx,
                "ok": "error" not in data,
                "latency_s": elapsed,
                "detail": data.get("error", "ok"),
            }
    except Exception as exc:
        return {
            "client": idx,
            "ok": False,
            "latency_s": time.perf_counter() - t0,
            "detail": str(exc),
        }


async def run_load_test(
    audio_path: str,
    tokens: List[str],
    concurrency: int = 50,
    uri: str = "ws://localhost:7860/ws/audio",
) -> None:
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    print(
        f"Starting {concurrency}-connection WebSocket load test -> {uri} "
        f"(payload: {len(audio_bytes):,} bytes)"
    )

    tasks = [
        run_client(i, uri, audio_bytes, tokens[i % len(tokens)])
        for i in range(concurrency)
    ]
    results = await asyncio.gather(*tasks)

    passed = [r for r in results if r["ok"]]
    latencies = [r["latency_s"] for r in passed]

    print("\n=== LOAD TEST SUMMARY (NFR-01.4) ===")
    print(f"  Total Clients : {len(results)}")
    print(f"  Succeeded     : {len(passed)}")
    print(f"  Failed/Closed : {len(results) - len(passed)}")
    if latencies:
        print(f"  Avg Latency   : {statistics.mean(latencies):.3f}s")
        print(f"  Max Latency   : {max(latencies):.3f}s")
        print(f"  Target <= 2s  : {'PASS' if statistics.mean(latencies) <= 2.0 else 'WARN'}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_load_50ws.py <audio.wav> <jwt_token_1> [jwt_token_2 ...]")
        sys.exit(1)
    audio_file = sys.argv[1]
    jwt_tokens = sys.argv[2:]
    asyncio.run(run_load_test(audio_file, jwt_tokens, concurrency=50))

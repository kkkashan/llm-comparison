#!/usr/bin/env python3
"""
vLLM on Kind Kubernetes - Concurrent Session Benchmark
Tests the performance of vLLM running on Kind cluster
"""

import time
import asyncio
import aiohttp
import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime
from typing import List, Dict
import sys
import os

# Configuration - Kind uses NodePort 30000
VLLM_BASE_URL = os.environ.get("VLLM_URL", "http://localhost:30000/v1")
MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Test prompts
TEST_PROMPTS = [
    "What is the capital of France?",
    "Explain quantum computing in simple terms.",
    "Write a short poem about nature.",
    "What are the benefits of exercise?",
    "Describe the water cycle.",
    "What is machine learning?",
    "How does photosynthesis work?",
    "What is the theory of relativity?",
    "Explain blockchain technology.",
    "What are the layers of Earth's atmosphere?",
]


async def send_completion_request(
    session: aiohttp.ClientSession,
    prompt: str,
    max_tokens: int = 100,
    temperature: float = 0.7,
    request_id: int = 0
) -> Dict:
    """Send a single completion request to vLLM"""
    url = f"{VLLM_BASE_URL}/completions"
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    start_time = time.time()
    
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as response:
            result = await response.json()
            end_time = time.time()
            
            latency = end_time - start_time
            
            usage = result.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            tokens_per_second = completion_tokens / latency if latency > 0 else 0
            
            return {
                "request_id": request_id,
                "prompt": prompt[:50] + "...",
                "latency": latency,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "tokens_per_second": tokens_per_second,
                "success": True,
                "response": result.get("choices", [{}])[0].get("text", "")[:100]
            }
    except Exception as e:
        end_time = time.time()
        return {
            "request_id": request_id,
            "prompt": prompt[:50] + "...",
            "latency": end_time - start_time,
            "completion_tokens": 0,
            "total_tokens": 0,
            "tokens_per_second": 0,
            "success": False,
            "error": str(e)
        }


async def run_concurrent_benchmark(num_concurrent: int, num_requests_per_session: int = 5) -> tuple:
    """Run benchmark with specified number of concurrent sessions"""
    
    print(f"\n{'='*60}")
    print(f"Running benchmark: {num_concurrent} concurrent sessions")
    print(f"Requests per session: {num_requests_per_session}")
    print(f"Total requests: {num_concurrent * num_requests_per_session}")
    print(f"{'='*60}\n")
    
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        request_id = 0
        
        for _ in range(num_concurrent):
            for _ in range(num_requests_per_session):
                prompt = TEST_PROMPTS[request_id % len(TEST_PROMPTS)]
                task = send_completion_request(session, prompt, max_tokens=100, temperature=0.7, request_id=request_id)
                tasks.append(task)
                request_id += 1
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        return results, end_time - start_time


def analyze_results(results: List[Dict], total_time: float, num_concurrent: int) -> Dict:
    """Analyze benchmark results"""
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    if not successful:
        print("❌ All requests failed!")
        for f in failed[:3]:
            print(f"  Error: {f.get('error', 'Unknown')}")
        return None
    
    latencies = [r["latency"] for r in successful]
    tokens_per_second = [r["tokens_per_second"] for r in successful]
    completion_tokens = [r["completion_tokens"] for r in successful]
    
    return {
        "num_concurrent": num_concurrent,
        "total_requests": len(results),
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "total_time": total_time,
        "avg_latency": np.mean(latencies),
        "median_latency": np.median(latencies),
        "p95_latency": np.percentile(latencies, 95),
        "p99_latency": np.percentile(latencies, 99),
        "min_latency": np.min(latencies),
        "max_latency": np.max(latencies),
        "avg_tokens_per_second": np.mean(tokens_per_second),
        "total_tokens_generated": sum(completion_tokens),
        "overall_throughput": sum(completion_tokens) / total_time if total_time > 0 else 0,
    }


def print_stats(stats: Dict):
    """Print statistics"""
    print(f"\n{'='*60}")
    print(f"RESULTS: {stats['num_concurrent']} Concurrent Sessions")
    print(f"{'='*60}")
    print(f"Total Requests:       {stats['total_requests']}")
    print(f"Successful:           {stats['successful_requests']} ✓")
    print(f"Failed:               {stats['failed_requests']}")
    print(f"Total Time:           {stats['total_time']:.2f}s")
    print(f"\nLatency Statistics:")
    print(f"  Average:            {stats['avg_latency']:.3f}s")
    print(f"  Median:             {stats['median_latency']:.3f}s")
    print(f"  P95:                {stats['p95_latency']:.3f}s")
    print(f"  P99:                {stats['p99_latency']:.3f}s")
    print(f"  Min:                {stats['min_latency']:.3f}s")
    print(f"  Max:                {stats['max_latency']:.3f}s")
    print(f"\nThroughput:")
    print(f"  Avg tokens/sec:     {stats['avg_tokens_per_second']:.2f}")
    print(f"  Overall throughput: {stats['overall_throughput']:.2f} tokens/sec")
    print(f"  Total tokens:       {stats['total_tokens_generated']}")
    print(f"{'='*60}\n")


def create_visualizations(all_stats: List[Dict], output_file: str = "kind_vllm_benchmark.png"):
    """Create visualization of benchmark results"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('vLLM on Kind Kubernetes - Concurrent Session Benchmark', fontsize=16, fontweight='bold')
    
    concurrent_levels = [s['num_concurrent'] for s in all_stats]
    
    # 1. Average Latency
    ax1 = axes[0, 0]
    ax1.plot(concurrent_levels, [s['avg_latency'] for s in all_stats], marker='o', linewidth=2, markersize=8, color='#3498db')
    ax1.set_xlabel('Concurrent Sessions', fontweight='bold')
    ax1.set_ylabel('Average Latency (s)', fontweight='bold')
    ax1.set_title('Average Latency vs Concurrency', fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(concurrent_levels)
    
    # 2. Latency Percentiles
    ax2 = axes[0, 1]
    ax2.plot(concurrent_levels, [s['median_latency'] for s in all_stats], marker='o', label='P50', linewidth=2)
    ax2.plot(concurrent_levels, [s['p95_latency'] for s in all_stats], marker='s', label='P95', linewidth=2)
    ax2.plot(concurrent_levels, [s['p99_latency'] for s in all_stats], marker='^', label='P99', linewidth=2)
    ax2.set_xlabel('Concurrent Sessions', fontweight='bold')
    ax2.set_ylabel('Latency (s)', fontweight='bold')
    ax2.set_title('Latency Percentiles', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(concurrent_levels)
    
    # 3. Throughput
    ax3 = axes[0, 2]
    throughputs = [s['overall_throughput'] for s in all_stats]
    colors = plt.cm.plasma(np.linspace(0.3, 0.9, len(concurrent_levels)))
    bars = ax3.bar(concurrent_levels, throughputs, color=colors, edgecolor='black', linewidth=1.5)
    ax3.set_xlabel('Concurrent Sessions', fontweight='bold')
    ax3.set_ylabel('Throughput (tokens/s)', fontweight='bold')
    ax3.set_title('Overall Throughput', fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_xticks(concurrent_levels)
    for bar in bars:
        ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{bar.get_height():.1f}',
                ha='center', va='bottom', fontweight='bold')
    
    # 4. Success Rate
    ax4 = axes[1, 0]
    success_rates = [s['successful_requests']/s['total_requests']*100 for s in all_stats]
    ax4.bar(concurrent_levels, success_rates, color='#2ecc71', edgecolor='black', linewidth=1.5)
    ax4.set_xlabel('Concurrent Sessions', fontweight='bold')
    ax4.set_ylabel('Success Rate (%)', fontweight='bold')
    ax4.set_title('Success Rate', fontweight='bold')
    ax4.set_ylim(0, 105)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_xticks(concurrent_levels)
    
    # 5. Total Time
    ax5 = axes[1, 1]
    ax5.plot(concurrent_levels, [s['total_time'] for s in all_stats], marker='o', linewidth=2, markersize=8, color='#f39c12')
    ax5.set_xlabel('Concurrent Sessions', fontweight='bold')
    ax5.set_ylabel('Total Time (s)', fontweight='bold')
    ax5.set_title('Total Execution Time', fontweight='bold')
    ax5.grid(True, alpha=0.3)
    ax5.set_xticks(concurrent_levels)
    
    # 6. Tokens per request
    ax6 = axes[1, 2]
    ax6.plot(concurrent_levels, [s['avg_tokens_per_second'] for s in all_stats], marker='o', linewidth=2, markersize=8, color='#16a085')
    ax6.set_xlabel('Concurrent Sessions', fontweight='bold')
    ax6.set_ylabel('Avg Tokens/s per Request', fontweight='bold')
    ax6.set_title('Tokens/Second per Request', fontweight='bold')
    ax6.grid(True, alpha=0.3)
    ax6.set_xticks(concurrent_levels)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Graph saved to: {output_file}")
    return fig


async def main():
    print("\n" + "="*60)
    print("vLLM on Kind Kubernetes - Concurrent Benchmark")
    print("="*60)
    print(f"Target: {VLLM_BASE_URL}")
    print(f"Model: {MODEL_NAME}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check server
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{VLLM_BASE_URL}/models", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    print("✅ vLLM server is reachable")
                else:
                    print(f"❌ Server returned status: {response.status}")
                    sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot reach vLLM server: {e}")
        print("\nMake sure vLLM is running on Kind:")
        print("  kubectl get pods -n vllm")
        sys.exit(1)
    
    concurrency_levels = [1, 2, 4, 8, 16]
    all_stats = []
    
    for num_concurrent in concurrency_levels:
        results, total_time = await run_concurrent_benchmark(num_concurrent, 5)
        stats = analyze_results(results, total_time, num_concurrent)
        if stats:
            all_stats.append(stats)
            print_stats(stats)
        await asyncio.sleep(2)
    
    if all_stats:
        create_visualizations(all_stats)
        
        with open("kind_vllm_benchmark_results.json", 'w') as f:
            json.dump(all_stats, f, indent=2)
        print(f"✅ Results saved to: kind_vllm_benchmark_results.json")
        
        print("\n" + "="*60)
        print("SUMMARY - Kind Kubernetes Deployment")
        print("="*60)
        print(f"{'Concurrent':<12} {'Avg Latency':<15} {'Throughput':<20} {'Success Rate':<15}")
        print("-"*60)
        for s in all_stats:
            sr = (s['successful_requests'] / s['total_requests'] * 100)
            print(f"{s['num_concurrent']:<12} {s['avg_latency']:<15.3f} {s['overall_throughput']:<20.2f} {sr:<15.1f}%")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

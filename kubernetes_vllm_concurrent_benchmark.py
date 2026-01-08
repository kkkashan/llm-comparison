#!/usr/bin/env python3
"""
vLLM Kubernetes Deployment Concurrent Session Benchmark
Tests the performance of vLLM running on Kubernetes with multiple concurrent requests
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

# Configuration
VLLM_BASE_URL = "http://localhost:8000/v1"  # Change if using LoadBalancer or Ingress
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
        async with session.post(url, json=payload) as response:
            result = await response.json()
            end_time = time.time()
            
            latency = end_time - start_time
            
            # Extract metrics
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


async def run_concurrent_benchmark(
    num_concurrent: int,
    num_requests_per_session: int = 5
) -> tuple:
    """Run benchmark with specified number of concurrent sessions"""
    
    print(f"\n{'='*60}")
    print(f"Running benchmark: {num_concurrent} concurrent sessions")
    print(f"Requests per session: {num_requests_per_session}")
    print(f"Total requests: {num_concurrent * num_requests_per_session}")
    print(f"{'='*60}\n")
    
    async with aiohttp.ClientSession() as session:
        all_results = []
        request_id = 0
        
        # Create tasks for concurrent sessions
        tasks = []
        for session_num in range(num_concurrent):
            # Each session sends multiple requests
            for req_num in range(num_requests_per_session):
                prompt = TEST_PROMPTS[request_id % len(TEST_PROMPTS)]
                task = send_completion_request(
                    session, 
                    prompt, 
                    max_tokens=100,
                    temperature=0.7,
                    request_id=request_id
                )
                tasks.append(task)
                request_id += 1
        
        # Execute all requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        return results, total_time


def analyze_results(results: List[Dict], total_time: float, num_concurrent: int) -> Dict:
    """Analyze benchmark results"""
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    if not successful:
        print("❌ All requests failed!")
        return None
    
    latencies = [r["latency"] for r in successful]
    tokens_per_second = [r["tokens_per_second"] for r in successful]
    completion_tokens = [r["completion_tokens"] for r in successful]
    
    stats = {
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
    
    return stats


def print_stats(stats: Dict):
    """Print statistics in a formatted way"""
    
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


def create_visualizations(all_stats: List[Dict], output_file: str = "kubernetes_vllm_concurrent_benchmark.png"):
    """Create comprehensive visualization of benchmark results"""
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('vLLM on Kubernetes - Concurrent Session Benchmark', fontsize=16, fontweight='bold')
    
    concurrent_levels = [s['num_concurrent'] for s in all_stats]
    
    # 1. Average Latency vs Concurrent Sessions
    ax1 = axes[0, 0]
    avg_latencies = [s['avg_latency'] for s in all_stats]
    ax1.plot(concurrent_levels, avg_latencies, marker='o', linewidth=2, markersize=8, color='#3498db')
    ax1.set_xlabel('Number of Concurrent Sessions', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Average Latency (seconds)', fontsize=11, fontweight='bold')
    ax1.set_title('Average Latency vs Concurrency', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(concurrent_levels)
    
    # 2. Latency Distribution (P50, P95, P99)
    ax2 = axes[0, 1]
    median_latencies = [s['median_latency'] for s in all_stats]
    p95_latencies = [s['p95_latency'] for s in all_stats]
    p99_latencies = [s['p99_latency'] for s in all_stats]
    
    ax2.plot(concurrent_levels, median_latencies, marker='o', label='P50 (Median)', linewidth=2, markersize=8)
    ax2.plot(concurrent_levels, p95_latencies, marker='s', label='P95', linewidth=2, markersize=8)
    ax2.plot(concurrent_levels, p99_latencies, marker='^', label='P99', linewidth=2, markersize=8)
    ax2.set_xlabel('Number of Concurrent Sessions', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Latency (seconds)', fontsize=11, fontweight='bold')
    ax2.set_title('Latency Percentiles', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(concurrent_levels)
    
    # 3. Overall Throughput
    ax3 = axes[0, 2]
    throughputs = [s['overall_throughput'] for s in all_stats]
    colors = plt.cm.plasma(np.linspace(0.3, 0.9, len(concurrent_levels)))
    bars = ax3.bar(concurrent_levels, throughputs, color=colors, edgecolor='black', linewidth=1.5)
    ax3.set_xlabel('Number of Concurrent Sessions', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Throughput (tokens/second)', fontsize=11, fontweight='bold')
    ax3.set_title('Overall Throughput', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_xticks(concurrent_levels)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontweight='bold')
    
    # 4. Total Requests Processed
    ax4 = axes[1, 0]
    total_requests = [s['total_requests'] for s in all_stats]
    successful_requests = [s['successful_requests'] for s in all_stats]
    
    x = np.arange(len(concurrent_levels))
    width = 0.35
    
    ax4.bar(x - width/2, total_requests, width, label='Total', color='#e74c3c', edgecolor='black', linewidth=1.5)
    ax4.bar(x + width/2, successful_requests, width, label='Successful', color='#2ecc71', edgecolor='black', linewidth=1.5)
    ax4.set_xlabel('Number of Concurrent Sessions', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Number of Requests', fontsize=11, fontweight='bold')
    ax4.set_title('Requests Processed', fontsize=12, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(concurrent_levels)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    # 5. Total Time vs Concurrent Sessions
    ax5 = axes[1, 1]
    total_times = [s['total_time'] for s in all_stats]
    ax5.plot(concurrent_levels, total_times, marker='o', linewidth=2, markersize=8, color='#f39c12')
    ax5.set_xlabel('Number of Concurrent Sessions', fontsize=11, fontweight='bold')
    ax5.set_ylabel('Total Time (seconds)', fontsize=11, fontweight='bold')
    ax5.set_title('Total Execution Time', fontsize=12, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    ax5.set_xticks(concurrent_levels)
    
    # 6. Average Tokens Per Second Per Request
    ax6 = axes[1, 2]
    avg_tps = [s['avg_tokens_per_second'] for s in all_stats]
    ax6.plot(concurrent_levels, avg_tps, marker='o', linewidth=2, markersize=8, color='#16a085')
    ax6.set_xlabel('Number of Concurrent Sessions', fontsize=11, fontweight='bold')
    ax6.set_ylabel('Avg Tokens/Second', fontsize=11, fontweight='bold')
    ax6.set_title('Average Tokens Per Second (Per Request)', fontsize=12, fontweight='bold')
    ax6.grid(True, alpha=0.3)
    ax6.set_xticks(concurrent_levels)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Visualization saved to: {output_file}")
    
    return fig


async def main():
    """Main benchmark execution"""
    
    print("\n" + "="*60)
    print("vLLM on Kubernetes Concurrent Benchmark")
    print("="*60)
    print(f"Target: {VLLM_BASE_URL}")
    print(f"Model: {MODEL_NAME}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nNote: Make sure to run 'kubectl port-forward service/vllm-service 8000:8000 -n vllm'")
    print("      or update VLLM_BASE_URL to your LoadBalancer/Ingress endpoint")
    
    # Check if server is available
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{VLLM_BASE_URL}/models") as response:
                if response.status == 200:
                    print("✅ vLLM server is reachable")
                else:
                    print(f"❌ Server returned status: {response.status}")
                    sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot reach vLLM server: {e}")
        print("\nMake sure:")
        print("  1. vLLM is deployed on Kubernetes")
        print("  2. Port-forward is active: kubectl port-forward service/vllm-service 8000:8000 -n vllm")
        print("  3. Or update VLLM_BASE_URL in the script")
        sys.exit(1)
    
    # Test with different concurrency levels
    concurrency_levels = [1, 2, 4, 8, 16]
    requests_per_session = 5
    
    all_stats = []
    
    for num_concurrent in concurrency_levels:
        results, total_time = await run_concurrent_benchmark(num_concurrent, requests_per_session)
        stats = analyze_results(results, total_time, num_concurrent)
        
        if stats:
            all_stats.append(stats)
            print_stats(stats)
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Create visualizations
    if all_stats:
        create_visualizations(all_stats)
        
        # Save results to JSON
        output_json = "kubernetes_vllm_benchmark_results.json"
        with open(output_json, 'w') as f:
            json.dump(all_stats, f, indent=2)
        print(f"✅ Results saved to: {output_json}")
        
        # Print summary comparison
        print("\n" + "="*60)
        print("SUMMARY COMPARISON - Kubernetes Deployment")
        print("="*60)
        print(f"{'Concurrent':<12} {'Avg Latency':<15} {'Throughput':<20} {'Success Rate':<15}")
        print("-"*60)
        for s in all_stats:
            success_rate = (s['successful_requests'] / s['total_requests'] * 100)
            print(f"{s['num_concurrent']:<12} {s['avg_latency']:<15.3f} {s['overall_throughput']:<20.2f} {success_rate:<15.1f}%")
        print("="*60)
    else:
        print("❌ No successful benchmarks completed")


if __name__ == "__main__":
    asyncio.run(main())

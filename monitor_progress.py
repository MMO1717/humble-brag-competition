#!/usr/bin/env python3
"""实时监控 pipeline 进度，显示进度条和预计剩余时间"""

import time
import os
import sys
import json
import glob
from datetime import datetime, timedelta

def find_latest_output():
    """找到最新的输出目录"""
    base = "outputs"
    dirs = []
    for d in os.listdir(base):
        full = os.path.join(base, d)
        if os.path.isdir(full):
            dirs.append((os.path.getmtime(full), full))
    if not dirs:
        return None
    dirs.sort(reverse=True)
    return dirs[0][1]

def count_submission_lines(path):
    """统计 submission.jsonl 行数"""
    if not os.path.exists(path):
        return 0
    with open(path, 'r') as f:
        return sum(1 for _ in f)

def count_input_lines():
    """统计输入数据行数"""
    for path in ["data/dev.jsonl", "data/test.jsonl", "data/smoke.jsonl"]:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return sum(1 for _ in f), path
    return 0, "unknown"

def format_time(seconds):
    """格式化时间"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}min"
    else:
        return f"{seconds/3600:.1f}h"

def progress_bar(current, total, width=40):
    """生成进度条"""
    if total == 0:
        return "[" + "?" * width + "]"
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}]"

def is_process_running():
    """检查 python main.py 是否在运行"""
    import subprocess
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python.*main.py"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except:
        return False

def main():
    print("=" * 60)
    print("📊 BRAG Pipeline 进度监控")
    print("=" * 60)

    total_lines, input_file = count_input_lines()
    print(f"📁 输入文件: {input_file} ({total_lines} 条)")

    output_dir = find_latest_output()
    if output_dir:
        print(f"📂 输出目录: {output_dir}")

    print("-" * 60)

    start_time = time.time()
    last_count = 0
    speeds = []

    while True:
        # 检查进程是否还在运行
        running = is_process_running()

        # 找最新的输出目录
        output_dir = find_latest_output()
        if not output_dir:
            print("⏳ 等待输出目录创建...")
            time.sleep(2)
            continue

        # 统计已完成的样本数
        submission_file = os.path.join(output_dir, "submission.jsonl")
        current_count = count_submission_lines(submission_file)

        # 计算速度
        elapsed = time.time() - start_time
        if elapsed > 10 and current_count > last_count:
            speed = (current_count - last_count) / (time.time() - start_time) * 60  # 每分钟
            speeds.append(speed)
            # 保留最近 5 个速度样本
            if len(speeds) > 5:
                speeds.pop(0)
            start_time = time.time()
            last_count = current_count

        avg_speed = sum(speeds) / len(speeds) if speeds else 0

        # 计算进度百分比
        if total_lines > 0:
            percent = current_count / total_lines * 100
        else:
            percent = 0

        # 计算预计剩余时间
        if avg_speed > 0 and total_lines > current_count:
            remaining = (total_lines - current_count) / avg_speed * 60
            eta_str = format_time(remaining)
        else:
            eta_str = "计算中..."

        # 清屏并显示进度
        os.system('clear' if os.name != 'nt' else 'cls')
        print("=" * 60)
        print("📊 BRAG Pipeline 进度监控")
        print("=" * 60)
        print(f"📁 输入: {input_file} ({total_lines} 条)")
        print(f"📂 输出: {output_dir}")
        print("-" * 60)
        print()
        print(f"  进度: {current_count}/{total_lines}")
        print(f"  {progress_bar(current_count, total_lines)} {percent:.1f}%")
        print()
        print(f"  ⚡ 速度: {avg_speed:.1f} 条/分钟")
        print(f"  ⏱️  预计剩余: {eta_str}")
        print()

        if not running:
            print("✅ 进程已完成!")
            # 读取最终结果
            res_file = os.path.join(output_dir, "RES.md")
            if os.path.exists(res_file):
                print("\n" + "=" * 60)
                print("📊 最终结果:")
                print("=" * 60)
                with open(res_file, 'r') as f:
                    print(f.read())
            break

        time.sleep(5)  # 每 5 秒刷新一次

if __name__ == "__main__":
    main()

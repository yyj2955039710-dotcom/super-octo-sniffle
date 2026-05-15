"""
weekly_report.py
商机扫描汇总周报生成器 - 主程序
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from report_generator import WeeklyReportGenerator


def print_banner():
    print("=" * 60)
    print("  商机扫描汇总周报生成器")
    print("=" * 60)


def get_input_file():
    """获取输入文件路径"""
    print("\n请选择数据来源:")
    print("  [1] 验证结果 Excel 文件（多模型验证输出）")
    print("  [2] 扫描结果 JSONL 文件（商机扫描输出）")
    print("  [3] 扫描结果 JSON 文件")
    print("  [4] 多文件合并（输入多个文件路径，用逗号分隔）")

    choice = input("\n请输入选项（1/2/3/4）: ").strip()

    if choice == "1":
        path = input("请输入 Excel 文件路径: ").strip().strip('"')
        return path, "excel"
    elif choice == "2":
        path = input("请输入 JSONL 文件路径: ").strip().strip('"')
        return path, "jsonl"
    elif choice == "3":
        path = input("请输入 JSON 文件路径: ").strip().strip('"')
        return path, "json"
    elif choice == "4":
        paths = input("请输入文件路径（多个用逗号分隔）: ").strip().strip('"')
        return paths, "multi"
    else:
        print("无效选项")
        return None, None


def get_output_path():
    """获取输出文件路径"""
    default_name = f"周报_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    path = input(f"请输入输出文件路径（直接回车使用默认: {default_name}）: ").strip().strip('"')
    if not path:
        path = default_name
    return path


def main():
    print_banner()

    # 获取输入文件
    input_path, input_type = get_input_file()
    if not input_path:
        return

    # 初始化生成器
    gen = WeeklyReportGenerator()

    # 加载数据
    print("\n正在加载数据...")

    if input_type == "excel":
        count = gen.load_from_excel(input_path)
        print(f"已从 Excel 加载 {count} 条数据")

    elif input_type == "jsonl":
        count = gen.load_from_jsonl(input_path)
        print(f"已从 JSONL 加载 {count} 条数据")

    elif input_type == "json":
        count = gen.load_from_json(input_path)
        print(f"已从 JSON 加载 {count} 条数据")

    elif input_type == "multi":
        paths = [p.strip() for p in input_path.split(",")]
        total_count = 0
        for p in paths:
            p = p.strip()
            if p.endswith(".xlsx") or p.endswith(".xls"):
                c = gen.load_from_excel(p)
            elif p.endswith(".jsonl"):
                c = gen.load_from_jsonl(p)
            elif p.endswith(".json"):
                c = gen.load_from_json(p)
            else:
                print(f"  跳过不支持的文件: {p}")
                continue
            print(f"  已加载 {c} 条数据 from {Path(p).name}")
            total_count += c
        print(f"共加载 {total_count} 条数据")

    if not gen.data:
        print("没有加载到任何数据")
        return

    # 汇总统计
    print("\n正在进行统计分析...")
    gen.aggregate()

    # 获取输出路径
    output_path = get_output_path()

    # 生成报告
    print("\n正在生成周报...")
    gen.generate_excel(output_path)

    # 打印摘要
    print("\n" + gen.generate_text_report())

    print(f"\n周报已生成: {output_path}")


if __name__ == "__main__":
    main()
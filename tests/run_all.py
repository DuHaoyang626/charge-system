"""
一键运行所有测试

用法：
    python tests/run_all.py               # 运行所有测试（含输出）
    python tests/run_all.py --quiet        # 仅显示汇总
    python tests/run_all.py --coverage     # 运行并生成覆盖率报告
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="一键运行充电桩系统测试")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="安静模式，仅显示失败用例")
    parser.add_argument("--coverage", "-c", action="store_true",
                        help="生成覆盖率报告")
    parser.add_argument("--module", "-m", type=str, default="",
                        help="指定运行单个模块，如 test_account_service")
    parser.add_argument("--api", action="store_true",
                        help="仅运行 API 端到端测试")
    parser.add_argument("--unit", action="store_true",
                        help="仅运行单元测试")
    parser.add_argument("--integration", action="store_true",
                        help="仅运行集成测试")
    args = parser.parse_args()

    # 构建 pytest 命令
    cmd = [sys.executable, "-m", "pytest"]

    if args.quiet:
        cmd.extend(["-q", "--tb=short"])
    else:
        cmd.extend(["-v", "--tb=long"])

    # 彩色输出
    cmd.append("--color=yes")

    # 覆盖率
    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])

    # 选择测试文件
    test_dir = Path(__file__).parent

    if args.module:
        test_path = test_dir / f"{args.module}.py"
        if not test_path.exists():
            print(f"错误：模块 '{args.module}' 不存在 (tests/{args.module}.py)")
            sys.exit(1)
        cmd.append(str(test_path))
    elif args.api:
        cmd.append(str(test_dir / "test_api.py"))
    elif args.unit:
        for f in test_dir.glob("test_*service*.py"):
            cmd.append(str(f))
    elif args.integration:
        cmd.append(str(test_dir / "test_integration.py"))
    else:
        # 运行所有测试
        cmd.append(str(test_dir))

    # 执行
    print(f"{'='*60}")
    print(f"  智能充电桩调度计费系统 — 测试套件")
    print(f"{'='*60}")
    print(f"  命令: {' '.join(cmd)}")
    print(f"{'='*60}")
    print()

    result = subprocess.run(cmd, cwd=test_dir.parent)

    # 汇总
    print()
    print(f"{'='*60}")
    if result.returncode == 0:
        print(f"  [OK] 全部测试通过！")
    else:
        print(f"  [FAIL] 存在失败的测试 (exit code: {result.returncode})")
        print(f"  提示：当前使用 mock 数据，测试失败是预期的。")
        print(f"  实现真实逻辑后，请移除 TODO 并更新断言值。")
    print(f"{'='*60}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

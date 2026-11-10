"""UI 自动化测试一键运行入口

示例:
  python run.py                                # 全量用例（默认环境 test）
  python run.py --level smoke                  # 只跑冒烟用例
  python run.py --level regression             # 只跑回归用例
  python run.py --env prod --browser firefox   # 切换环境与浏览器
  python run.py -k login --headed              # 关键字过滤 + 有头模式
  python run.py --open                         # 运行后自动打开 Allure 报告
"""
import argparse
import os
import shutil
import subprocess

import pytest


def main() -> int:
    parser = argparse.ArgumentParser(description="UI 自动化测试运行器")
    parser.add_argument("--env", default=None, help="运行环境: test / prod ...")
    parser.add_argument("--browser", default=None, help="chromium / firefox / webkit")
    parser.add_argument("--headed", action="store_true", help="有头模式")
    parser.add_argument("--level", choices=["all", "smoke", "regression"], default="all",
                        help="用例级别过滤")
    parser.add_argument("-k", "--keyword", default=None, help="按关键字过滤用例")
    parser.add_argument("--no-report", action="store_true", help="不生成 Allure HTML 报告")
    parser.add_argument("--open", action="store_true", help="生成报告后自动打开")
    args = parser.parse_args()

    pytest_args = ["-ra"]
    if args.level != "all":
        pytest_args += ["-m", args.level]
    if args.keyword:
        pytest_args += ["-k", args.keyword]
    if args.env:
        pytest_args += ["--env", args.env]
    if args.browser:
        pytest_args += ["--browser", args.browser]
    if args.headed:
        pytest_args += ["--headed"]

    code = pytest.main(pytest_args)

    if not args.no_report:
        results = os.path.abspath("reports/allure-results")
        report = os.path.abspath("reports/allure-html")
        if shutil.which("allure"):
            # --single-file：所有数据内嵌进单个 index.html，file:// 直接双击即可打开
            # （多文件模式通过 AJAX 加载 JSON，本地 file:// 打开会被浏览器拦截导致空白）
            # 单文件模式不输出 history/ 目录，因此先额外生成一次多文件到临时目录，
            # 仅为取得累积的趋势历史数据，随后删除
            tmp_multi = os.path.abspath("reports/.allure-multi-tmp")
            subprocess.run(["allure", "generate", results, "-o", tmp_multi, "--clean"],
                           check=False, capture_output=True)
            from utils.allure_results_patch import backup_history
            backup_history(tmp_multi, os.path.join("reports", "history"))
            shutil.rmtree(tmp_multi, ignore_errors=True)
            subprocess.run(["allure", "generate", results, "-o", report, "--clean",
                            "--single-file"], check=False)
            from utils.report_locale import (patch_index_locale, patch_index_style,
                                             patch_index_title)
            patch_index_locale(report, lang="zh")
            # 定制报告标题（config/config.yaml -> report.title）
            from utils.config import settings as _st
            patch_index_title(report, _st.get("report.title", ""))
            # 自定义 CSS（config/config.yaml -> report.custom_css，留空跳过）
            patch_index_style(report, _st.get("report.custom_css", ""))
            index = os.path.join(report, "index.html")
            if os.path.exists(index):
                print(f"\nAllure 报告已生成: {index}")
                if args.open:
                    os.startfile(index) if os.name == "nt" else subprocess.run(["open", index])
        else:
            print("\n未检测到 allure 命令行工具，可执行以下命令安装后重新生成报告:")
            print("  macOS:   brew install allure")
            print("  Windows: scoop install allure")
            print("  Linux:   apt install allure / 下载 https://github.com/allure-framework/allure2/releases")
            print("生成报告:")
            print(f"  allure generate {results} -o {report} --clean")
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())

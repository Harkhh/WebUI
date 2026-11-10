"""Allure 结果数据修补：失败分类匹配与趋势图历史累积

1. fill_status_message：allure-pytest 对非断言异常（broken）只写 statusDetails.message，
   statusMessage 为空导致 categories.json 的正则匹配不到；把 message 回填到 statusMessage。
2. backup_history / restore_history：allure 趋势图依赖 results 目录中的 history/，
   而 allure-pytest 每轮 --clean-alluredir 会清空 results；
   因此在 generate 后把输出目录的 history 备份到 reports/history，
   下一轮 pytest 启动（清理完成后）再恢复进 results，实现趋势跨轮累积。
"""
import glob
import json
import os
import shutil


def fill_status_message(results_dir: str) -> int:
    """把 statusDetails.message 回填到空的 statusMessage，返回修补条数。"""
    patched = 0
    for f in glob.glob(os.path.join(results_dir, "*-result.json")):
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        if data.get("statusMessage"):
            continue
        msg = (data.get("statusDetails") or {}).get("message")
        if msg:
            data["statusMessage"] = msg.splitlines()[0] if msg else msg
            data["statusTrace"] = (data.get("statusDetails") or {}).get("trace", "")
            with open(f, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False)
            patched += 1
    return patched


def backup_history(report_dir: str, store_dir: str) -> None:
    """generate 后：allure-html/history -> reports/history"""
    src = os.path.join(report_dir, "history")
    if os.path.isdir(src):
        os.makedirs(store_dir, exist_ok=True)
        shutil.copytree(src, store_dir, dirs_exist_ok=True)


def restore_history(store_dir: str, results_dir: str) -> None:
    """pytest 启动（results 清理完成）后：reports/history -> allure-results/history"""
    if os.path.isdir(store_dir) and os.listdir(store_dir):
        shutil.copytree(store_dir, os.path.join(results_dir, "history"),
                        dirs_exist_ok=True)

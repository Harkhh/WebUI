"""执行引擎：驱动一个 CaseData 的步骤序列，串联 变量解析 / 日志 / 过程监测 / Allure 附件"""
import json
import os
import time

import allure

from core.actions import ACTIONS
from core.models import CaseData
from core.var_parser import VarResolver
from utils.config import ROOT, settings
from utils.logger import case_logger, release_case_logger, get_run_logger
from utils.monitor import RunMonitor

# 业务数据在收集阶段加载一次（settings 已在 pytest_configure 初始化）
BUSINESS_ALL: dict = {}


def _init_business() -> None:
    global BUSINESS_ALL
    if not BUSINESS_ALL:
        BUSINESS_ALL = settings.load_business_all()


def run_case(request, page, case: CaseData) -> None:
    """在 pytest 测试函数内调用：执行用例并记录过程监测数据"""
    _init_business()
    monitor = RunMonitor.instance()
    monitor.start_case(case_id=case.id, title=case.title, module=case.module,
                       source=os.path.relpath(case.source, ROOT),
                       level=case.level, priority=case.priority)
    logger = case_logger(case.id)
    log = get_run_logger()
    resolver = VarResolver(env=settings.env, business=BUSINESS_ALL, data={})
    # 先整体解析用例数据（支持 data 里引用业务数据/环境变量，如 user: ${business.users.xxx})
    resolver.scopes["data"] = resolver.resolve(case.data)
    log.info(f"开始执行用例 [{case.id}] {case.title}（{case.level}/{case.priority}, 来源: {os.path.basename(case.source)}）")

    try:
        for index, step in enumerate(case.steps, 1):
            params = {k: resolver.resolve(v) for k, v in step.params.items()}
            logger.info(f"步骤{index} {step.action} 参数: {params}")
            t0 = time.monotonic()
            try:
                result = ACTIONS[step.action]["fn"](page, params)
                duration = time.monotonic() - t0
                if isinstance(result, dict) and "__save__" in result:
                    var_name, var_value = result["__save__"]
                    resolver.set_runtime(var_name, var_value)
                    logger.info(f"步骤{index} 保存变量 {var_name} = {var_value!r}")
                logger.info(f"步骤{index} {step.action} 成功 (耗时 {duration:.3f}s)")
                monitor.record_step(case.id, index, step.action, params, "passed", duration)
            except Exception as e:
                duration = time.monotonic() - t0
                msg = f"{type(e).__name__}: {e}"
                logger.error(f"步骤{index} {step.action} 失败 (耗时 {duration:.3f}s) -> {msg}")
                monitor.record_step(case.id, index, step.action, params, "failed", duration, msg)
                raise
        monitor.end_case(case.id, "passed")
        log.info(f"用例 [{case.id}] 执行通过")
    except Exception as e:
        monitor.end_case(case.id, "failed", str(e)[:300])
        log.error(f"用例 [{case.id}] 执行失败: {e}")
        raise
    finally:
        _attach_process_record(case)
        release_case_logger(case.id)


def _attach_process_record(case: CaseData) -> None:
    """把过程监测记录 + 用例日志挂到 Allure"""
    monitor = RunMonitor.instance()
    record = monitor.get_case(case.id)
    if record:
        allure.attach(json.dumps(record, ensure_ascii=False, indent=2),
                      name="执行过程监测", attachment_type=allure.attachment_type.JSON)
    log_path = os.path.join(settings.run_logs_dir, f"{case.id}.log")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            allure.attach(f.read(), name=f"用例日志-{case.id}",
                          attachment_type=allure.attachment_type.TEXT)

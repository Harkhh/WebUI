"""过程日志：每次运行独立目录 logs/<run_id>/，报告目录完全分离"""
import logging
import os
import threading

from utils.config import settings

_FMT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
_lock = threading.Lock()
_run_logger: logging.Logger | None = None


def init_run_logger() -> logging.Logger:
    """pytest_configure 时调用：创建 logs/<run_id>/run.log"""
    global _run_logger
    with _lock:
        if _run_logger is not None:
            return _run_logger
        os.makedirs(settings.run_logs_dir, exist_ok=True)
        logger = logging.getLogger("ui_test")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        fh = logging.FileHandler(os.path.join(settings.run_logs_dir, "run.log"), encoding="utf-8")
        fh.setFormatter(logging.Formatter(_FMT))
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter(_FMT))
        sh.setLevel(logging.INFO)
        logger.addHandler(sh)
        _run_logger = logger
        return logger


def get_run_logger() -> logging.Logger:
    return _run_logger or init_run_logger()


def case_logger(case_id: str) -> logging.Logger:
    """为单个用例挂一个独立文件 logs/<run_id>/<case_id>.log"""
    logger = logging.getLogger(f"ui_test.case.{case_id}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if not any(getattr(h, "_case_log", None) == case_id for h in logger.handlers):
        os.makedirs(settings.run_logs_dir, exist_ok=True)
        fh = logging.FileHandler(os.path.join(settings.run_logs_dir, f"{case_id}.log"),
                                 encoding="utf-8", mode="w")
        fh._case_log = case_id  # type: ignore[attr-defined]
        fh.setFormatter(logging.Formatter(_FMT))
        logger.addHandler(fh)
    return logger


def release_case_logger(case_id: str) -> str:
    """用例结束后移除文件 handler，返回日志文件路径"""
    logger = logging.getLogger(f"ui_test.case.{case_id}")
    path = ""
    for h in list(logger.handlers):
        path = getattr(h, "baseFilename", path)
        logger.removeHandler(h)
        h.close()
    return path

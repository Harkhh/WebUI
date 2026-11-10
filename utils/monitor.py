"""测试过程监测：
1. RunMonitor    —— 用例级/步骤级监测：每个用例的步骤序列、每步耗时与状态、用例总耗时，
                    汇总输出 reports/summary_<run_id>.json，并作为 Allure 附件挂到对应用例。
2. ResourceMonitor —— 进程资源监测：后台线程按间隔采样 pytest 进程 CPU / 内存，
                    输出 reports/resource_<run_id>.csv 与统计摘要。
"""
import csv
import json
import os
import threading
import time
from datetime import datetime


class RunMonitor:
    _instance = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.run_id: str = ""
        self.started_at: str = ""
        self.config_snapshot: dict = {}
        self._cases: dict[str, dict] = {}
        self._t0: dict[str, float] = {}
        self._current_case: str | None = None

    @classmethod
    def instance(cls) -> "RunMonitor":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---------- 运行级 ----------
    def start_run(self, run_id: str, config_snapshot: dict) -> None:
        self.run_id = run_id
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.config_snapshot = config_snapshot
        self._cases.clear()

    def finish_run(self, extra: dict | None = None) -> dict:
        return self.dump(extra=extra)

    # ---------- 用例级 ----------
    def start_case(self, case_id: str, title: str, module: str = "", source: str = "",
                   level: str = "", priority: str = "") -> None:
        self._current_case = case_id
        self._t0[case_id] = time.monotonic()
        self._cases[case_id] = {
            "case_id": case_id,
            "title": title,
            "module": module,
            "level": level,
            "priority": priority,
            "source": source,
            "start_time": datetime.now().isoformat(timespec="seconds"),
            "status": "running",
            "error": None,
            "duration_sec": 0.0,
            "steps": [],
        }

    def record_step(self, case_id: str, index: int, action: str, params: dict,
                    status: str, duration: float, error: str | None = None) -> None:
        case = self._cases.get(case_id)
        if case is None:
            return
        case["steps"].append({
            "index": index,
            "action": action,
            "params": {k: (str(v)[:80]) for k, v in params.items()},
            "status": status,
            "duration_sec": round(duration, 3),
            "error": error,
        })

    def end_case(self, case_id: str, status: str, error: str | None = None) -> None:
        case = self._cases.get(case_id)
        if case is None:
            return
        case["status"] = status
        case["error"] = error
        case["duration_sec"] = round(time.monotonic() - self._t0.get(case_id, time.monotonic()), 3)
        case["end_time"] = datetime.now().isoformat(timespec="seconds")

    def get_case(self, case_id: str) -> dict | None:
        return self._cases.get(case_id)

    # ---------- 汇总输出 ----------
    def dump(self, extra: dict | None = None) -> dict:
        summary = {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "config": self.config_snapshot,
            "total_cases": len(self._cases),
            "passed": sum(1 for c in self._cases.values() if c["status"] == "passed"),
            "failed": sum(1 for c in self._cases.values() if c["status"] == "failed"),
            "cases": list(self._cases.values()),
        }
        if extra:
            summary.update(extra)
        from utils.config import settings
        os.makedirs(settings.reports_dir, exist_ok=True)
        path = os.path.join(settings.reports_dir, f"summary_{self.run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return summary


class ResourceMonitor:
    """后台线程采样当前进程 CPU% / 内存(MB)"""

    def __init__(self, interval: float = 1.0) -> None:
        self.interval = interval
        self._samples: list[dict] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        try:
            import psutil
        except ImportError:
            return
        self._proc = psutil.Process()
        self._proc.cpu_percent(interval=None)  # 首次调用建立基线
        self._thread = threading.Thread(target=self._loop, daemon=True, name="resource-monitor")
        self._thread.start()

    def _loop(self) -> None:
        import psutil
        while not self._stop.is_set():
            try:
                self._samples.append({
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "cpu_percent": self._proc.cpu_percent(interval=self.interval),
                    "rss_mb": round(self._proc.memory_info().rss / 1024 / 1024, 1),
                })
            except Exception:
                break

    def stop_and_save(self) -> dict:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval * 2)
        if not self._samples:
            return {}
        from utils.config import settings
        os.makedirs(settings.reports_dir, exist_ok=True)
        csv_path = os.path.join(settings.reports_dir, f"resource_{settings.run_id}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ts", "cpu_percent", "rss_mb"])
            writer.writeheader()
            writer.writerows(self._samples)
        cpu = [s["cpu_percent"] for s in self._samples]
        rss = [s["rss_mb"] for s in self._samples]
        return {
            "csv": csv_path,
            "samples": len(self._samples),
            "cpu_avg": round(sum(cpu) / len(cpu), 1),
            "cpu_max": round(max(cpu), 1),
            "rss_avg_mb": round(sum(rss) / len(rss), 1),
            "rss_max_mb": round(max(rss), 1),
        }

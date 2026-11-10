"""全局配置加载：config/config.yaml + config/env/<env>.yaml + 业务数据目录"""
import os
from functools import reduce

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def root_path(*parts: str) -> str:
    return os.path.join(ROOT, *parts)


def _load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Settings:
    """全局配置单例：pytest_configure 阶段初始化"""

    def __init__(self) -> None:
        self.config: dict = {}
        self.env_name: str = "test"
        self.env: dict = {}
        self.run_id: str = ""

    # ---------- 初始化 ----------
    def init(self, env_name: str | None = None, run_id: str | None = None) -> None:
        self.config = _load_yaml(root_path("config", "config.yaml"))
        if env_name:
            self.config["env"] = env_name
        self.env_name = self.config.get("env", "test")
        self.env = _load_yaml(root_path("config", "env", f"{self.env_name}.yaml"))
        self.run_id = run_id or self.run_id

    # ---------- 常用读取 ----------
    def get(self, dotted: str, default=None):
        try:
            return reduce(lambda d, k: d[k], dotted.split("."), self.config)
        except (KeyError, TypeError):
            return default

    @property
    def base_url(self) -> str:
        return str(self.env.get("base_url", "")).rstrip("/")

    @property
    def browser(self) -> dict:
        return self.config.get("browser", {})

    # ---------- 路径 ----------
    @property
    def reports_dir(self) -> str:
        return root_path(self.get("paths.reports_dir", "reports"))

    @property
    def logs_dir(self) -> str:
        return root_path(self.get("paths.logs_dir", "logs"))

    @property
    def run_logs_dir(self) -> str:
        return os.path.join(self.logs_dir, self.run_id)

    @property
    def screenshots_dir(self) -> str:
        return os.path.join(self.reports_dir, "screenshots", self.run_id)

    @property
    def allure_results_dir(self) -> str:
        return os.path.join(self.reports_dir, "allure-results")

    def business_dir(self) -> str:
        return root_path(self.get("paths.business_dir", "data/business"))

    def cases_dir(self) -> str:
        return root_path(self.get("paths.cases_dir", "data/cases"))

    def excel_cases_dir(self) -> str:
        return root_path(self.get("paths.excel_cases_dir", "data/cases/excel"))

    # ---------- 业务数据 ----------
    def load_business_all(self) -> dict:
        """读取 data/business/*.yaml，按文件名合并 -> {文件名: 内容}"""
        merged: dict = {}
        d = self.business_dir()
        if not os.path.isdir(d):
            return merged
        for fn in sorted(os.listdir(d)):
            if fn.endswith((".yaml", ".yml")):
                merged[os.path.splitext(fn)[0]] = _load_yaml(os.path.join(d, fn))
        return merged


settings = Settings()

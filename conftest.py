"""pytest 插件入口：
- 命令行参数（--env / --browser / --headed）
- 运行初始化（日志目录、过程监测、Allure 环境信息）
- 浏览器 fixture 生命周期
- 本地演示站点自动拉起
- 失败自动截图
"""
import functools
import os
import socket
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright

from utils.config import root_path, settings
from utils.logger import get_run_logger, init_run_logger
from utils.monitor import ResourceMonitor, RunMonitor


# ---------------- 命令行参数 ----------------
def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("ui-test")
    group.addoption("--env", action="store", default=None,
                    help="运行环境，对应 config/env/ 下的文件名（默认取 config.yaml 的 env）")
    group.addoption("--browser", action="store", default=None,
                    help="浏览器类型: chromium / firefox / webkit（默认取 config.yaml）")
    group.addoption("--headed", action="store_true", help="有头模式运行（默认无头）")


# ---------------- 运行初始化 ----------------
def pytest_configure(config: pytest.Config) -> None:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    settings.init(env_name=config.getoption("--env"), run_id=run_id)
    init_run_logger()

    browser_type = config.getoption("--browser") or settings.browser.get("type", "chromium")
    headed = bool(config.getoption("--headed"))
    snapshot = {
        "env": settings.env_name,
        "base_url": settings.base_url,
        "browser": browser_type,
        "headed": headed,
        "run_id": run_id,
    }
    RunMonitor.instance().start_run(run_id, snapshot)
    config._resource_monitor = ResourceMonitor(interval=1.0)  # type: ignore[attr-defined]
    config._resource_monitor.start()  # type: ignore[attr-defined]

    log = get_run_logger()
    log.info(f"===== UI 自动化测试开始 run_id={run_id} 配置={snapshot} =====")


def pytest_sessionstart(session: pytest.Session) -> None:
    """Allure 环境信息 + 构建信息（在 allure 插件清理结果目录之后写入）"""
    os.makedirs(settings.allure_results_dir, exist_ok=True)
    with open(os.path.join(settings.allure_results_dir, "environment.properties"), "w",
              encoding="utf-8") as f:
        for k, v in RunMonitor.instance().config_snapshot.items():
            f.write(f"{k}={v}\n")
    # executor.json：概览页"构建"区块显示定制构建名
    import json as _json
    build_name = settings.get("report.build_name") or f"UI测试-{settings.run_id}"
    with open(os.path.join(settings.allure_results_dir, "executor.json"), "w",
              encoding="utf-8") as f:
        _json.dump({"name": "本地运行", "type": "local", "buildName": build_name},
                   f, ensure_ascii=False)
    # categories.json：失败自动分类（总览页"类别"卡片与类别页按此聚合）
    categories = [
        {"name": "断言失败", "matchedStatuses": ["failed"],
         "messageRegex": ".*(AssertionError|expect|Locator expected).*"},
        {"name": "元素定位超时", "matchedStatuses": ["failed", "broken"],
         "messageRegex": ".*(Timeout \\d+ms exceeded|TimeoutError|waiting for locator).*"},
        {"name": "页面加载失败", "matchedStatuses": ["failed", "broken"],
         "messageRegex": ".*(net::ERR|NS_ERROR|ERR_CONNECTION|Navigation timeout).*"},
        {"name": "用例数据错误", "matchedStatuses": ["failed", "broken"],
         "messageRegex": ".*(KeyError|无法解析|缺少必填|未知 action|不是合法 JSON).*"},
    ]
    with open(os.path.join(settings.allure_results_dir, "categories.json"), "w",
              encoding="utf-8") as f:
        _json.dump(categories, f, ensure_ascii=False, indent=2)
    # 恢复历史趋势数据（在上轮 generate 备份的 reports/history 基础上累积）
    from utils.allure_results_patch import restore_history
    restore_history(os.path.join("reports", "history"), settings.allure_results_dir)


def pytest_unconfigure(config: pytest.Config) -> None:
    # 回填 statusMessage：让 categories.json 的失败分类能匹配非断言异常
    from utils.allure_results_patch import fill_status_message
    fill_status_message(settings.allure_results_dir)
    resource_stats = config._resource_monitor.stop_and_save()  # type: ignore[attr-defined]
    summary = RunMonitor.instance().finish_run(extra={"resource": resource_stats})
    log = get_run_logger()
    log.info(f"===== 运行结束：共 {summary['total_cases']} 条，通过 {summary['passed']}，"
             f"失败 {summary['failed']} =====")
    log.info(f"运行摘要: reports/summary_{settings.run_id}.json | 资源监测: "
             f"reports/resource_{settings.run_id}.csv | 过程日志: logs/{settings.run_id}/")


# ---------------- 报告上报钩子 ----------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
    if rep.when == "call" and RunMonitor.instance().get_case(_case_id(item)):
        RunMonitor.instance().end_case(_case_id(item),
                                       "passed" if rep.passed else "failed",
                                       None if rep.passed else str(rep.longrepr)[:300])


def _case_id(item: pytest.Item) -> str:
    """取用例真实 id（参数化用例 id 为 case.id 而非 pytest id）"""
    return getattr(item, "_ui_case_id", item.name)


# ---------------- 浏览器 fixture ----------------
@pytest.fixture(scope="session")
def browser(request: pytest.FixtureRequest):
    pw = sync_playwright().start()
    btype = request.config.getoption("--browser") or settings.browser.get("type", "chromium")
    headless = False if request.config.getoption("--headed") else settings.browser.get("headless", True)
    browser = getattr(pw, btype).launch(
        headless=headless,
        slow_mo=int(settings.browser.get("slow_mo", 0)),
    )
    get_run_logger().info(f"启动浏览器 {btype} headless={headless}")
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture(scope="function")
def page(request: pytest.FixtureRequest, browser):
    viewport = settings.browser.get("viewport", {"width": 1280, "height": 720})
    ctx_kwargs: dict = {"viewport": viewport}
    if settings.browser.get("user_agent"):
        ctx_kwargs["user_agent"] = settings.browser["user_agent"]
    context = browser.new_context(**ctx_kwargs)
    context.set_default_timeout(int(settings.browser.get("timeout", 10)) * 1000)
    if settings.browser.get("stealth"):
        # 隐藏自动化特征：navigator.webdriver / plugins / languages
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)
    page = context.new_page()
    yield page

    rep = getattr(request.node, "rep_call", None)
    if rep is not None and rep.failed:
        # 失败自动截图（存报告目录并挂到 Allure）
        from core.actions import take_screenshot
        slug = request.node.nodeid.replace("::", "_").replace("/", "_").replace("[", "_").replace("]", "")
        try:
            take_screenshot(page, slug, full_page=True)
        except Exception:
            pass
    context.close()


# ---------------- 本地演示站点 ----------------
@pytest.fixture(scope="session", autouse=True)
def demo_server(request: pytest.FixtureRequest):
    """base_url 指向本机时，自动拉起 demo_site 静态服务（先探测，未运行才启动）"""
    host = urlparse(settings.base_url).hostname or ""
    port = urlparse(settings.base_url).port or 80
    if host not in ("127.0.0.1", "localhost"):
        yield None
        return

    def _alive() -> bool:
        import urllib.request
        try:
            with urllib.request.urlopen(f"{settings.base_url}/index.html", timeout=1.5):
                return True
        except Exception:
            return False

    if _alive():
        get_run_logger().info(f"检测到 {settings.base_url} 已有服务，直接复用")
        yield None
        return

    doc_root = root_path(settings.get("demo_server.doc_root", "demo_site"))

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:  # 静默访问日志
            pass

    handler = functools.partial(QuietHandler, directory=doc_root)
    try:
        server = ThreadingHTTPServer((host, port), handler)
    except OSError as e:
        raise RuntimeError(
            f"演示站点启动失败: {settings.base_url} 端口被占用且无响应（{e}）。"
            f"请检查端口 {port} 是否被其他程序占用") from e
    threading.Thread(target=server.serve_forever, daemon=True).start()
    get_run_logger().info(f"演示站点已启动: {settings.base_url} (目录 {doc_root})")
    yield server
    server.shutdown()

"""关键字动作库：YAML / Excel 用例中可直接使用的 action 集合，可在此扩展自定义动作"""
import os

import allure
from playwright.sync_api import Page, expect

from utils.config import settings


class StepError(AssertionError):
    """步骤执行失败（带用例上下文信息）"""


# ---------------- 注册机制 ----------------
ACTIONS: dict[str, dict] = {}


def register(name: str, required: tuple = (), optional: tuple = (), doc: str = ""):
    def deco(fn):
        ACTIONS[name] = {"fn": fn, "required": required, "optional": optional, "doc": doc}
        return fn
    return deco


def _loc(page: Page, locator: str):
    """定位语法: css= / xpath= / text= / id=，默认 css"""
    locator = str(locator).strip()
    if locator.startswith(("css=", "xpath=", "text=", "id=")):
        kind, _, expr = locator.partition("=")
        expr = expr.strip()
        if kind == "css":
            return page.locator(expr)
        if kind == "xpath":
            return page.locator(f"xpath={expr}")
        if kind == "text":
            return page.get_by_text(expr)
        if kind == "id":
            return page.locator(f"#{expr}")
    return page.locator(locator)


def _full_url(url: str) -> str:
    url = str(url)
    if url.startswith(("http://", "https://")):
        return url
    return f"{settings.base_url}{url if url.startswith('/') else '/' + url}"


# ---------------- 导航类 ----------------
@register("goto", required=("value",), doc="打开页面：value 支持 http 全地址或相对路径（自动拼接 base_url）")
def _goto(page: Page, p: dict):
    page.goto(_full_url(p["value"]), wait_until="domcontentloaded")


@register("wait", required=("value",), doc="强制等待：value 秒数（建议优先用 wait_for）")
def _wait(page: Page, p: dict):
    page.wait_for_timeout(float(p["value"]) * 1000)


@register("wait_for", required=("locator",), optional=("state",),
          doc="等待元素状态：state=visible/hidden/attached/detached，默认 visible")
def _wait_for(page: Page, p: dict):
    _loc(page, p["locator"]).wait_for(state=p.get("state", "visible"))


# ---------------- 交互类 ----------------
@register("click", required=("locator",), doc="点击元素")
def _click(page: Page, p: dict):
    _loc(page, p["locator"]).click()


@register("dblclick", required=("locator",), doc="双击元素")
def _dblclick(page: Page, p: dict):
    _loc(page, p["locator"]).dblclick()


@register("fill", required=("locator", "value"), doc="清空并输入内容")
def _fill(page: Page, p: dict):
    _loc(page, p["locator"]).fill(str(p["value"]))


@register("clear", required=("locator",), doc="清空输入框")
def _clear(page: Page, p: dict):
    _loc(page, p["locator"]).fill("")


@register("press", required=("key",), optional=("locator",), doc="按键：key 如 Enter；可指定 locator")
def _press(page: Page, p: dict):
    if p.get("locator"):
        _loc(page, p["locator"]).press(str(p["key"]))
    else:
        page.keyboard.press(str(p["key"]))


@register("hover", required=("locator",), doc="鼠标悬停")
def _hover(page: Page, p: dict):
    _loc(page, p["locator"]).hover()


@register("select", required=("locator", "value"), doc="下拉框按 value/label 选择")
def _select(page: Page, p: dict):
    _loc(page, p["locator"]).select_option(str(p["value"]))


@register("check", required=("locator",), doc="勾选复选框/单选框")
def _check(page: Page, p: dict):
    _loc(page, p["locator"]).check()


@register("uncheck", required=("locator",), doc="取消勾选")
def _uncheck(page: Page, p: dict):
    _loc(page, p["locator"]).uncheck()


@register("scroll", required=("value",), optional=("locator",),
          doc="滚动：value 为像素；指定 locator 时滚动至元素可见")
def _scroll(page: Page, p: dict):
    if p.get("locator"):
        _loc(page, p["locator"]).scroll_into_view_if_needed()
    else:
        page.mouse.wheel(0, int(p["value"]))


# ---------------- 取值类 ----------------
@register("save_text", required=("locator", "value"), doc="保存元素文本到变量：value 为变量名，后续用 ${变量名} 引用")
def _save_text(page: Page, p: dict):
    return {"__save__": (str(p["value"]), _loc(page, p["locator"]).inner_text().strip())}


@register("save_attr", required=("locator", "attr", "value"), doc="保存元素属性到变量：attr 为属性名，value 为变量名")
def _save_attr(page: Page, p: dict):
    return {"__save__": (str(p["value"]), _loc(page, p["locator"]).get_attribute(p["attr"]))}


# ---------------- 断言类 ----------------
@register("assert_visible", required=("locator",), doc="断言元素可见")
def _assert_visible(page: Page, p: dict):
    expect(_loc(page, p["locator"])).to_be_visible()


@register("assert_hidden", required=("locator",), doc="断言元素隐藏/不存在")
def _assert_hidden(page: Page, p: dict):
    expect(_loc(page, p["locator"])).to_be_hidden()


@register("assert_text", required=("locator", "expect"), doc="断言元素文本完全等于 expect")
def _assert_text(page: Page, p: dict):
    expect(_loc(page, p["locator"])).to_have_text(str(p["expect"]))


@register("assert_contains", required=("locator", "expect"), doc="断言元素文本包含 expect（locator 传 url 时断言地址包含）")
def _assert_contains(page: Page, p: dict):
    if str(p["locator"]).strip().lower() == "url":
        _assert_url(page, p)
    else:
        expect(_loc(page, p["locator"])).to_contain_text(str(p["expect"]))


@register("assert_title", required=("expect",), doc="断言页面标题等于 expect")
def _assert_title(page: Page, p: dict):
    expect(page).to_have_title(str(p["expect"]))


@register("assert_url", required=("expect",), doc="断言当前 URL 包含 expect")
def _assert_url(page: Page, p: dict):
    expect_str = str(p["expect"])
    page.wait_for_url(lambda url: expect_str in str(url))


@register("assert_count", required=("locator", "expect"), doc="断言元素数量等于 expect")
def _assert_count(page: Page, p: dict):
    expect(_loc(page, p["locator"])).to_have_count(int(p["expect"]))


# ---------------- 截图 ----------------
def take_screenshot(page: Page, name: str, full_page: bool = True) -> str:
    """截图并挂到 Allure，返回文件路径"""
    os.makedirs(settings.screenshots_dir, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))
    path = os.path.join(settings.screenshots_dir, f"{safe}.png")
    page.screenshot(path=path, full_page=full_page)
    with open(path, "rb") as f:
        allure.attach(f.read(), name=f"截图-{name}", attachment_type=allure.attachment_type.PNG)
    return path


@register("screenshot", optional=("value",), doc="主动截图并挂到 Allure：value 为截图名")
def _screenshot(page: Page, p: dict):
    take_screenshot(page, p.get("value") or "screenshot")

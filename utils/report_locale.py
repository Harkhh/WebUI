"""Allure 报告本地化：生成后把默认界面语言预设为中文

原理：Allure 前端的界面语言存于浏览器 localStorage 的
ALLURE_REPORT_SETTINGS（JSON 字符串）中的 language 字段。
本模块在 index.html 的 <head> 最前面注入一段脚本：首次打开（尚无语言偏好）时
写入 {"language": "zh"}，之后用户手动切换语言不会被覆盖。
幂等：已注入过则跳过。
"""
import os
import re

_MARK = "allure-locale-patch"


def patch_index_locale(report_dir: str, lang: str = "zh") -> bool:
    """在报告 index.html 注入默认语言脚本。返回是否发生了修改。"""
    index = os.path.join(report_dir, "index.html")
    if not os.path.exists(index):
        return False
    with open(index, "r", encoding="utf-8") as f:
        html = f.read()
    if _MARK in html:
        return False
    snippet = (
        f'<script id="{_MARK}">try{{'
        f'var s=JSON.parse(localStorage.getItem("ALLURE_REPORT_SETTINGS")||"{{}}");'
        f'if(!s.language)s.language="{lang}";'
        f'localStorage.setItem("ALLURE_REPORT_SETTINGS",JSON.stringify(s));'
        f"}}catch(e){{}}</script>"
    )
    if "<head>" in html:
        html = html.replace("<head>", "<head>" + snippet, 1)
    else:
        html = snippet + html
    with open(index, "w", encoding="utf-8") as f:
        f.write(html)
    return True


def patch_index_title(report_dir: str, title: str) -> bool:
    """替换报告 <title> 标签（浏览器标签页标题）。返回是否发生了修改。"""
    index = os.path.join(report_dir, "index.html")
    if not os.path.exists(index) or not title:
        return False
    with open(index, "r", encoding="utf-8") as f:
        html = f.read()
    new_html, n = re.subn(r"<title>[^<]*</title>", f"<title>{title}</title>", html, count=1)
    if n == 0:
        return False
    with open(index, "w", encoding="utf-8") as f:
        f.write(new_html)
    return True


def patch_index_style(report_dir: str, css: str) -> bool:
    """在报告 <head> 注入自定义 CSS（覆盖总览页样式/隐藏卡片/加横幅等）。"""
    index = os.path.join(report_dir, "index.html")
    if not os.path.exists(index) or not css.strip():
        return False
    with open(index, "r", encoding="utf-8") as f:
        html = f.read()
    if "allure-style-patch" in html:
        return False
    snippet = f'<style id="allure-style-patch">{css}</style>'
    if "</head>" in html:
        html = html.replace("</head>", snippet + "</head>", 1)
    else:
        html += snippet
    with open(index, "w", encoding="utf-8") as f:
        f.write(html)
    return True

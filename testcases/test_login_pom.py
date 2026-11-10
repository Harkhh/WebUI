"""POM（Page Object）代码用例示例：与关键字驱动引擎并存的补充方式
业务数据同样来自 data/business/users.yaml，保持数据分离
"""
import allure
import pytest

from pages.base_page import BasePage
from utils.config import settings


@allure.feature("登录模块")
@allure.title("POM 方式登录冒烟（代码用例示例）")
@pytest.mark.smoke
@pytest.mark.P1
def test_pom_login(page):
    users = settings.load_business_all()["users"]["demo_shop"]
    bp = BasePage(page)
    bp.goto("/index.html")
    bp.fill("#username", users["standard_user"]["username"])
    bp.fill("#password", users["standard_user"]["password"])
    bp.click("#login-btn")
    assert "products.html" in page.url

"""可选 PO（Page Object）层：适合复杂业务封装；与关键字引擎可并存使用"""
from utils.config import settings


class BasePage:
    def __init__(self, page) -> None:
        self.page = page

    def goto(self, path: str = "/") -> None:
        url = path if path.startswith("http") else f"{settings.base_url}{path}"
        self.page.goto(url, wait_until="domcontentloaded")

    def click(self, locator: str) -> None:
        self.page.locator(locator).click()

    def fill(self, locator: str, value: str) -> None:
        self.page.locator(locator).fill(str(value))

    def text_of(self, locator: str) -> str:
        return self.page.locator(locator).inner_text().strip()

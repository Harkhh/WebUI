"""用例数据模型"""
from dataclasses import dataclass, field


@dataclass
class Step:
    action: str
    params: dict = field(default_factory=dict)


@dataclass
class CaseData:
    id: str
    title: str
    level: str = "regression"        # smoke / regression
    priority: str = "P2"             # P0 ~ P3
    module: str = ""                 # 业务模块（Allure feature）
    steps: list[Step] = field(default_factory=list)
    data: dict = field(default_factory=dict)          # 用例级数据（可被参数行覆盖）
    parametrize: list[dict] | None = None             # 参数化数据集
    source: str = ""                                  # 用例文件路径
    source_type: str = "yaml"                         # yaml / excel

    @property
    def pytest_id(self) -> str:
        return f"{self.id}[{self.title}]"

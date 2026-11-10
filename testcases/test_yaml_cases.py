"""YAML 用例统一执行入口：自动收集 data/cases 下所有 yaml 并参数化注入"""
import allure
import pytest

from core.loader import collect_yaml_cases
from core.runner import run_case
from utils.config import settings

SEVERITY = {
    "P0": allure.severity_level.BLOCKER,
    "P1": allure.severity_level.CRITICAL,
    "P2": allure.severity_level.NORMAL,
    "P3": allure.severity_level.MINOR,
}

CASES = collect_yaml_cases(settings.cases_dir())


def _marks(case):
    marks = []
    if case.level in ("smoke", "regression"):
        marks.append(getattr(pytest.mark, case.level))
    marks.append(getattr(pytest.mark, case.priority))
    return marks


PARAMS = [pytest.param(c, id=c.pytest_id, marks=_marks(c)) for c in CASES]


@pytest.mark.parametrize("case", PARAMS)
def test_yaml_case(request, page, case):
    request.node._ui_case_id = case.id
    allure.dynamic.title(case.title)
    allure.dynamic.feature(case.module or "YAML 用例")
    allure.dynamic.tag(case.level)
    allure.dynamic.severity(SEVERITY.get(case.priority, allure.severity_level.NORMAL))
    run_case(request, page, case)

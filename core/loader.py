"""用例加载器：把 YAML / Excel 文件解析为 CaseData 模型（含参数化展开与步骤校验）"""
import json
import os

from core.actions import ACTIONS
from core.models import CaseData, Step

REQUIRED_CASE_KEYS = ("id", "title")
VALID_LEVELS = ("smoke", "regression")
VALID_PRIORITIES = ("P0", "P1", "P2", "P3")


def _validate_case(case: CaseData, source: str) -> None:
    for i, step in enumerate(case.steps, 1):
        if step.action not in ACTIONS:
            raise ValueError(
                f"用例 {case.id}({source}) 第 {i} 步使用了未知 action: {step.action}，"
                f"可用: {sorted(ACTIONS)}")
        missing = [k for k in ACTIONS[step.action]["required"] if k not in step.params]
        if missing:
            raise ValueError(
                f"用例 {case.id}({source}) 第 {i} 步 {step.action} 缺少必填参数: {missing}")


def _build_case(raw: dict, source: str, source_type: str) -> CaseData:
    for key in REQUIRED_CASE_KEYS:
        if not raw.get(key):
            raise ValueError(f"用例缺少必填字段 {key}: {source}")
    case = CaseData(
        id=str(raw["id"]),
        title=str(raw["title"]),
        level=str(raw.get("level", "regression")).lower(),
        priority=str(raw.get("priority", "P2")).upper(),
        module=str(raw.get("module", "")),
        steps=[Step(action=str(s["action"]),
                    params={k: v for k, v in s.items() if k != "action"})
               for s in raw.get("steps", [])],
        data=dict(raw.get("data") or {}),
        parametrize=raw.get("parametrize"),
        source=source,
        source_type=source_type,
    )
    if case.level not in VALID_LEVELS:
        raise ValueError(f"用例 {case.id} level 非法: {case.level}（可选 {VALID_LEVELS}）")
    if case.priority not in VALID_PRIORITIES:
        raise ValueError(f"用例 {case.id} priority 非法: {case.priority}（可选 {VALID_PRIORITIES}）")
    _validate_case(case, source)
    return case


def load_yaml_cases(path: str) -> list[CaseData]:
    """加载单个 YAML 用例文件；parametrize 展开为多条用例"""
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    cases: list[CaseData] = []
    module = str(doc.get("suite", os.path.splitext(os.path.basename(path))[0]))
    for raw in doc.get("cases", []):
        raw.setdefault("module", module)
        case = _build_case(raw, path, "yaml")
        if case.parametrize:
            for i, row in enumerate(case.parametrize, 1):
                sub = CaseData(**{**case.__dict__})
                sub.id = f"{case.id}_p{i}"
                sub.data = {**case.data, **row}
                sub.parametrize = None
                _validate_case(sub, path)
                cases.append(sub)
        else:
            cases.append(case)
    return cases


def load_excel_cases(path: str) -> list[CaseData]:
    """加载 Excel 用例（需含 Cases 与 Steps 两个 sheet，模板见 tools/gen_excel_cases.py）"""
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True)

    def sheet_rows(name: str) -> list[dict]:
        if name not in wb.sheetnames:
            raise ValueError(f"Excel 缺少 sheet[{name}]: {path}")
        ws = wb[name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
        out = []
        for r in rows[1:]:
            if all(v is None for v in r):
                continue
            out.append({headers[i]: r[i] for i in range(min(len(headers), len(r)))})
        return out

    case_rows = sheet_rows("Cases")
    step_rows = sheet_rows("Steps")
    steps_map: dict[str, list[dict]] = {}
    for r in step_rows:
        cid = str(r.get("case_id", "")).strip()
        if not cid:
            continue
        params = {k: v for k, v in r.items()
                  if k not in ("case_id", "step") and v is not None and str(k).strip() != ""}
        steps_map.setdefault(cid, []).append(params)

    cases: list[CaseData] = []
    for r in case_rows:
        cid = str(r.get("case_id", "")).strip()
        if not cid:
            continue
        data_cell = r.get("data")
        parametrize = None
        data: dict = {}
        if data_cell not in (None, ""):
            try:
                parsed = json.loads(str(data_cell))
            except json.JSONDecodeError as e:
                raise ValueError(f"Excel 用例 {cid} 的 data 列不是合法 JSON: {e}")
            if isinstance(parsed, list):
                parametrize = parsed
            elif isinstance(parsed, dict):
                data = parsed
        raw = {
            "id": cid,
            "title": str(r.get("title", cid)),
            "level": str(r.get("level", "regression")),
            "priority": str(r.get("priority", "P2")),
            "module": str(r.get("module", "")),
            "steps": steps_map.get(cid, []),
            "data": data,
            "parametrize": parametrize,
        }
        case = _build_case(raw, path, "excel")
        if case.parametrize:
            for i, row in enumerate(case.parametrize, 1):
                sub = CaseData(**{**case.__dict__})
                sub.id = f"{case.id}_p{i}"
                sub.data = {**case.data, **row}
                sub.parametrize = None
                _validate_case(sub, path)
                cases.append(sub)
        else:
            cases.append(case)
    return cases


def collect_yaml_cases(directory: str, exclude: tuple = ()) -> list[CaseData]:
    all_cases: list[CaseData] = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith((".yaml", ".yml")) or fn.startswith("_"):
            continue
        if any(ex in fn for ex in exclude):
            continue
        all_cases.extend(load_yaml_cases(os.path.join(directory, fn)))
    return all_cases


def collect_excel_cases(directory: str) -> list[CaseData]:
    all_cases: list[CaseData] = []
    if not os.path.isdir(directory):
        return all_cases
    for fn in sorted(os.listdir(directory)):
        if fn.endswith(".xlsx") and not fn.startswith("~$"):
            all_cases.extend(load_excel_cases(os.path.join(directory, fn)))
    return all_cases

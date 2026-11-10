"""变量解析：支持 ${env.xxx} / ${business.<文件>.<键>} / ${用例数据键} / 内置变量"""
import re
import time
from datetime import datetime
from functools import reduce

VAR_RE = re.compile(r"\$\{([^{}]+)\}")

_BUILTINS = {
    "timestamp": lambda: str(int(time.time())),
    "today": lambda: datetime.now().strftime("%Y-%m-%d"),
    "now": lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}


def _traverse(data: dict, dotted: str):
    try:
        return reduce(lambda d, k: d[k], dotted.split("."), data)
    except (KeyError, TypeError, IndexError):
        raise KeyError(f"变量 ${{{dotted}}} 无法解析，请检查 env/业务数据/用例数据定义")


class VarResolver:
    """
    scopes 解析优先级（先命中先使用）:
      1. runtime  运行期变量（save_text 保存的）
      2. data     用例数据（含参数化行）
      3. business data/business/*.yaml 合并后 {文件名: 内容}
      4. env      config/env/<env>.yaml
    内置: timestamp / today / now
    """

    def __init__(self, env: dict, business: dict, data: dict | None = None,
                 runtime: dict | None = None) -> None:
        self.scopes = {
            "runtime": runtime if runtime is not None else {},
            "data": data if data is not None else {},
            "business": business,
            "env": env,
        }

    def set_runtime(self, key: str, value) -> None:
        self.scopes["runtime"][key] = value

    def _resolve_token(self, token: str, _depth: int = 0):
        token = token.strip()
        if token in _BUILTINS:
            return _BUILTINS[token]()
        if _depth > 5:
            raise KeyError(f"变量嵌套层级过深: ${{{token}}}")
        if token.startswith("env."):
            value = _traverse(self.scopes["env"], token[4:])
        elif token.startswith("business."):
            value = _traverse(self.scopes["business"], token[9:])
        else:
            value = None
            for scope in ("runtime", "data"):
                try:
                    value = _traverse(self.scopes[scope], token)
                    break
                except KeyError:
                    continue
            if value is None:
                raise KeyError(f"变量 ${{{token}}} 无法解析，请检查用例数据/业务数据定义")
        # 变量的值本身仍是 ${...} 时继续解析（如参数化行引用业务数据）
        if isinstance(value, str) and VAR_RE.search(value):
            return self.resolve(value, _depth + 1)
        return value

    def resolve(self, obj, _depth: int = 0):
        """递归解析字符串中的 ${var}；整体恰好是一个变量时保留原始类型（dict/list/int）"""
        if isinstance(obj, dict):
            return {k: self.resolve(v, _depth) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.resolve(v, _depth) for v in obj]
        if not isinstance(obj, str):
            return obj
        m = VAR_RE.fullmatch(obj.strip())
        if m:
            return self._resolve_token(m.group(1), _depth)
        return VAR_RE.sub(lambda mm: str(self._resolve_token(mm.group(1), _depth)), obj)

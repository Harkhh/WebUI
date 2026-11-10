"""Excel 用例模板生成器

用法:
  python tools/gen_excel_cases.py                     # 生成示例用例 data/cases/excel/login_cases.xlsx
  python tools/gen_excel_cases.py -o 新文件.xlsx       # 生成空白模板到指定路径

Excel 结构（两个 sheet）:
  sheet=Cases : case_id | title | level | priority | module | data
                - data 列填 JSON：dict 表示用例数据；list 表示参数化多组数据；留空表示无数据
  sheet=Steps : case_id | step | action | locator | value | expect
                - 同一 case_id 的步骤按 step 列排序执行
                - 除 case_id/step 外的列都会作为该步骤参数传入
"""
import argparse
import os

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASE_HEADERS = ["case_id", "title", "level", "priority", "module", "data"]
STEP_HEADERS = ["case_id", "step", "action", "locator", "value", "expect"]

SAMPLE_CASES = [
    ["xl_001", "Excel登录成功冒烟", "smoke", "P0", "登录", ""],
    ["xl_002", "Excel登录失败参数化", "regression", "P1", "登录",
     '[{"desc":"密码错误","username":"standard","password":"bad","expect_msg":"用户名或密码错误"},'
     '{"desc":"锁定用户","username":"locked","password":"123456","expect_msg":"账号已被锁定，请联系管理员"}]'],
]

SAMPLE_STEPS = [
    ["xl_001", 1, "goto", "", "/index.html", ""],
    ["xl_001", 2, "fill", "#username", "${business.users.demo_shop.standard_user.username}", ""],
    ["xl_001", 3, "fill", "#password", "${business.users.demo_shop.standard_user.password}", ""],
    ["xl_001", 4, "click", "#login-btn", "", ""],
    ["xl_001", 5, "assert_text", ".title", "", "商品列表"],
    ["xl_001", 6, "screenshot", "", "excel登录成功", ""],
    ["xl_002", 1, "goto", "", "/index.html", ""],
    ["xl_002", 2, "fill", "#username", "${username}", ""],
    ["xl_002", 3, "fill", "#password", "${password}", ""],
    ["xl_002", 4, "click", "#login-btn", "", ""],
    ["xl_002", 5, "assert_text", "#error", "", "${expect_msg}"],
    ["xl_002", 6, "screenshot", "", "excel登录失败_${desc}", ""],
]


def _style_header(ws) -> None:
    fill = PatternFill("solid", fgColor="1677FF")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = fill
    ws.freeze_panes = "A2"


def generate(path: str, sample: bool = True) -> None:
    wb = Workbook()
    ws_cases = wb.active
    ws_cases.title = "Cases"
    ws_cases.append(CASE_HEADERS)
    ws_steps = wb.create_sheet("Steps")
    ws_steps.append(STEP_HEADERS)

    if sample:
        for row in SAMPLE_CASES:
            ws_cases.append(row)
        for row in SAMPLE_STEPS:
            ws_steps.append(row)

    _style_header(ws_cases)
    _style_header(ws_steps)
    for ws, widths in ((ws_cases, [12, 30, 12, 10, 12, 60]),
                       (ws_steps, [12, 8, 16, 30, 40, 30])):
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)
    print(f"Excel 用例文件已生成: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Excel 用例模板生成器")
    parser.add_argument("-o", "--output",
                        default=os.path.join(ROOT, "data", "cases", "excel", "login_cases.xlsx"),
                        help="输出文件路径（默认生成示例用例）")
    parser.add_argument("--blank", action="store_true", help="生成空白模板（不含示例数据）")
    args = parser.parse_args()
    generate(args.output, sample=not args.blank)

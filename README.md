# Web UI 自动化测试框架（WebUI）

基于 **pytest + Playwright + Allure** 的 Web UI 自动化测试框架。以 YAML / Excel 关键字驱动为主，同时保留 Page Object 代码用例，内置变量引擎、业务数据分离、本地演示站点、失败截图、运行监测与开箱即用的中文 Allure 单文件报告。

## 目录

- [1. 功能特性](#1-功能特性)
- [2. 项目结构](#2-项目结构)
- [3. 环境准备](#3-环境准备)
- [4. 快速开始](#4-快速开始)
- [5. 运行方式](#5-运行方式)
- [6. 配置说明](#6-配置说明)
- [7. 用例编写](#7-用例编写)
- [8. 关键字（action）参考](#8-关键字action参考)
- [9. 变量系统](#9-变量系统)
- [10. 报告与日志](#10-报告与日志)
- [11. 常见问题](#11-常见问题)

## 1. 功能特性

| 特性 | 说明 |
| --- | --- |
| 关键字驱动 | 21 个内置 action，覆盖导航、输入、点击、等待、断言、截图等常用操作 |
| 双用例载体 | YAML（推荐）与 Excel（Cases + Steps 两个 sheet），零代码编写 |
| POM 支持 | 复杂流程可用 `pages/` 下的 Page Object + pytest 代码实现，两种方式并存 |
| 变量引擎 | `${env.*}` / `${business.*}` / 用例数据 / 运行期变量，支持嵌套与内置时间变量 |
| 数据分离 | 环境配置、业务数据、用例三者独立维护 |
| 本地演示站点 | `base_url` 指向 `127.0.0.1` 时自动拉起 `demo_site/`，端口被占用时复用已有服务 |
| 稳定与排障 | 失败自动截图、Playwright 自动等待、用例重跑与并行（pytest 插件生态） |
| 中文报告 | Allure 单文件报告（`--single-file`，双击即可打开）+ 中文本地化 + 历史趋势累积 |
| 运行监测 | 资源占用与用例过程监测，输出到日志目录 |

## 2. 项目结构

```text
WebUI/
├── config/
│   ├── config.yaml         # 主配置：浏览器、路径、报告、演示站点
│   └── env/                # 环境配置，按文件名切换（--env test / prod）
│       ├── test.yaml
│       └── prod.yaml
├── core/                   # 关键字引擎
│   ├── actions.py          # action 注册表与实现
│   ├── loader.py           # YAML / Excel 用例解析与校验
│   ├── models.py           # CaseData / Step 数据模型
│   ├── runner.py           # 用例执行器
│   └── var_parser.py       # 变量解析
├── data/
│   ├── business/           # 业务数据（账号、商品、预期文案等）
│   └── cases/              # YAML / Excel 用例
│       └── excel/          # Excel 用例
├── demo_site/              # 本地演示站点（纯静态页面）
├── pages/
│   └── base_page.py        # POM 基类，可继续扩展页面对象
├── testcases/
│   ├── test_yaml_cases.py  # YAML 用例统一入口
│   ├── test_excel_cases.py # Excel 用例统一入口
│   └── test_login_pom.py   # POM 代码用例示例
├── tools/
│   └── gen_excel_cases.py  # Excel 用例模板生成器
├── utils/                  # 配置、日志、监测、Allure 报告定制
├── reports/                # 运行产物（已 gitignore，仅保留占位文件）
├── logs/                   # 运行日志（已 gitignore）
├── conftest.py             # pytest 插件入口（参数、fixture、演示站点、失败截图）
├── pytest.ini
├── requirements.txt
└── run.py                  # 一键执行入口
```

## 3. 环境准备

要求 Python 3.9+（Python 3.14 亦可运行本框架）。

```bash
# 1. 创建虚拟环境（.venv 已被 gitignore，需要本地创建）
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器（首次必须执行）
python -m playwright install chromium
# 需要多浏览器时：python -m playwright install firefox webkit

# 4. 安装 Allure 命令行（可选，用于生成 HTML 报告）
brew install allure                # Windows: scoop install allure
```

## 4. 快速开始

```bash
python run.py                  # 全量用例，默认 test 环境、无头 chromium
python run.py --open           # 运行结束后自动打开 Allure 报告
```

默认环境 `test` 的 `base_url` 是 `http://127.0.0.1:8930`，框架会**自动拉起** `demo_site/` 静态站点（若该端口已有服务则直接复用），无需手动启动被测应用。

报告位置：`reports/allure-html/index.html`（单文件，直接双击即可在浏览器打开）。

## 5. 运行方式

### 5.1 run.py（推荐）

```bash
python run.py                                 # 全量用例
python run.py --level smoke                   # 只跑冒烟用例
python run.py --level regression              # 只跑回归用例
python run.py --env prod --browser firefox    # 切换环境与浏览器
python run.py -k login --headed               # 关键字过滤 + 有头模式
python run.py --no-report                     # 只跑用例，不生成 HTML 报告
python run.py --open                          # 生成报告后自动打开
```

| 参数 | 说明 |
| --- | --- |
| `--env` | 环境名，对应 `config/env/<env>.yaml` |
| `--browser` | `chromium` / `firefox` / `webkit` |
| `--headed` | 有头模式（调试时观察浏览器操作） |
| `--level` | `all` / `smoke` / `regression` |
| `-k` | 按用例名关键字过滤 |
| `--no-report` | 跳过 Allure HTML 生成 |
| `--open` | 生成后自动打开报告 |

### 5.2 直接使用 pytest

```bash
pytest                                   # 全部用例
pytest -m smoke                          # 冒烟用例
pytest -m "smoke and P0"                 # 组合标记
pytest --env prod --browser webkit       # 指定环境与浏览器
pytest --headed -k login                 # 有头调试
pytest testcases/test_excel_cases.py -v  # 只跑 Excel 用例
```

## 6. 配置说明

### 6.1 `config/config.yaml`（公共配置）

```yaml
env: test                  # 默认环境，可被 --env 覆盖
browser:
  type: chromium           # chromium / firefox / webkit
  headless: true
  slow_mo: 0               # 每步操作延迟（毫秒），调试用
  timeout: 10              # 元素操作默认超时（秒）
  user_agent: ...          # 自定义 UA
  stealth: true            # 隐藏 navigator.webdriver 等自动化特征
  viewport: { width: 1280, height: 720 }
paths:
  cases_dir: data/cases
  excel_cases_dir: data/cases/excel
  business_dir: data/business
  reports_dir: reports
  logs_dir: logs
demo_server:               # base_url 指向本机时自动拉起
  port: 8930
  doc_root: demo_site
report:
  title: UI自动化测试报告
  build_name: ""           # 留空自动使用 run_id
  custom_css: ""           # 注入报告的自定义样式
```

### 6.2 `config/env/<env>.yaml`（环境配置）

```yaml
# config/env/test.yaml
base_url: http://127.0.0.1:8930
project: 演示商城
```

主配置与环境配置会**深度合并**，环境文件中的同名字段覆盖主配置。

## 7. 用例编写

### 7.1 YAML 用例（推荐）

放在 `data/cases/` 下（以 `_` 开头的文件仅作模板参考，不会被执行），结构如下：

```yaml
suite: 登录模块            # 套件名，缺省注入为每条用例的 module
cases:
  - id: login_001          # 必填，用例唯一标识
    title: 标准用户登录成功进入商品页
    level: smoke           # smoke / regression
    priority: P0           # P0~P3，映射 Allure 严重级别
    data:                  # 用例数据，可用 ${...} 引用业务数据
      user: ${business.users.demo_shop.standard_user}
    steps:
      - action: goto
        value: /index.html
      - action: fill
        locator: "#username"
        value: ${user.username}
      - action: fill
        locator: "#password"
        value: ${user.password}
      - action: click
        locator: "#login-btn"
      - action: assert_url
        expect: products.html
      - action: assert_text
        locator: .title
        expect: 商品列表
      - action: screenshot
        value: 登录成功
```

### 7.2 参数化

```yaml
  - id: login_002
    title: 登录失败提示
    parametrize:                 # 每行展开为一条独立用例（id 追加 _p1/_p2...）
      - desc: 密码错误
        username: standard
        password: wrong_password
        expect_msg: ${business.users.demo_shop.msg_invalid}
      - desc: 用户不存在
        username: nobody
        password: "123456"
        expect_msg: ${business.users.demo_shop.msg_invalid}
    steps:
      - action: goto
        value: /index.html
      - action: fill
        locator: "#username"
        value: ${username}
      - action: fill
        locator: "#password"
        value: ${password}
      - action: click
        locator: "#login-btn"
      - action: assert_text
        locator: "#error"
        expect: ${expect_msg}
```

完整的语法全集见 `data/cases/_example_full.yaml`。

### 7.3 Excel 用例

`data/cases/excel/*.xlsx`，需要 **Cases** 与 **Steps** 两个 sheet：

- `Cases`：`case_id | title | level | priority | module | data`
  - `data` 列填 JSON：对象表示用例数据，数组表示参数化多组数据，留空表示无数据
- `Steps`：`case_id | step | action | locator | value | expect`
  - 同一 `case_id` 的步骤按 `step` 列升序执行，除 `case_id` / `step` 外的列作为该步骤参数

生成模板：

```bash
python tools/gen_excel_cases.py                 # 生成示例用例
python tools/gen_excel_cases.py -o 新文件.xlsx   # 生成空白模板
```

### 7.4 POM 代码用例

复杂业务流程可在 `pages/` 继承 `BasePage` 封装页面对象，用 pytest 编写：

```python
from pages.base_page import BasePage

def test_login(page):
    bp = BasePage(page)
    bp.goto("/index.html")
    bp.fill("#username", "standard")
    bp.fill("#password", "123456")
    bp.click("#login-btn")
    assert "products.html" in page.url
```

示例见 `testcases/test_login_pom.py`。YAML/Excel 用例与 POM 用例可在同一次运行中混跑。

## 8. 关键字（action）参考

每个步骤至少包含 `action`，其余键作为该 action 的参数；必填参数缺失时用例加载阶段即报错。

| 分类 | action | 参数 | 说明 |
| --- | --- | --- | --- |
| 导航 | `goto` | `value` | 打开页面，相对路径自动拼接 `base_url` |
| | `scroll` | `value`[, `locator`] | 滚动指定像素；给 locator 时滚动至元素 |
| 等待 | `wait` | `value` | 强制等待秒数（建议优先用 `wait_for`） |
| | `wait_for` | `locator`[, `state`] | 等待元素状态：visible / hidden / attached / detached |
| 操作 | `click` / `dblclick` | `locator` | 单击 / 双击 |
| | `fill` | `locator`, `value` | 清空并输入 |
| | `clear` | `locator` | 清空输入框 |
| | `press` | `key`[, `locator`] | 按键，如 `Enter` |
| | `hover` | `locator` | 悬停 |
| | `select` | `locator`, `value` | 下拉框选择 |
| | `check` / `uncheck` | `locator` | 勾选 / 取消勾选 |
| 取值 | `save_text` | `locator`, `value` | 保存元素文本到变量，`value` 为变量名 |
| | `save_attr` | `locator`, `attr`, `value` | 保存元素属性到变量 |
| 断言 | `assert_visible` / `assert_hidden` | `locator` | 元素可见 / 隐藏 |
| | `assert_text` | `locator`, `expect` | 文本完全等于 |
| | `assert_contains` | `locator`, `expect` | 文本包含；`locator: url` 时断言地址包含 |
| | `assert_title` | `expect` | 页面标题等于 |
| | `assert_url` | `expect` | 当前 URL 包含 |
| | `assert_count` | `locator`, `expect` | 元素数量等于 |
| 截图 | `screenshot` | [`value`] | 主动截图并挂到 Allure，`value` 为截图名 |

**定位语法**：默认 CSS；支持 `css=选择器`、`xpath=表达式`、`text=文本`、`id=元素id`（等价 `#id`）。

## 9. 变量系统

### 9.1 语法与优先级

`${...}`，解析优先级由高到低：

1. **runtime** 运行期变量（`save_text` / `save_attr` 保存，后续步骤可用）
2. **data** 用例数据（含参数化行数据）
3. **business** `data/business/*.yaml` 合并后的数据，按文件名分组
4. **env** `config/env/<env>.yaml`

内置变量：`${timestamp}`（秒级时间戳）、`${today}`（YYYY-MM-DD）、`${now}`（YYYY-MM-DD HH:MM:SS）。

### 9.2 常用写法

```yaml
value: ${business.users.demo_shop.standard_user.username}   # 业务数据
value: ${business.users.demo_shop.msg_invalid}               # 预期文案也放在业务数据中
value: ${env.base_url}/index.html                            # 环境配置
value: ${user.username}                                      # 用例 data 中的对象字段
value: ${desc}_${timestamp}                                  # 支持嵌套与拼接
```

变量值本身仍是 `${...}` 时会继续解析（最多 5 层），整体恰好是一个变量时保留原始类型（dict / list / int）。

## 10. 报告与日志

| 产物 | 路径 | 说明 |
| --- | --- | --- |
| Allure 报告 | `reports/allure-html/index.html` | 单文件模式，双击即可打开；已做中文本地化与标题定制 |
| Allure 原始结果 | `reports/allure-results/` | 每次运行自动清理 |
| 趋势历史 | `reports/history/` | 跨次运行累积，报告中展示趋势 |
| 失败截图 | `reports/screenshots/<run_id>/` | 用例失败自动截图并附到报告 |
| 运行日志 | `logs/<run_id>/` | 每次运行独立目录 |
| 资源监测 | 日志目录 | CPU / 内存等运行期指标 |

`reports/`、`logs/` 属于运行产物，已被 `.gitignore` 排除，仓库中仅保留目录占位文件。

## 11. 常见问题

**Q：提示浏览器不存在 / `Executable doesn't exist`？**
执行 `python -m playwright install chromium`（或 `playwright install --with-deps`）。

**Q：`未检测到 allure 命令行工具`？**
用例仍会执行，只是不生成 HTML 报告。安装后可重跑：macOS `brew install allure`，或从 [Allure Releases](https://github.com/allure-framework/allure2/releases) 下载解压并加入 PATH。

**Q：报告打开是空白页？**
本框架使用 `--single-file` 生成单文件报告；若手动执行 `allure generate`，请务必加上 `--single-file`，否则 `file://` 直开会被浏览器拦截 AJAX 请求。

**Q：提示端口 8930 被占用？**
若占用方不是演示站点，修改 `config/env/test.yaml` 的 `base_url` 端口并同步 `config/config.yaml` 的 `demo_server.port`；或直接使用其他环境。

**Q：用例加载时报“未知 action / 缺少必填参数”？**
对照 [第 8 节关键字表](#8-关键字action参考) 检查 `action` 拼写与必填参数；`core/loader.py` 在运行前会统一校验并给出可用 action 列表。

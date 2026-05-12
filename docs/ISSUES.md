# 问题记录

本文档记录项目实测和开发过程中遇到的问题、原因、修复方式和验证结果。后续每个外设遇到的问题都追加到这里，方便复盘和避免重复踩坑。

## 记录模板

```text
日期：
阶段/外设：
现象：
原因：
修复：
验证：
状态：
关联提交：
```

## 2026-05-08 GPIO 板卡依赖安装后运行失败

阶段/外设：GPIO 实测准备，Board Agent 部署到 RK3568 板卡。

现象：

- 在板卡执行 `pip3 install -r requirements.txt` 后，依赖安装最终显示成功，但 pip 提示 `typing-extensions` 版本不兼容。
- 随后执行 `from board_agent.app import create_app` 失败。
- 关键错误：

```text
TypeError: Unable to evaluate type annotation 'list[str]'.
If you are making use of the new typing syntax ... install the eval_type_backport package.
```

环境：

```text
Board OS: Ubuntu 20.04.6 LTS
Board Python: 3.8.10
Board pip: 20.0.2
```

原因：

- 代码中使用了 `list[str]`、`dict[str, Any]` 等较新的类型标注写法。
- Pydantic v2 在 Python 3.8 上解析这些类型标注时需要额外兼容依赖。
- 板卡已有 `typing-extensions 4.10.0`，低于 Pydantic 当前依赖要求。

修复：

- 在 `requirements.txt` 中增加：

```text
typing-extensions>=4.12.2
eval-type-backport>=0.2,<1.0
```

- 在板卡重新执行：

```bash
pip3 install -r requirements.txt
```

验证：

```text
from board_agent.app import create_app
app = create_app()
app ok RK3568 Test Box Board Agent
```

状态：已修复。

关联提交：

```text
e57e157 Fix board dependency compatibility
```

## 2026-05-08 GPIO 任务执行在 Python 3.8 上失败

阶段/外设：GPIO 实测准备，Board Agent 任务执行。

现象：

- Web/API 可访问，`/api/health`、`/api/system`、`/api/resources` 正常。
- 提交 GPIO `info/read/write dry-run` 任务后失败。
- 关键错误：

```text
module 'asyncio' has no attribute 'to_thread'
```

原因：

- `asyncio.to_thread` 是 Python 3.9 引入的 API。
- 板卡 Python 版本为 3.8.10，不支持该 API。

修复：

- 将任务执行中的：

```python
await asyncio.to_thread(self._dispatch, record.request)
```

- 改为 Python 3.8 可用的：

```python
loop = asyncio.get_running_loop()
await loop.run_in_executor(None, self._dispatch, record.request)
```

验证：

```text
GET / -> 200
GET /api/health -> 200
GET /api/system -> 200
GET /api/resources -> 200
GPIO info -> completed
GPIO read /dev/gpiochip0 line 0 -> completed, value 0
GPIO write dry-run /dev/gpiochip0 line 0 value 1 duration_ms 200 -> completed
```

状态：已修复。

关联提交：

```text
e57e157 Fix board dependency compatibility
```

## 2026-05-08 从非项目目录启动时报找不到 board_agent

阶段/外设：GPIO 实测准备，Board Agent 启动。

现象：

- 用户在板卡执行：

```bash
RK_BOX_MODE=auto RK_BOX_HOST=0.0.0.0 RK_BOX_PORT=8080 python3 -m board_agent
```

- Python 提示找不到模块：

```text
No module named board_agent
```

原因：

- `board_agent` 当前是项目内源码包，还没有安装成系统级 Python package。
- `python3 -m board_agent` 会从当前目录和 Python 搜索路径查找模块。
- 如果当前目录是 `/root`，而项目实际目录是 `/root/rk3568_finger_box`，Python 就找不到 `board_agent`。

验证：

```text
cd /root/rk3568_finger_box
python3 -c 'import board_agent; print(board_agent.__file__)'
-> /root/rk3568_finger_box/board_agent/__init__.py

cd /root
python3 -c 'import importlib.util; print(importlib.util.find_spec("board_agent"))'
-> None
```

修复：

- 新增启动脚本：

```text
scripts/run_board_agent.sh
```

- 脚本会自动切到项目根目录，再执行：

```bash
python3 -m board_agent
```

推荐启动方式：

```bash
cd /root/rk3568_finger_box
./scripts/run_board_agent.sh
```

验证：

```text
Started from /root:
  /root/rk3568_finger_box/scripts/run_board_agent.sh
Board service:
  PID 392691
  LISTEN 0.0.0.0:8080
GET /api/health -> 200
```

状态：已修复，脚本已同步到板卡并验证可用。

## 2026-05-10 Web 实时日志长行撑宽页面

阶段/外设：GPIO 实测阶段，Web 控制台。

现象：

- 点击“测试任务”的 `ping` 执行按钮后，实时日志会打印较长任务 JSON。
- 日志区域按单行显示，导致页面被横向撑宽，浏览器视图被拖到右侧，影响操作体验。

原因：

- 实时日志使用 `<pre>` 显示，浏览器默认保留空白且不自动换行。
- `.log` 和 `.result` 没有限制长字符串换行，长 JSON 会撑开布局。

修复：

- 为日志和结果区域增加 `white-space: pre-wrap` 与 `overflow-wrap: anywhere`。
- 为页面布局、面板、表单标签增加最小宽度约束，避免子内容撑开父容器。
- 禁止页面整体横向溢出，保持初始 UI 宽度。

验证：

```text
MacBook Safari -> http://192.168.2.88:8080
提交 dry-run ping 任务 -> Task queued
实时日志中的 task.updated 长 JSON 在日志面板内自动换行，页面不再被横向撑宽。
```

状态：已修复，已在板卡 Web 控制台验证。

## 2026-05-13 GPIO 保持时间语义与真实电平不一致

阶段/外设：GPIO 实测阶段，GPIO 输出。

现象：

- Web 面板设置输出高电平，保持时间为 200ms。
- 逻辑分析仪实测发现 GPIO 没有在 200ms 后自动回到低电平，而是一直保持高电平。
- 点击“读取”后，电平才变化为低电平。

原因：

- 后端使用 `gpioset --mode=time`，它只保证 `gpioset` 进程持有 line 指定时长。
- 进程退出后 GPIO line 被释放，后续电平由硬件默认状态、上下拉、复用配置等决定，并不保证自动拉低。
- `gpioget` 读取时会重新申请该 line，可能改变方向或释放原输出状态，导致实测电平变化。
- 对测试盒场景来说，“保持 ms”增加理解成本，也不能表达用户期望的“输出高/低并保持”。

修复：

- 移除 Web GPIO 面板中的“保持 ms”和输出值下拉。
- 将操作简化为“读取 / 输出低 / 输出高”。
- 后端 GPIO 输出改用 `gpioset --mode=signal`，由 Board Agent 持有输出进程。
- 同一 chip/line 再次输出时先停止旧输出进程，再启动新输出进程，实现高/低电平切换。
- 读取当前由 Board Agent 持有输出的 line 时，直接返回已持有的输出值，避免 `gpioget` 改变该 line 状态。

验证：

```text
本地自动化测试：pytest -> passed
板端上传并重启服务后验证：
  GET /api/health -> 200
  GPIO dry-run 输出高 -> completed, command 使用 gpioset --mode=signal
```

状态：已修复，等待用户用逻辑分析仪验收真实 GPIO 电平保持和切换。

## 2026-05-10 GPIO 面板宽屏控件间距和信息结果排版不友好

阶段/外设：GPIO 实测阶段，Web 控制台。

现象：

- Safari 全屏打开 `http://192.168.2.88:8080` 后，Dry run/确认写入的复选框和文字距离不协调。
- 点击 GPIO“信息”后，结果区域直接展示完整任务 JSON，`gpioinfo` 文本混在 JSON 字符串里，难以阅读。

原因：

- 前端样式把普通输入框和 checkbox 统一设置为 `width: 100%`，导致 checkbox 在 Safari 下布局异常。
- GPIO 任务结果使用 `JSON.stringify(task, null, 2)` 直接渲染，没有针对 `info/read/write` 做用户友好的结果视图。

修复：

- 将 checkbox 样式从普通 input 中拆出，固定尺寸并紧贴标签文字。
- 调整 GPIO 表单网格列宽，让 Dry run、确认写入和按钮在宽屏下自然对齐。
- 新增 GPIO 任务结果渲染逻辑：任务摘要、芯片/来源信息、GPIO line 表格。
- `read` 和 `write` 结果也改为简洁摘要，调试原始事件仍保留在实时日志里。

验证：

```text
MacBook Safari -> http://192.168.2.88:8080
刷新页面后，GPIO 面板 Dry run/确认写入显示紧凑。
点击 GPIO 信息 -> 返回 completed 摘要、芯片信息和 line 表格。
```

状态：已修复，已在板卡 Web 控制台验证。

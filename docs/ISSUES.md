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

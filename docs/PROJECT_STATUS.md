# 项目执行进度

更新时间：2026-05-07

## 当前阶段

项目处于 **GPIO 外设可测试，暂停等待用户实测** 阶段。

当前可以实测：

- 本地或板端启动 Board Agent 服务。
- 打开 Web 控制台。
- 查看健康检查、系统信息、资源枚举。
- 提交 dry-run 测试任务。
- 通过 WebSocket 查看实时日志。
- 使用 mock 模式模拟 GPIO、I2C、UART、CAN、PWM、ADC 资源。
- 在板卡真实模式下测试 GPIO 信息、GPIO 输入读取、短时 GPIO 输出。

当前还不能直接用于真实控制板卡外设：

- I2C/UART/CAN/PWM/ADC 的真实 Hardware Adapter 尚未实现。
- 还没有完成资源锁、审计日志和全部接口级参数校验。
- 不建议对 `gpioinfo` 标记为 `[used]` 的 GPIO line 做输出测试。

## 已完成

- 项目文档：
  - `README.md`
  - `docs/DESIGN.md`
  - `AGENTS.md`
  - `docs/PROJECT_STATUS.md`
- Git 仓库初始化。
- Board Agent MVP：
  - `GET /api/health`
  - `GET /api/system`
  - `GET /api/resources`
  - `POST /api/tasks`
  - `GET /api/tasks/{id}`
  - `WS /ws/events`
- Web 控制台 MVP：
  - 设备状态展示。
  - 系统信息展示。
  - 外设资源展示。
  - dry-run 测试任务提交。
  - 实时日志面板。
- 模拟模式：
  - `RK_BOX_MODE=mock`。
  - 无板卡时可开发和验证 UI/API 主链路。
- 基础安全保护：
  - 非 dry-run 的真实写操作默认要求 `confirm=true`。
  - UI 不直接拼 shell，统一通过 Board Agent API。
- 基础测试：
  - mock 系统信息。
  - mock 外设资源。
  - 写操作确认拦截。
  - API 健康检查和任务提交。
- GPIO Adapter：
  - `info`：调用 `gpioinfo` 查看 GPIO chip/line 信息。
  - `read`：调用 `gpioget` 读取一个或多个 GPIO line。
  - `write`：调用 `gpioset --mode=time` 做短时输出。
  - 支持 `dry_run` 和 mock 模式。
  - 写操作需要 `confirm=true`，否则后端拒绝。
  - 支持 chip、line、value、duration_ms、active_low 参数校验。
- Web GPIO 面板：
  - GPIO 信息。
  - GPIO 读取。
  - GPIO 输出。
  - Dry run 和确认写入开关。

## 待完成

- 真实板卡部署验证：
  - 将 Board Agent 部署到 `192.168.2.88`。
  - 在板卡上安装依赖并启动服务。
  - 从电脑访问 `http://192.168.2.88:8080`。
  - 验证真实 `/api/system` 和 `/api/resources` 输出。
- GPIO Adapter 后续增强：
  - 边沿事件监听。
  - line 占用可视化。
  - 更友好的 40pin 引脚映射。
  - 资源锁和审计日志。
- I2C Adapter：
  - 总线扫描。
  - 寄存器读写。
  - 地址范围校验。
  - 常见器件模板。
- UART/RS232/RS485 Adapter：
  - 串口参数配置。
  - 收发数据。
  - 循环发送。
  - RS485 半双工方向控制策略。
- CAN Adapter：
  - CAN 接口状态读取。
  - 波特率配置。
  - 帧发送。
  - 帧监听。
  - 过滤器和错误统计。
- PWM Adapter：
  - PWM chip/channel 枚举。
  - 周期、占空比、启停控制。
  - 长时间输出保护。
- ADC Adapter：
  - 实际 ADC 节点确认。
  - 通道读取。
  - 电压换算和阈值判断。
- 任务与报告：
  - 资源锁。
  - 审计日志。
  - 测试报告导出。
  - 批量测试流程。
- 交付：
  - systemd 服务文件。
  - 板端一键启动脚本。
  - Windows 桌面封装评估。

## 下一步计划

当前暂停，等待用户实测 GPIO。

用户测试 GPIO 通过后，下一步进入 I2C Adapter：

1. I2C 总线扫描。
2. I2C 地址范围校验。
3. I2C 寄存器读写 dry-run 和真实模式。
4. 更新状态文档并暂停让用户实测 I2C。

## 迭代执行流程

项目按“单个外设可测试”为里程碑推进。每完成一个外设控制能力，就暂停开发并交给用户实测。

固定循环：

1. 读取本文件，确认当前阶段和下一个外设目标。
2. 实现当前外设的最小可测试能力。
3. 补充或更新自动化测试。
4. 本地运行验证。
5. 更新 `docs/PROJECT_STATUS.md`，记录已完成能力、测试入口、已知限制和下一步。
6. 停下来通知用户实测当前外设。
7. 如果用户反馈 bug，优先修 bug，更新状态文档后再次交给用户测试。
8. 用户确认当前外设测试通过后，再继续下一个外设。

外设推进顺序：

1. GPIO
2. I2C
3. UART
4. RS232/RS485
5. CAN
6. PWM
7. ADC/电压采样
8. 测试报告、批量测试、Windows 封装等增强功能

每个外设完成节点必须满足：

- Web UI 有对应入口或明确的 API 测试方法。
- Board Agent 有对应 Adapter 或任务处理逻辑。
- 后端有参数校验和错误返回。
- 真实写操作有 `confirm=true` 或 UI 确认路径。
- 状态文档写明“现在可以测什么、不要测什么”。
- 开发者暂停，不主动继续下一个外设，等待用户测试结果或“项目继续”指令。

## 实测边界

现在适合测试：

- 本地 mock 控制台是否能打开。
- Web UI 是否能刷新系统和资源信息。
- dry-run 任务是否能提交并在日志中显示。
- WebSocket 是否会实时推送任务事件。
- 板卡真实模式下的 GPIO 信息、读取和短时输出。

现在不适合测试：

- 真实 I2C 写寄存器。
- 真实 UART/RS485 连续发送。
- 真实 CAN 发帧。
- 真实 PWM 输出。
- 修改 `/boot/uEnv`、设备树 overlay、CAN 波特率等系统状态。

## GPIO 实测步骤

在板卡上启动 Board Agent：

```bash
cd /root/rk3568_finger_box
pip3 install -r requirements.txt
RK_BOX_MODE=auto RK_BOX_HOST=0.0.0.0 RK_BOX_PORT=8080 python3 -m board_agent
```

在电脑浏览器打开：

```text
http://192.168.2.88:8080
```

建议测试顺序：

1. 打开 GPIO 测试面板。
2. 保持 Dry run 勾选，点击“信息”，确认能看到 `gpioinfo` 输出。
3. 保持 Dry run 勾选，选择空闲 line，点击“读取”。
4. 接好 LED 和限流电阻，或用万用表连接确认安全的 GPIO line。
5. 取消 Dry run，勾选“确认写入”。
6. 设置 `duration_ms=200` 到 `1000`，点击“输出”。
7. 观察 LED/万用表变化，并查看实时日志和任务结果。

GPIO 测试注意事项：

- 不要对 `gpioinfo` 显示 `[used]` 的 line 做输出测试。
- 不要直接把 GPIO 接到 5V。
- 输出测试建议先从 200ms 短时脉冲开始。
- 如果不确定 40pin 对应关系，先只做“信息”和“读取”，不要做“输出”。

## 验证记录

最近一次本地验证：

```text
python3 -m compileall board_agent tests
pytest -q
11 passed
```

本地 mock 服务已验证：

```text
GET /api/health -> 200
GET /api/system -> 200
GET /api/resources -> 200
POST /api/tasks dry_run -> queued
```

GPIO 验证：

```text
GPIO Adapter mock read -> passed
GPIO Adapter mock write command -> passed
GPIO invalid line validation -> passed
GPIO real read parser with fake runner -> passed
confirmed GPIO write task accepted -> passed
```

## Git 远端与同步记录

远端仓库：

```text
https://github.com/lc285800/rk3568-test-box.git
```

当前远端配置：

```bash
git remote add origin https://github.com/lc285800/rk3568-test-box.git
git push -u origin main
```

该流程已跑通。首次推送记录：

```text
670a5e9 Initial RK3568 test box MVP
main -> origin/main
```

后续常规同步流程：

```bash
git status --short
git add .
git commit -m "<本次变更摘要>"
git push
```

如果远端已存在但需要确认地址：

```bash
git remote -v
```

## 状态维护规则

- 每次完成一个功能、发现一个限制、改变下一步计划，都要更新本文件。
- `docs/DESIGN.md` 记录稳定架构，不作为每日进度记录。
- `README.md` 面向使用者，只放当前阶段摘要和入口。
- `AGENTS.md` 面向后续工程代理，必须提醒先读本文件。

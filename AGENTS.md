# AGENTS.md

本文件给后续在本仓库工作的 Codex 或工程代理使用。项目目标是把鲁班猫 2 金手指 RK3568 板卡做成 Web 控制的嵌入式接口测试盒。

## 项目默认决策

- 上位机第一版采用 Web 控制台，不优先做 Windows 原生软件。
- 电脑与测试盒默认通过以太网/LAN 通信。
- 板卡默认地址为 `192.168.2.88`，实际实现应支持配置化。
- 首版聚焦 GPIO、I2C、UART/RS232/RS485、CAN、PWM、ADC/电压采样。
- Board Agent 首版推荐 Python + FastAPI，前端可按项目后续实际技术栈选择。
- REST 用于配置和动作请求，WebSocket 用于实时日志、任务进度和状态推送。

## 工作原则

- 优先阅读 `README.md`、`docs/DESIGN.md` 和 `docs/PROJECT_STATUS.md`，保持实现与文档一致。
- 每次新增或调整功能时，同步更新 `docs/PROJECT_STATUS.md`。如果影响用户使用或架构，再同步更新 README 或设计文档。
- 回答项目当前阶段、能否实测、下一步做什么时，以 `docs/PROJECT_STATUS.md` 为准。
- 项目按单个外设里程碑推进。完成一个外设能力后必须暂停，更新 `docs/PROJECT_STATUS.md`，让用户实测；用户反馈 bug 时优先修 bug；用户确认通过或明确说“项目继续”后，再进入下一个外设。
- 默认先实现模拟模式和只读探测接口，再实现真实硬件写操作。
- UI 不允许直接拼接 shell 命令；必须通过 Board Agent 的结构化 API 调用外设适配器。
- 外设适配器按 GPIO、I2C、UART、CAN、PWM、ADC 分开封装，避免把不同总线逻辑混在一起。
- 参数校验和错误处理放在后端，前端校验只能作为用户体验补充。

## 硬件安全要求

- 不要在没有明确需求时对真实外设执行写操作。
- GPIO 输出、PWM 输出、CAN 发送、UART/RS485 连续发送等动作必须有明确参数和用户确认路径。
- 修改 `/boot/uEnv`、设备树 overlay、网络接口、CAN 波特率等会影响系统状态的动作必须单独记录，并提示是否需要重启。
- 同一硬件资源不能被多个写任务同时占用。实现时需要资源锁或任务队列。
- 所有外设访问都要设置超时，失败时返回可读错误并写入日志。
- 保留审计日志：记录接口、动作、参数摘要、执行时间、结果和错误。

## 板卡探测基线

当前已知板卡资源：

- 系统：Ubuntu 20.04.6 LTS。
- 内核：Linux 4.19.232。
- CPU：4 核 Cortex-A55，aarch64。
- 内存：约 3.8 GiB。
- 网络：`eth0=192.168.2.88/24`。
- CAN：`can0`、`can1`。
- GPIO：`/dev/gpiochip0` 至 `/dev/gpiochip5`。
- I2C：`/dev/i2c-0`、`/dev/i2c-5`、`/dev/i2c-6`。
- UART：`/dev/ttyS3`、`/dev/ttyS7`、`/dev/ttyS9`。
- PWM：`/sys/class/pwm`。

已知可用工具包括 `python3`、`pip3`、`gcc`、`gpiodetect`、`gpioinfo`、`gpioset`、`gpioget`、`i2cdetect`、`i2cget`、`i2cset`、`candump`、`cansend`、`ip`、`stty`。

## 推荐实现顺序

已完成：

- 建立 Board Agent 项目骨架，提供 `GET /api/health`、`GET /api/system`、`GET /api/resources`。
- 增加模拟模式，保证没有真实板卡时也能开发前端。
- 建立 Web 控制台骨架，包含设备首页、接口资源展示、实时日志。
- 实现任务模型和 `WS /ws/events`。
- 实现 GPIO Adapter 的 `info/read/write` 最小可测试能力。
- 实现 Web GPIO 测试面板。

下一步：

1. 当前暂停等待用户实测 GPIO。
2. 用户反馈 GPIO bug 时，优先修 GPIO bug。
3. 用户确认 GPIO 通过或明确说“项目继续”后，实现 I2C Adapter。
4. 后续按 UART、RS232/RS485、CAN、PWM、ADC 顺序推进。
5. 每完成一个外设，更新 `docs/PROJECT_STATUS.md` 并停下来让用户测试。

## 验证要求

- 文档变更后检查 Markdown 链接和标题结构。
- 后端实现后至少覆盖健康检查、资源枚举、参数校验、模拟任务、错误返回。
- 前端实现后至少验证 Mac 和 Windows 浏览器兼容性。
- 涉及真实板卡的测试必须先运行只读探测，再运行写操作。

## Git 同步流程

远端仓库已配置为：

```text
https://github.com/lc285800/rk3568-test-box.git
```

首次远端配置和推送已跑通：

```bash
git remote add origin https://github.com/lc285800/rk3568-test-box.git
git push -u origin main
```

后续提交和推送使用：

```bash
git status --short
git add .
git commit -m "<本次变更摘要>"
git push
```

推送前先确认测试和状态文档已经更新。不要提交 `.venv/`、`.pytest_cache/` 或其它被 `.gitignore` 忽略的本地缓存。

## 参考资料

- [野火 LubanCat-RK356x 快速使用手册](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/index.html)
- [LubanCat-RK356x 40pin 引脚对照说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/40pin.html)
- [GPIO 控制说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/gpio/gpio.html)

# RK3568 测试工具盒设计说明

## 1. 目标与架构选择

本项目的目标是把鲁班猫 2 金手指 RK3568 板卡做成通用嵌入式接口测试盒，并提供一个小白可用的图形化上位机软件。第一版选择 Web 控制台优先，而不是直接开发 Windows 原生软件。

选择 Web 优先的原因：

- 跨平台迁移方便：MacBook 和 Windows 都可以使用浏览器调试。
- 部署简单：板卡提供控制台页面和 API，电脑无需安装复杂驱动。
- 后续可封装：需要 Windows 软件形态时，可以复用 Web 前端，用 Tauri 或 Electron 打包。
- 适合实时控制：HTTP 适合配置和动作请求，WebSocket 适合日志、任务进度和总线监听。

默认连接方式是以太网/LAN。电脑和测试盒处于同一局域网，浏览器访问板卡 IP，例如 `http://192.168.2.88`。USB 虚拟网卡和串口直连可作为后续补充，不作为首版主通道。

## 2. 当前硬件与系统基线

已探测到的板卡基线：

- 板卡：鲁班猫 2 金手指板卡，RK3568。
- 系统：Ubuntu 20.04.6 LTS。
- 内核：Linux 4.19.232。
- 架构：aarch64，4 核 Cortex-A55。
- 内存：约 3.8 GiB。
- 网络：`eth0=192.168.2.88/24`，`can0`/`can1` 存在但当前 DOWN。
- GPIO：`/dev/gpiochip0` 至 `/dev/gpiochip5`。
- I2C：`/dev/i2c-0`、`/dev/i2c-5`、`/dev/i2c-6`。
- UART：`/dev/ttyS3`、`/dev/ttyS7`、`/dev/ttyS9`。
- PWM：`/sys/class/pwm` 存在。

当前 `/boot/uEnv/uEnv.txt` 指向 `uEnvLubanCat2IO.txt`，已启用的典型 overlay 包括 `can1-m1`、`canfd2-m0`、`uart3-m1`、`uart7-m1`、`uart9-m1`、`2io-rs485-1` 等。修改设备树 overlay、`/boot/uEnv` 或 CAN 波特率等系统状态时，需要明确记录并提示是否需要重启。

## 3. 系统模块

### Web UI

Web UI 是用户主要入口，负责让非专业用户通过表单、按钮、状态灯和日志面板完成接口测试。

核心页面：

- 设备首页：显示板卡在线状态、IP、系统信息、资源摘要和服务版本。
- 接口面板：GPIO、I2C、UART/RS232/RS485、CAN、PWM、ADC 分面板操作。
- 测试任务：选择测试模板、执行单项或批量测试、查看进度。
- 日志与报告：实时日志、错误信息、测试结果、导出记录。
- 设置页：网络连接、权限确认、模拟模式、危险操作开关。

UI 不直接拼接 shell 命令，也不直接暴露 Linux 设备节点的写操作。所有动作都通过 Board Agent 的结构化 API 完成。

### Board Agent

Board Agent 运行在 RK3568 板卡上，是唯一允许访问外设的服务。首版推荐使用 Python + FastAPI 实现。

职责：

- 提供 REST API：系统信息、资源枚举、配置读取、测试动作提交、报告查询。
- 提供 WebSocket：实时日志、任务进度、总线监听、设备状态推送。
- 管理任务执行：每个测试动作生成任务 ID，记录输入参数、执行状态、输出和错误。
- 管理权限：真实写操作必须经过后端校验；危险操作需要显式确认字段。
- 封装外设适配器：统一错误处理、超时控制、日志格式和模拟模式。

### Hardware Adapters

每类外设独立封装，不让上层关心命令行细节。

- GPIO Adapter：基于 `libgpiod` 工具或库实现芯片枚举、line 信息、输入读取、输出置位、事件监听。
- I2C Adapter：基于 `/dev/i2c-*` 和 `i2c-tools` 实现总线扫描、寄存器读写和常见设备模板。
- UART Adapter：基于串口库和 `/dev/ttyS*` 实现波特率、数据位、校验位、停止位、收发和日志。
- RS232/RS485 Adapter：复用 UART 能力，RS485 增加半双工方向控制、收发时序和 jumper/overlay 提示。
- CAN Adapter：基于 SocketCAN 和 `can-utils` 实现接口状态、波特率配置、发送、监听、过滤和错误统计。
- PWM Adapter：基于 `/sys/class/pwm` 实现 export、周期、占空比、启停控制。
- ADC Adapter：基于板卡实际 ADC 节点实现通道读取、量程转换、阈值判断和趋势记录。

所有 Adapter 都需要支持模拟模式。模拟模式返回稳定的假数据和可预测错误，方便没有真实板卡时开发 UI。

## 4. API 与数据流

建议 API 分层：

- `GET /api/health`：服务健康检查。
- `GET /api/system`：系统、内核、CPU、内存、网络信息。
- `GET /api/resources`：列出 GPIO、I2C、UART、CAN、PWM、ADC 资源。
- `POST /api/tasks`：提交测试任务，请求体包含接口类型、动作、参数和确认字段。
- `GET /api/tasks/{id}`：查询任务状态和结果。
- `GET /api/reports/{id}`：读取测试报告。
- `WS /ws/events`：推送日志、任务进度、监听数据和状态变化。

典型数据流：

1. 浏览器打开 Web UI，调用 `GET /api/health` 和 `GET /api/resources`。
2. 用户选择接口类型并填写参数。
3. UI 提交 `POST /api/tasks`，Board Agent 校验参数并创建任务。
4. 任务执行器调用对应 Hardware Adapter。
5. Adapter 将日志和中间结果写入事件流。
6. UI 通过 WebSocket 实时显示进度。
7. 任务完成后生成结果摘要和报告。

## 5. 安全与约束

接口测试工具会直接影响真实硬件，首版必须把安全边界写进实现。

- 默认只读：资源探测、系统信息、总线枚举可以直接执行；写操作必须由用户点击确认。
- 参数校验：GPIO 编号、I2C 地址、CAN ID、串口参数、PWM 周期和占空比都必须后端校验。
- 超时保护：所有外设访问都要有超时，防止任务卡死。
- 串行化冲突资源：同一 GPIO line、同一 I2C 总线、同一 UART、同一 CAN 口不能被多个写任务同时占用。
- 明确危险操作：修改 `/boot/uEnv`、启停网络接口、设置 CAN 波特率、切换 overlay、长期输出高电平等操作必须带 `confirm=true` 和日志记录。
- 可恢复：任务失败要返回可读错误，不应让服务进程崩溃。
- 审计日志：记录谁在什么时间对哪个接口执行了什么动作，以及执行结果。

## 6. 首版交付边界

首版包含：

- Web 控制台基础页面。
- Board Agent 基础服务。
- 模拟模式。
- 系统信息和资源枚举。
- GPIO、I2C、UART/RS232/RS485、CAN、PWM、ADC 的基础操作设计和优先实现路径。
- 实时日志和任务状态。

当前 MVP 已实现：

- `GET /api/health`、`GET /api/system`、`GET /api/resources`。
- `POST /api/tasks`、`GET /api/tasks/{id}`。
- `WS /ws/events`。
- 静态 Web 控制台首页、资源展示、dry-run 任务提交和日志面板。
- `RK_BOX_MODE=mock` 模拟模式。
- 对非 dry-run 的真实写操作进行 `confirm=true` 校验。

首版暂不包含：

- 摄像头、屏幕、音频、USB 存储等复杂外设测试。
- Windows 原生安装包。
- 云端账号体系。
- 多测试盒集中管理。

## 7. 验收标准

文档阶段：

- `README.md`、`docs/DESIGN.md`、`AGENTS.md` 均存在。
- 默认架构、连接方式、首版范围在三个文档中保持一致。
- 官方资料链接可访问，关键板卡资源记录清楚。

实现阶段：

- 无板卡时可以运行 Web UI 和模拟 Board Agent。
- 有板卡时可以读取系统信息并列出 GPIO、I2C、UART、CAN 等资源。
- WebSocket 能实时显示测试任务日志。
- GPIO、CAN、UART 等写操作有后端参数校验、错误返回和日志记录。
- 修改系统状态的动作有显式确认和重启提示。

## 8. 参考资料

- [野火 LubanCat-RK356x 快速使用手册](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/index.html)
- [LubanCat-RK356x 40pin 引脚对照说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/40pin.html)
- [GPIO 控制说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/gpio/gpio.html)
- [I2C 通讯说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/i2c/i2c.html)
- [SPI 通信说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/spi/spi.html)
- [CAN 总线说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/can/can.html)
- [RS485 说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/rs485/rs485.html)
- [RS232 说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/rs232/rs232.html)

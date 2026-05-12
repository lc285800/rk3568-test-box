# RK3568 测试工具盒

本项目用于把鲁班猫 2 金手指 RK3568 板卡打造成一个嵌入式接口测试盒。目标用户不需要熟悉 Linux 命令行，只需要在电脑浏览器中打开图形化控制台，就能控制测试盒的 GPIO、I2C、UART、RS232、RS485、CAN、PWM、ADC 等外设，对其它板卡或外设模块做接口验证。

## 推荐架构

第一版采用 Web 控制台优先的方案：

- 上位机 UI：运行在浏览器中的网页控制台，MacBook 和 Windows 都可以直接使用。
- 板端服务：RK3568 板卡上运行 Board Agent，负责外设资源探测、权限控制、测试任务执行和日志采集。
- 通信方式：电脑和测试盒接入同一局域网，通过 HTTP API 下发配置和测试动作，通过 WebSocket 接收实时日志、总线监听结果、任务进度和设备状态。
- 后续扩展：如果需要交付 Windows 安装包，可以把同一套 Web 前端封装进 Tauri 或 Electron，不需要推翻第一版架构。

默认连接入口为：

```text
http://192.168.2.88:8080
```

实际部署时可以继续保留固定 IP，也可以增加 mDNS 域名或设备发现功能。

## 当前开发与实测环境

当前项目按“MacBook 开发与浏览器控制端 + 鲁班猫 2 金手指 RK3568 板卡端”的局域网环境推进：

| 角色 | 设备 | 用途 |
| --- | --- | --- |
| 开发/控制端 | MacBook | 编辑代码、运行本地 mock、用 Safari/Chrome 打开 Web 控制台、通过 SSH/SCP 操作板卡 |
| 测试盒端 | 鲁班猫 2 金手指 RK3568 | 运行 Board Agent，访问 GPIO/I2C/UART/CAN/PWM/ADC 等真实外设资源 |

默认网络和登录信息：

```text
板卡 IP: 192.168.2.88
Web 控制台: http://192.168.2.88:8080
SSH 用户: root
SSH 密码: root
板卡项目目录: /root/rk3568_finger_box
MacBook 项目目录: /Users/evanliu/Documents/rk3568_finger_box
```

从 MacBook 登录板卡：

```bash
ssh root@192.168.2.88
```

从 MacBook 上传单个文件到板卡，例如同步前端样式：

```bash
scp web/styles.css root@192.168.2.88:/root/rk3568_finger_box/web/styles.css
```

从 MacBook 远程执行板卡命令，例如确认服务和端口：

```bash
ssh root@192.168.2.88 "cd /root/rk3568_finger_box && ./scripts/run_board_agent.sh"
```

如果只需要在浏览器验证板端 Web 控制台，优先打开：

```text
http://192.168.2.88:8080
```

## 板卡现状

当前已通过局域网探测到板卡 `192.168.2.88`，资源摘要如下：

| 项目 | 当前结果 |
| --- | --- |
| 板卡 | 鲁班猫 2 金手指板卡，RK3568 |
| 系统 | Ubuntu 20.04.6 LTS |
| 内核 | Linux 4.19.232 |
| CPU | 4 核 Cortex-A55，aarch64 |
| 内存 | 约 3.8 GiB |
| 存储 | `mmcblk1p3` 挂载为 `/`，约 29.6 GiB |
| 网络 | `eth0` 为 `192.168.2.88/24`，`eth1`/`usb0` 当前未启用 |
| CAN | `can0`、`can1` 当前存在但为 DOWN |
| GPIO | `/dev/gpiochip0` 至 `/dev/gpiochip5` |
| I2C | `/dev/i2c-0`、`/dev/i2c-5`、`/dev/i2c-6` |
| UART | `/dev/ttyS3`、`/dev/ttyS7`、`/dev/ttyS9` |
| PWM | `/sys/class/pwm` 存在 |

板卡上已存在常用用户态工具：`python3`、`pip3`、`gcc`、`gpiodetect`、`gpioinfo`、`gpioset`、`gpioget`、`i2cdetect`、`i2cget`、`i2cset`、`candump`、`cansend`、`ip`、`stty`。

## 首版功能

首版聚焦基础接口测试，不把摄像头、屏幕、音频、USB 存储等复杂外设纳入核心范围。

计划覆盖：

- GPIO：输入读取、输出置位、边沿事件监听、引脚占用提示。
- I2C：总线扫描、寄存器读写、常见器件探测模板。
- UART/RS232/RS485：串口参数配置、收发数据、循环发送、日志保存。
- CAN：波特率配置、发送帧、接收监听、过滤器、错误统计。
- PWM：频率、占空比、启停控制。
- ADC/电压采样：通道读取、阈值判断、简单趋势显示。
- 测试任务：单项测试、批量执行、实时日志、结果报告。

## 快速使用设想

第一版完成后，小白用户的典型流程应是：

1. 给 RK3568 测试盒上电，并把电脑和测试盒接入同一局域网。
2. 在浏览器打开 `http://192.168.2.88`。
3. 在设备页确认板卡在线，查看 GPIO、I2C、UART、CAN 等资源。
4. 进入对应接口面板，选择端口或引脚，填写测试参数。
5. 点击执行测试，实时查看日志、状态和结果。
6. 导出或保存测试报告，作为被测板卡接口验证记录。

## 技术路线

推荐首版技术栈：

- Frontend：Web 控制台，可选 React/Vue/Svelte，重点是清晰的测试面板、实时日志和报告视图。
- Board Agent：Python + FastAPI，便于快速调用 Linux 外设工具和系统接口。
- API：REST 负责设备信息、配置和动作请求；WebSocket 负责实时日志、任务进度和总线监听。
- 外设访问：优先封装 `libgpiod`、`i2c-tools`、`can-utils`、串口库、`sysfs`/`/dev` 设备节点，不允许前端直接拼接 shell 命令。
- 运行模式：同时支持真实硬件模式和模拟模式。没有板卡时也能开发 UI 和测试基础流程。

快速上手见 [docs/QUICKSTART.md](docs/QUICKSTART.md)。更详细的系统设计见 [docs/DESIGN.md](docs/DESIGN.md)。当前执行进度和实测边界见 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。问题记录见 [docs/ISSUES.md](docs/ISSUES.md)。

## 当前 MVP

仓库已经包含第一版可运行骨架：

- `board_agent/`：FastAPI 板端服务，包含健康检查、系统信息、资源枚举、任务提交/查询和 WebSocket 事件流。
- `web/`：无需构建工具的静态 Web 控制台，可以展示设备资源、提交 dry-run 任务并显示实时日志。
- `tests/`：不依赖真实板卡的基础测试，覆盖模拟资源和危险写操作确认逻辑。

当前阶段是 GPIO 外设可测试，暂停等待用户实测。现在适合测试 UI、API、mock 模式、dry-run 任务，以及板卡真实模式下的 GPIO 信息、读取和持续高/低电平输出；还不适合直接控制真实 I2C/UART/CAN/PWM/ADC 外设。

项目后续按单个外设里程碑推进：GPIO 完成后暂停并交给用户测试，测试通过后再继续 I2C、UART、RS232/RS485、CAN、PWM、ADC，依次循环。详细流程记录在 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

实际测试时优先跟随 [docs/QUICKSTART.md](docs/QUICKSTART.md) 操作。后续每完成一个外设，都会把测试步骤追加到该文档。

本地开发运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
RK_BOX_MODE=mock python -m board_agent
```

然后在浏览器打开：

```text
http://127.0.0.1:8080
```

部署到板卡时可以使用真实探测模式：

```bash
pip install -r requirements.txt
RK_BOX_MODE=auto RK_BOX_HOST=0.0.0.0 RK_BOX_PORT=8080 python -m board_agent
```

电脑与测试盒在同一局域网时，访问：

```text
http://192.168.2.88:8080
```

运行测试：

```bash
pytest
```

## 重要资料

- [野火 LubanCat-RK356x 快速使用手册](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/index.html)
- [LubanCat-RK356x 40pin 引脚对照说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/40pin.html)
- [GPIO 控制说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/gpio/gpio.html)
- [I2C 通讯说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/i2c/i2c.html)
- [SPI 通信说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/40pin/spi/spi.html)
- [CAN 总线说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/can/can.html)
- [RS485 说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/rs485/rs485.html)
- [RS232 说明](https://doc.embedfire.com/linux/rk356x/quick_start/zh/latest/quick_start/rs232/rs232.html)

## 后续路线

1. 用户实测 GPIO，修复反馈问题。
2. 实现 I2C Adapter 并暂停实测。
3. 继续实现 UART、RS232/RS485、CAN、PWM、ADC。
4. 增加测试模板、批量测试流程、权限确认和安全保护。
5. 增加测试报告导出。
6. 如需交付给 Windows 用户，封装为 Tauri 或 Electron 桌面应用。

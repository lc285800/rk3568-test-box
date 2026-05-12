# 快速上手

本文档用于指导用户一步一步使用 RK3568 测试工具盒。后续每完成一个外设，都会把对应测试方法补充到这里。

当前可实测外设：GPIO。

当前暂不可实测外设：I2C、UART、RS232/RS485、CAN、PWM、ADC。

## 1. 准备环境

需要准备：

- 鲁班猫 2 金手指 RK3568 板卡。
- MacBook 或 Windows 电脑。
- 板卡和电脑接入同一局域网。
- 板卡 IP 当前默认为 `192.168.2.88`。
- SSH 账号密码当前均为 `root`。

先在电脑确认板卡网络可达：

```bash
ping 192.168.2.88
```

如果需要登录板卡：

```bash
ssh root@192.168.2.88
```

## 2. 部署到板卡

在电脑上把项目同步到板卡：

```bash
scp -r /Users/evanliu/Documents/rk3568_finger_box root@192.168.2.88:/root/
```

登录板卡：

```bash
ssh root@192.168.2.88
```

进入项目目录：

```bash
cd /root/rk3568_finger_box
```

安装 Python 依赖：

```bash
pip3 install -r requirements.txt
```

板卡当前是 Python 3.8.10，依赖文件已经包含 Python 3.8 兼容项：

```text
typing-extensions>=4.12.2
eval-type-backport>=0.2,<1.0
```

如果安装过程中曾出现 Pydantic 解析 `list[str]` 的错误，重新拉取最新代码或同步最新 `requirements.txt` 后，再执行一次安装命令。

启动 Board Agent：

```bash
./scripts/run_board_agent.sh
```

启动后保持这个终端不要关闭。看到类似下面的信息表示服务已启动：

```text
Uvicorn running on http://0.0.0.0:8080
```

也可以手动启动，但必须先进入项目根目录：

```bash
cd /root/rk3568_finger_box
RK_BOX_MODE=auto RK_BOX_HOST=0.0.0.0 RK_BOX_PORT=8080 python3 -m board_agent
```

如果在 `/root` 等其它目录直接执行 `python3 -m board_agent`，会提示找不到 `board_agent` 模块。

## 3. 打开 Web 控制台

在电脑浏览器打开：

```text
http://192.168.2.88:8080
```

进入页面后先确认：

- 顶部状态显示在线。
- 系统信息能正常显示。
- 外设资源里能看到 GPIO、I2C、串口、CAN 等资源。
- 实时日志面板能显示连接或刷新日志。

## 4. GPIO 快速测试

GPIO 当前支持：

- 信息：查看 `gpioinfo` 输出。
- 读取：读取指定 GPIO line 电平。
- 输出：持续输出高电平或低电平，再次输出同一 line 时会覆盖旧电平。

### 4.1 查看 GPIO 信息

1. 打开 Web 控制台中的“GPIO 测试”面板。
2. 芯片填入：

```text
/dev/gpiochip0
```

3. 保持 `Dry run` 勾选。
4. 点击“信息”。
5. 查看任务结果和实时日志。

如果看到类似 `gpiochip0 - 32 lines` 的输出，说明 GPIO 信息读取正常。

### 4.2 读取 GPIO 输入

1. 在 GPIO 测试面板中选择一个 line，例如：

```text
0
```

2. 保持 `Dry run` 勾选时先点“读取”，确认任务流程正常。
3. 如果要读真实 GPIO，取消 `Dry run`。
4. 点击“读取”。
5. 查看任务结果中的 `values`。

返回示例：

```json
{
  "chip": "/dev/gpiochip0",
  "values": {
    "0": 1
  },
  "simulated": false
}
```

### 4.3 输出 GPIO

真实 GPIO 输出前必须确认接线安全。

建议使用：

- LED + 限流电阻。
- 万用表。
- 已确认可安全输入的被测板卡 GPIO。

操作步骤：

1. 先点击“信息”，确认目标 line 没有显示 `[used]`。
2. 芯片填入：

```text
/dev/gpiochip0
```

3. Line 填入你要测试的空闲 line。
4. 取消 `Dry run`。
5. 勾选“确认写入”。
6. 点击“输出高”或“输出低”。
7. 观察 LED、万用表、逻辑分析仪或被测板卡输入状态。
8. 如需切换电平，直接点击另一个输出按钮。
9. 查看实时日志和任务结果。

注意：当前输出使用 `gpioset --mode=signal` 持续保持电平。该状态会保持到再次输出同一 line、服务重启或板卡重启。

## 5. GPIO 安全注意事项

- 不要对 `gpioinfo` 显示 `[used]` 的 line 做输出测试。
- 不要把 GPIO 直接接到 5V。
- 不要短接两个输出引脚。
- 不确定 40pin 对应关系时，只做“信息”和“读取”，先不要做“输出”。
- 如果接 LED，必须串联限流电阻。
- 如果页面报错，先保留错误信息，不要反复点击输出。

## 6. 常见问题

### 页面打不开

检查板卡服务是否运行：

```bash
ps aux | grep board_agent
```

检查端口是否监听：

```bash
ss -lntp | grep 8080
```

检查电脑是否能访问板卡：

```bash
ping 192.168.2.88
```

### GPIO 信息为空或报错

在板卡上手动确认工具是否存在：

```bash
command -v gpioinfo
command -v gpioget
command -v gpioset
```

手动查看 GPIO：

```bash
gpioinfo | head -80
```

### 输出后一直保持高电平或低电平

这是当前设计。GPIO 输出使用持续保持模式：

```bash
gpioset --mode=signal
```

如果需要改变电平，直接点击“输出低”或“输出高”。如果需要恢复系统默认状态，可以重启服务或重启板卡。

### 提示真实写操作需要确认

取消 `Dry run` 后，必须勾选“确认写入”。这是为了避免误操作真实外设。

## 7. 后续外设测试入口

以下外设完成后，会把步骤追加到本文档：

- I2C：总线扫描、寄存器读写。
- UART：串口参数配置、收发测试。
- RS232/RS485：收发测试、RS485 半双工方向控制。
- CAN：接口状态、发帧、监听。
- PWM：频率、占空比、启停。
- ADC：通道读取、电压换算。

## 8. 当前项目状态

当前状态以 [PROJECT_STATUS.md](PROJECT_STATUS.md) 为准。

当前阶段：

```text
GPIO 外设可测试，暂停等待用户实测
```

# iPhone 群控实战：一台电脑操控多台 iPhone 的完整方案

> 上一篇我们聊了单台 iPhone 的自动化操作，但当你需要同时操作 10 台、50 台甚至上百台 iPhone 时，单机方案就力不从心了。这篇文章将系统讲解 iPhone 群控的完整技术方案，从硬件选型到软件架构，从多设备 WDA 部署到并发调度框架，帮你搭建一套可落地的群控系统。

## 一、什么是群控？为什么需要群控？

群控，即一台控制端同时管理多台移动设备，实现批量操作、同步控制或差异化调度。

**典型应用场景：**

- **App 测试**：同时在多台不同型号 iPhone 上运行自动化测试
- **电商运营**：多店铺同步上架商品、批量回复消息
- **内容分发**：多账号同步发布内容到社交平台
- **设备管理**：企业批量配置、安装应用、推送策略
- **数据采集**：多设备并行采集公开数据

**群控 vs 单控的核心区别：**

| 维度 | 单控 | 群控 |
|------|------|------|
| 设备数量 | 1 台 | N 台（10~500+） |
| 连接方式 | 单根 USB / WiFi | USB Hub / 网络集群 |
| 端口管理 | 单端口 | 多端口映射 |
| 并发调度 | 无需 | 核心问题 |
| 状态监控 | 简单 | 需要仪表盘 |
| 容错处理 | 重试即可 | 需要设备级隔离 |

---

## 二、群控系统架构总览

一个完整的 iPhone 群控系统由四层组成：

```
┌─────────────────────────────────────────────┐
│              控制面板层 (Dashboard)            │
│    Web UI / 命令行  ·  任务管理  ·  状态监控     │
├─────────────────────────────────────────────┤
│              调度引擎层 (Scheduler)            │
│    任务队列  ·  并发调度  ·  设备分配  ·  重试    │
├─────────────────────────────────────────────┤
│              设备驱动层 (Device Driver)        │
│    WDA 实例管理  ·  端口映射  ·  连接保活        │
├─────────────────────────────────────────────┤
│              硬件连接层 (Hardware)             │
│    USB Hub  ·  数据线  ·  iPhone 设备          │
└─────────────────────────────────────────────┘
```

下面自底向上逐层拆解。

---

## 三、硬件层：多设备连接方案

### 3.1 USB Hub 选型

群控的第一道关卡是物理连接。普通家用 USB Hub 无法满足多台 iPhone 同时连接的需求，需要工业级方案。

**选型要点：**

| 参数 | 要求 | 说明 |
|------|------|------|
| 端口数 | 10~24 口 | 根据设备数量选择 |
| 供电 | 每口 ≥ 2.1A | iPhone 充电+数据传输需要足够电流 |
| 协议 | USB 2.0 即可 | WDA 通信数据量不大，USB 2.0 足够 |
| MTT | 支持 | 多事务转换器，多设备并发不抢占带宽 |
| 稳定性 | 7×24 小时 | 工业级散热和供电设计 |

**推荐方案：**

- **小规模（≤10 台）**：工业级 10 口 USB 2.0 Hub，带独立供电适配器（12V/5A 以上）
- **中规模（10~50 台）**：多台 10 口 Hub 级联，每台 Hub 独立供电
- **大规模（50+ 台）**：专用群控机柜，内置多口 Hub + 集中供电 + 散热系统

> ⚠️ 不要使用普通家用 Hub。家用 Hub 供电不足，连接 3~4 台 iPhone 后就会出现设备掉线、充电中断等问题。

### 3.2 数据线选择

- 必须使用 **支持数据传输** 的 Lightning/USB-C 线缆
- 建议统一线缆长度（1~1.5m），便于理线
- 线缆质量直接影响连接稳定性，不要用几块钱的山寨线

### 3.3 设备布局

```
┌──────────────────────────────┐
│         群控机架/桌面          │
│                              │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐  │
│  │📱│ │📱│ │📱│ │📱│ │📱│  │  ← iPhone 手机架
│  └──┘ └──┘ └──┘ └──┘ └──┘  │
│   │    │    │    │    │      │
│  ┌──────────────────────┐   │
│  │   10口 USB Hub       │   │  ← 工业级 Hub
│  └──────────────────────┘   │
│            │                 │
│        ┌───────┐            │
│        │  Mac  │            │  ← 控制主机
│        └───────┘            │
└──────────────────────────────┘
```

### 3.4 WiFi 方案（备选）

如果不想用 USB 连接，也可以通过 WiFi 控制：

1. 先用 USB 连接 iPhone，获取设备 IP
2. iPhone 和 Mac 连入同一 WiFi
3. WDA 监听 WiFi 端口，直接通过 IP 访问

**WiFi 方案的优缺点：**

| 优点 | 缺点 |
|------|------|
| 无需 Hub，布线简单 | 延迟高，操作卡顿 |
| 设备位置灵活 | 连接不稳定，容易断线 |
| 扩展方便 | 首次仍需 USB 部署 WDA |

> 建议：小规模测试可用 WiFi，生产环境优先 USB。

---

## 四、设备驱动层：多 WDA 实例管理

每台 iPhone 需要运行一个独立的 WebDriverAgent 实例，这是群控的核心技术难点。

### 4.1 核心原理

```
Mac 电脑
├── iproxy 8100 8100 --udid AAAA   →  iPhone A (WDA 端口 8100)
├── iproxy 8200 8100 --udid BBBB   →  iPhone B (WDA 端口 8100)
├── iproxy 8300 8100 --udid CCCC   →  iPhone C (WDA 端口 8100)
└── iproxy 8400 8100 --udid DDDD   →  iPhone D (WDA 端口 8100)
```

关键点：
- 每台 iPhone 上 WDA 都监听 **8100 端口**（设备内部端口相同）
- 通过 `iproxy -u UDID` 将不同设备映射到 Mac 的 **不同本地端口**
- Python 代码通过不同本地端口连接不同设备

### 4.2 获取设备 UDID

```bash
# 方法一：通过 idevice_id
idevice_id -l

# 方法二：通过 system_profiler
system_profiler SPUSBDataType | grep "Serial Number" | sed 's/.*: //'

# 方法三：通过 xcrun
xcrun xctrace list devices
```

### 4.3 批量部署 WDA

**方式一：命令行逐台部署**

```bash
# 获取所有设备 UDID
UDIDS=$(idevice_id -l)

# 本地端口从 8100 开始递增
PORT=8100

for UDID in $UDIDS; do
    echo "部署 WDA 到设备 $UDID，本地端口 $PORT"

    xcodebuild -project WebDriverAgent.xcodeproj \
        -scheme WebDriverAgentRunner \
        -destination "id=$UDID" \
        USE_PORT=$PORT \
        test &

    PORT=$((PORT + 100))
done

wait
echo "所有设备 WDA 部署完成"
```

**方式二：使用 go-ios 跨平台部署**

```bash
# go-ios 可以在 Windows/Linux 上运行
for UDID in $(go-ios list | jq -r '.[].UDID'); do
    go-ios runwda --bundleid com.yourname.WebDriverAgentRunner --udid $UDID
done
```

### 4.4 批量端口映射

```bash
#!/bin/bash

DEVICES=$(idevice_id -l)
PORT=8100

for UDID in $DEVICES; do
    echo "映射设备 $UDID → 本地端口 $PORT"
    iproxy $PORT 8100 -u $UDID &
    PORT=$((PORT + 100))
done

echo "所有端口映射完成"
echo "设备列表："
echo "  iPhone-A → http://localhost:8100"
echo "  iPhone-B → http://localhost:8200"
echo "  iPhone-C → http://localhost:8300"
echo "  ..."
```

### 4.5 验证所有设备连接

```bash
#!/bin/bash

PORT=8100
DEVICE_COUNT=$(idevice_id -l | wc -l)

echo "检测 $DEVICE_COUNT 台设备的 WDA 连接状态..."
echo "----------------------------------------"

for i in $(seq 1 $DEVICE_COUNT); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/status)
    if [ "$STATUS" = "200" ]; then
        echo "✅ 端口 $PORT - 设备在线"
    else
        echo "❌ 端口 $PORT - 设备离线"
    fi
    PORT=$((PORT + 100))
done
```

### 4.6 WDA 保活

WDA 在长时间运行后可能崩溃，需要保活机制：

```bash
#!/bin/bash

keep_wda_alive() {
    local PORT=$1
    local UDID=$2

    while true; do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/status)
        if [ "$STATUS" != "200" ]; then
            echo "[$(date)] 设备 $UDID WDA 离线，正在重启..."
            xcodebuild -project WebDriverAgent.xcodeproj \
                -scheme WebDriverAgentRunner \
                -destination "id=$UDID" \
                test > /dev/null 2>&1 &
        fi
        sleep 30
    done
}

DEVICES=$(idevice_id -l)
PORT=8100

for UDID in $DEVICES; do
    keep_wda_alive $PORT $UDID &
    PORT=$((PORT + 100))
done
```

---

## 五、调度引擎层：并发控制框架

有了多设备连接，接下来需要一个调度引擎来管理任务的并发执行。

### 5.1 设备注册表

首先，用一个数据结构管理所有设备：

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import wda


class DeviceStatus(Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class Device:
    udid: str
    name: str
    local_port: int
    status: DeviceStatus = DeviceStatus.OFFLINE
    client: Optional[wda.Client] = None
    current_task: Optional[str] = None

    @property
    def wda_url(self) -> str:
        return f"http://localhost:{self.local_port}"

    def connect(self) -> bool:
        try:
            self.client = wda.Client(self.wda_url)
            self.client.status()
            self.status = DeviceStatus.ONLINE
            return True
        except Exception as e:
            print(f"设备 {self.name} 连接失败: {e}")
            self.status = DeviceStatus.OFFLINE
            return False


class DeviceRegistry:
    def __init__(self):
        self.devices: dict[str, Device] = {}

    def register(self, udid: str, name: str, local_port: int):
        device = Device(udid=udid, name=name, local_port=local_port)
        self.devices[udid] = device

    def get_available(self) -> list[Device]:
        return [
            d for d in self.devices.values()
            if d.status == DeviceStatus.ONLINE
        ]

    def get_by_name(self, name: str) -> Optional[Device]:
        for d in self.devices.values():
            if d.name == name:
                return d
        return None

    def health_check(self):
        for device in self.devices.values():
            try:
                if device.client:
                    device.client.status()
                    if device.status == DeviceStatus.OFFLINE:
                        device.status = DeviceStatus.ONLINE
                else:
                    device.connect()
            except Exception:
                device.status = DeviceStatus.OFFLINE
```

### 5.2 任务调度器

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Scheduler")


@dataclass
class Task:
    task_id: str
    action: Callable
    target_devices: list[str] | None = None
    retry_count: int = 3
    timeout: int = 300


class TaskScheduler:
    def __init__(self, registry: DeviceRegistry, max_workers: int = 10):
        self.registry = registry
        self.max_workers = max_workers
        self.task_results: dict[str, dict] = {}

    def _execute_on_device(self, task: Task, device: Device) -> dict:
        result = {
            "task_id": task.task_id,
            "device": device.name,
            "status": "failed",
            "error": None,
            "duration": 0,
        }

        for attempt in range(1, task.retry_count + 1):
            try:
                device.status = DeviceStatus.BUSY
                device.current_task = task.task_id
                start = time.time()

                task.action(device)

                result["status"] = "success"
                result["duration"] = round(time.time() - start, 2)
                break

            except Exception as e:
                result["error"] = str(e)
                logger.warning(
                    f"任务 {task.task_id} 在 {device.name} 上第 {attempt} 次失败: {e}"
                )
                if attempt < task.retry_count:
                    time.sleep(2)
                    device.connect()

            finally:
                device.status = DeviceStatus.ONLINE
                device.current_task = None

        return result

    def run_broadcast(self, task: Task) -> list[dict]:
        if task.target_devices:
            devices = [
                d for d in self.registry.get_available()
                if d.name in task.target_devices
            ]
        else:
            devices = self.registry.get_available()

        if not devices:
            logger.error("没有可用设备")
            return []

        logger.info(f"广播任务 {task.task_id} 到 {len(devices)} 台设备")

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._execute_on_device, task, device): device
                for device in devices
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                status_icon = "✅" if result["status"] == "success" else "❌"
                logger.info(
                    f"{status_icon} {result['device']}: "
                    f"{result['status']} ({result['duration']}s)"
                )

        self.task_results[task.task_id] = results
        return results

    def run_sequential(self, task: Task) -> list[dict]:
        if task.target_devices:
            devices = [
                d for d in self.registry.get_available()
                if d.name in task.target_devices
            ]
        else:
            devices = self.registry.get_available()

        results = []
        for i, device in enumerate(devices):
            logger.info(f"[{i+1}/{len(devices)}] 在 {device.name} 上执行任务")
            result = self._execute_on_device(task, device)
            results.append(result)

        return results
```

### 5.3 使用示例

```python
registry = DeviceRegistry()

registry.register("aaaa1111", "iPhone-A", 8100)
registry.register("bbbb2222", "iPhone-B", 8200)
registry.register("cccc3333", "iPhone-C", 8300)
registry.register("dddd4444", "iPhone-D", 8400)

for device in registry.devices.values():
    device.connect()

scheduler = TaskScheduler(registry, max_workers=4)


def open_wechat(device: Device):
    device.client.app_launch("com.tencent.xin")
    time.sleep(2)
    device.client.screenshot(f"screenshot_{device.name}.png")


task = Task(
    task_id="open_wechat_001",
    action=open_wechat,
)

results = scheduler.run_broadcast(task)

success = sum(1 for r in results if r["status"] == "success")
print(f"\n执行完成: {success}/{len(results)} 成功")
```

---

## 六、群控实战案例

### 6.1 案例：多设备批量截图

```python
def batch_screenshot(device: Device):
    device.client.screenshot(f"screenshots/{device.name}_{int(time.time())}.png")


task = Task(task_id="screenshot_all", action=batch_screenshot)
scheduler.run_broadcast(task)
```

### 6.2 案例：多设备批量安装 App

```python
import subprocess


def batch_install_app(device: Device):
    subprocess.run(
        ["ideviceinstaller", "-u", device.udid, "-i", "app.ipa"],
        check=True,
    )


task = Task(task_id="install_app", action=batch_install_app)
scheduler.run_broadcast(task)
```

### 6.3 案例：多设备同步操作（同屏控制）

同屏控制要求所有设备**同时执行相同操作**，模拟一个人同时操作多台手机：

```python
import threading
import time


class SyncController:
    def __init__(self, registry: DeviceRegistry):
        self.registry = registry
        self.barrier = None

    def _sync_action(self, device: Device, actions: list, step_index: int):
        self.barrier.wait()
        action = actions[step_index]
        action(device)

    def execute_sync(self, actions: list[Callable]):
        devices = self.registry.get_available()
        total_steps = len(actions)

        for step in range(total_steps):
            self.barrier = threading.Barrier(len(devices))
            threads = []

            for device in devices:
                t = threading.Thread(
                    target=self._sync_action,
                    args=(device, actions, step),
                )
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            time.sleep(0.5)


sync = SyncController(registry)

actions = [
    lambda d: d.client.home(),
    lambda d: d.client.click(200, 400),
    lambda d: d.client.swipe(200, 800, 200, 200),
    lambda d: d.client.click(350, 600),
]

sync.execute_sync(actions)
```

### 6.4 案例：分组差异化操作

不同组设备执行不同任务：

```python
def group_a_task(device: Device):
    device.client.app_launch("com.tencent.xin")
    time.sleep(2)


def group_b_task(device: Device):
    device.client.app_launch("com.ss.iphone.ugc.Aweme")
    time.sleep(2)


task_a = Task(
    task_id="group_a_wechat",
    action=group_a_task,
    target_devices=["iPhone-A", "iPhone-B"],
)

task_b = Task(
    task_id="group_b_douyin",
    action=group_b_task,
    target_devices=["iPhone-C", "iPhone-D"],
)

results_a = scheduler.run_broadcast(task_a)
results_b = scheduler.run_broadcast(task_b)
```

---

## 七、企业级方案：MDM 群控

如果你的需求是**设备管理**而非 UI 操作（安装应用、推送配置、远程锁定等），MDM（移动设备管理）是更合适的方案。

### 7.1 MDM 工作原理

```
MDM 服务器 ──(APNs 推送)──→ iPhone 上的 MDM 配置文件 ──→ 执行管理命令
```

MDM 基于 Apple 官方的 Mobile Device Management 协议，通过 APNs（Apple Push Notification service）向设备推送管理指令。

### 7.2 主流 MDM 方案对比

| 方案 | 类型 | 适用规模 | 价格 |
|------|------|----------|------|
| Jamf Pro | 商业 | 中大型企业 | 付费（按设备数） |
| SimpleMDM | 商业 | 中小企业 | 付费 |
| Microsoft Intune | 商业 | 企业（已有 M365） | 含在 M365 中 |
| MicroMDM | 开源 | 技术团队 | 免费 |
| 鹰眼中控 | 商业 | 工作室/企业 | 付费 |

### 7.3 MDM 能做什么

- ✅ 批量安装/卸载 App
- ✅ 推送 WiFi、VPN、邮箱等配置
- ✅ 远程锁定/擦除设备
- ✅ 限制设备功能（相机、App Store 等）
- ✅ 批量推送系统更新
- ✅ 收集设备硬件/软件信息
- ❌ **不能**模拟 UI 操作（点击、滑动等）

### 7.4 MDM + WDA 混合方案

实际生产中，往往需要 MDM 和 WDA 配合使用：

```
MDM 负责：设备初始化、应用安装、配置推送、设备监控
WDA 负责：UI 自动化操作、业务流程执行
```

**典型工作流：**

1. MDM 批量注册设备，推送基础配置
2. MDM 批量安装 WebDriverAgent 和业务 App
3. WDA 接管，执行 UI 自动化任务
4. MDM 持续监控设备状态，异常时远程处理

---

## 八、AI 驱动的群控方案

将 AI Agent 与群控结合，可以实现「一句话控制所有设备」。

### 8.1 架构设计

```
自然语言指令
    │
    ▼
┌──────────────┐
│  AI 调度中心   │  ← 理解指令，拆解为多设备任务
└──────┬───────┘
       │
       ├──→ Device-A: Open-AutoGLM Agent
       ├──→ Device-B: Open-AutoGLM Agent
       ├──→ Device-C: Open-AutoGLM Agent
       └──→ Device-D: Open-AutoGLM Agent
```

### 8.2 实现思路

```python
import asyncio
import wda


class AIGroupController:
    def __init__(self, registry: DeviceRegistry, model_api: str):
        self.registry = registry
        self.model_api = model_api

    async def _agent_loop(self, device: Device, instruction: str):
        client = device.client
        step = 0
        max_steps = 20

        while step < max_steps:
            screenshot_path = f"/tmp/agent_{device.name}_{step}.png"
            client.screenshot(screenshot_path)

            action = await self._ask_model(screenshot_path, instruction)

            if action["type"] == "done":
                return {"device": device.name, "status": "success"}

            self._execute_action(client, action)
            step += 1

        return {"device": device.name, "status": "max_steps_reached"}

    async def _ask_model(self, screenshot_path: str, instruction: str) -> dict:
        pass

    def _execute_action(self, client: wda.Client, action: dict):
        atype = action["type"]
        if atype == "click":
            client.click(action["x"], action["y"])
        elif atype == "swipe":
            client.swipe(
                action["startX"], action["startY"],
                action["endX"], action["endY"],
            )
        elif atype == "input":
            client.set_text(action["text"])
        elif atype == "home":
            client.home()

    async def execute(self, instruction: str):
        devices = self.registry.get_available()
        tasks = [
            self._agent_loop(device, instruction)
            for device in devices
        ]
        results = await asyncio.gather(*tasks)
        return results


async def main():
    controller = AIGroupController(registry, "https://your-model-api")
    results = await controller.execute("打开微信发一条朋友圈")
    for r in results:
        print(f"{r['device']}: {r['status']}")


asyncio.run(main())
```

---

## 九、监控面板

群控系统需要一个可视化面板来监控设备状态和任务进度。

### 9.1 轻量方案：命令行仪表盘

```python
import time


def render_dashboard(registry: DeviceRegistry):
    while True:
        devices = list(registry.devices.values())

        print("\033[2J\033[H")
        print("=" * 60)
        print("         iPhone 群控监控面板")
        print("=" * 60)
        print(f"{'设备名':<12} {'状态':<10} {'端口':<8} {'当前任务':<20}")
        print("-" * 60)

        online = busy = offline = 0
        for d in devices:
            status_map = {
                DeviceStatus.ONLINE: ("🟢 在线", "online"),
                DeviceStatus.BUSY: ("🟡 忙碌", "busy"),
                DeviceStatus.OFFLINE: ("🔴 离线", "offline"),
            }
            status_text, status_key = status_map[d.status]
            task_text = d.current_task or "-"
            print(f"{d.name:<12} {status_text:<10} {d.local_port:<8} {task_text:<20}")

            if status_key == "online":
                online += 1
            elif status_key == "busy":
                busy += 1
            else:
                offline += 1

        print("-" * 60)
        print(f"总计: {len(devices)} 台 | 在线: {online} | 忙碌: {busy} | 离线: {offline}")
        print(f"刷新时间: {time.strftime('%H:%M:%S')}")

        time.sleep(5)
```

### 9.2 Web 方案：Flask + WebSocket

```python
from flask import Flask, jsonify, render_template_string
from flask_socketio import SocketIO
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

registry = None


@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>iPhone 群控面板</title></head>
    <body>
        <h1>iPhone 群控监控面板</h1>
        <div id="devices"></div>
        <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
        <script>
            const socket = io();
            socket.on('update', function(data) {
                let html = '<table border="1" cellpadding="8"><tr>'
                    + '<th>设备</th><th>状态</th><th>端口</th><th>任务</th></tr>';
                data.forEach(d => {
                    const color = d.status === 'online' ? 'green'
                        : d.status === 'busy' ? 'orange' : 'red';
                    html += '<tr>'
                        + '<td>' + d.name + '</td>'
                        + '<td style="color:' + color + '">' + d.status + '</td>'
                        + '<td>' + d.port + '</td>'
                        + '<td>' + (d.task || '-') + '</td></tr>';
                });
                html += '</table>';
                document.getElementById('devices').innerHTML = html;
            });
        </script>
    </body>
    </html>
    """)


@app.route("/api/devices")
def api_devices():
    return jsonify([
        {
            "name": d.name,
            "udid": d.udid,
            "status": d.status.value,
            "port": d.local_port,
            "task": d.current_task,
        }
        for d in registry.devices.values()
    ])


def background_push():
    while True:
        socketio.emit("update", [
            {
                "name": d.name,
                "status": d.status.value,
                "port": d.local_port,
                "task": d.current_task,
            }
            for d in registry.devices.values()
        ])
        import time
        time.sleep(3)


if __name__ == "__main__":
    threading.Thread(target=background_push, daemon=True).start()
    socketio.run(app, port=5000)
```

---

## 十、完整启动脚本

将所有步骤整合为一个一键启动脚本：

```bash
#!/bin/bash

set -e

echo "======================================"
echo "    iPhone 群控系统 - 一键启动"
echo "======================================"

DEVICES=$(idevice_id -l)
DEVICE_COUNT=$(echo "$DEVICES" | wc -l | tr -d ' ')

if [ "$DEVICE_COUNT" -eq 0 ]; then
    echo "❌ 未检测到连接的 iPhone 设备"
    exit 1
fi

echo "📱 检测到 $DEVICE_COUNT 台设备"

PORT=8100
PIDS=()

for UDID in $DEVICES; do
    echo "  → 设备 $UDID → 本地端口 $PORT"

    iproxy $PORT 8100 -u $UDID > /dev/null 2>&1 &
    PIDS+=($!)

    PORT=$((PORT + 100))
done

echo ""
echo "等待端口映射就绪..."
sleep 3

PORT=8100
ONLINE=0
OFFLINE=0

for UDID in $DEVICES; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/status 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "  ✅ 端口 $PORT - 在线"
        ONLINE=$((ONLINE + 1))
    else
        echo "  ❌ 端口 $PORT - 离线（需先部署 WDA）"
        OFFLINE=$((OFFLINE + 1))
    fi
    PORT=$((PORT + 100))
done

echo ""
echo "======================================"
echo "  在线: $ONLINE | 离线: $OFFLINE"
echo "  端口范围: 8100 - $((8100 + (DEVICE_COUNT - 1) * 100))"
echo "======================================"

if [ "$OFFLINE" -gt 0 ]; then
    echo ""
    echo "⚠️  有设备离线，请确保："
    echo "  1. WDA 已部署到对应设备"
    echo "  2. iPhone 已信任开发者证书"
    echo "  3. 数据线支持数据传输"
fi

echo ""
echo "按 Ctrl+C 停止所有端口映射..."

trap "echo '正在停止...'; kill ${PIDS[@]} 2>/dev/null; exit 0" SIGINT SIGTERM

wait
```

---

## 十一、性能优化与扩展

### 11.1 单机性能上限

一台 Mac 能同时控制多少台 iPhone？取决于以下因素：

| 因素 | 影响 | 建议 |
|------|------|------|
| USB 带宽 | USB 2.0 理论 480Mbps，10 台设备共享 | WDA 通信量小，10~20 台无压力 |
| CPU | 每个线程处理一个设备 | M1/M2 Mac 建议 ≤30 台并发 |
| 内存 | 每个 WDA 连接约 10~20MB | 16GB 内存可支撑 50+ 连接 |
| iproxy 进程 | 每设备一个进程 | 注意进程数限制 |

**经验值：** 一台 M1 Mac 稳定控制 **20~30 台** iPhone。

### 11.2 多机集群扩展

超过 30 台设备时，需要多台 Mac 组成集群：

```
┌─────────────┐
│  主控服务器   │  ← 任务调度、Web 面板
└──────┬───────┘
       │
       ├──→ Mac Worker 1 (20 台 iPhone)
       ├──→ Mac Worker 2 (20 台 iPhone)
       └──→ Mac Worker 3 (20 台 iPhone)
```

每台 Mac 作为 Worker 节点，运行 WDA 和 iproxy；主控服务器通过 HTTP API 分发任务。

### 11.3 关键优化点

- **连接池**：复用 WDA 连接，避免频繁创建/销毁
- **异步 I/O**：使用 asyncio 替代线程池，减少上下文切换
- **操作去重**：相同操作只截图一次，广播给所有设备
- **智能调度**：根据设备型号、iOS 版本分配不同任务
- **结果缓存**：相同操作的结果缓存，避免重复执行

---

## 十二、安全与合规

群控场景下，安全合规问题更加突出：

1. **Apple 开发者协议**：免费账号 7 天签名限制，大规模群控建议使用企业开发者账号（$299/年）
2. **设备合规**：确保所有设备为合法持有，避免使用黑产设备
3. **数据安全**：群控系统集中管理大量设备数据，需做好加密和访问控制
4. **App 合规**：部分 App 明确禁止自动化操作和群控行为
5. **法律风险**：群控用于灰黑产（刷量、养号等）可能触犯法律

> ⚠️ 本文所有技术方案仅供合法合规用途，请勿用于任何违法违规场景。

---

## 十三、方案选择速查

```
你的群控需求是什么？
│
├─ 只需管理设备（安装App、推送配置）
│  └─ ✅ MDM 方案（Jamf / MicroMDM）
│
├─ 需要 UI 自动化操作（点击、输入、滑动）
│  ├─ ≤10 台设备
│  │  └─ ✅ 单 Mac + 多 WDA + ThreadPoolExecutor
│  ├─ 10~30 台设备
│  │  └─ ✅ 单 Mac + 工业Hub + 调度框架 + 监控面板
│  └─ 30+ 台设备
│     └─ ✅ 多 Mac 集群 + 分布式调度
│
├─ 需要用自然语言控制多台设备
│  └─ ✅ AI 群控方案（Open-AutoGLM × N）
│
└─ 没有 Mac 电脑
   └─ ✅ go-ios + Windows/Linux
```

---

## 十四、总结

iPhone 群控是一个从硬件到软件、从单机到集群的系统工程。核心要点回顾：

| 层级 | 关键技术 | 核心挑战 |
|------|----------|----------|
| 硬件层 | 工业级 USB Hub | 供电和带宽 |
| 驱动层 | 多 WDA 实例 + iproxy | 端口映射和保活 |
| 调度层 | ThreadPoolExecutor / asyncio | 并发控制和容错 |
| 应用层 | 任务编排 + 监控面板 | 可视化和运维 |
| 企业层 | MDM + WDA 混合 | 合规和规模 |

从单台到多台，核心变化是**并发调度**和**状态管理**。掌握了这两点，群控就是单控的自然扩展。

---

## 参考资源

- [iPhone 自动化操作完全手册](./iphone-automation-guide.md) — 本系列上篇
- [WebDriverAgent - GitHub](https://github.com/appium/WebDriverAgent)
- [facebook-wda - GitHub](https://github.com/openatx/facebook-wda)
- [go-ios - GitHub](https://github.com/danielpaulus/go-ios) — 跨平台 iOS 设备管理
- [pymobiledevice3 - GitHub](https://github.com/doronz88/pymobiledevice3)
- [MicroMDM - GitHub](https://github.com/micromdm/micromdm) — 开源 MDM
- [Jamf Pro](https://www.jamf.com/) — 商业 Apple MDM
- [Open-AutoGLM - GitHub](https://github.com/zai-org/Open-AutoGLM) — AI Phone Agent

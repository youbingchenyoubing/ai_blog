# run_kali.bat 图形化可行性分析

> 参考 https://ctf-wiki.org/pwn/linux/user-mode/environment/ 中"将 Docker 容器接入本地图形界面"一节，分析当前 run_kali.bat 启动的 Kali 容器开启图形界面（GUI 工具、gdb.attach 弹窗等）的可行性，并给出改造方案。原 run_kali.bat 不动，本文仅作分析与方案备份。

---

## 一、当前 run_kali.bat 现状

文件内容（保持原样，未做任何修改）：

```bat
docker run --privileged -dit --name kali -v D:\docker_env\kali:/root kalilinux/kali-rolling /bin/bash
```

参数解读：

| 参数 | 含义 | 与图形化的关系 |
|------|------|----------------|
| `--privileged` | 特权模式，容器获得近乎所有宿主能力 | 对图形化非必需但无害，反而便于访问 /tmp/.X11-unix、设备等 |
| `-d` | 后台运行 | 与图形化无关 |
| `-i` `-t` | 保留 stdin 与分配 tty | 与图形化无关 |
| `--name kali` | 容器名 | 无关 |
| `-v D:\docker_env\kali:/root` | 宿主目录挂载到容器 /root | 用于持久化数据/配置，与图形化无关，但便于保存工具配置 |
| `kalilinux/kali-rolling` | Kali 滚动版最小镜像 | 镜像本身不含 GUI 工具，需自行 apt 安装（burpsuite、firefox-esr、wireshark、ghidra 等） |
| `/bin/bash` | 容器入口 | 容器靠 bash 常驻，进入需用 docker exec |

关键缺失要素（导致 GUI 起不来的根因）：

1. 未设置 `DISPLAY` 环境变量——容器内 X 客户端不知道往哪里画窗口。
2. 未挂载 X11 socket `/tmp/.X11-unix`——容器无法走 Unix domain socket 连接宿主 X Server。
3. 未挂载 Wayland socket（如使用 Wayland）——同上。
4. Windows 宿主本身没有原生 X Server，需要额外安装 VcXsrv/Xming，或走 WSL2 + WSLg。

---

## 二、ctf-wiki 的图形化方案要点

ctf-wiki 给出的核心思路是：把宿主的图形服务暴露给容器，让容器内 GUI 程序直接在宿主屏幕上原生弹出窗口（而不是 VNC 远程桌面）。

### 1. For Wayland

```bash
docker run \
    -d \
    -p "25000:22" \
    --name=pwn24 \
    -v ~/Desktop/CTF:/CTF \
    -e XDG_RUNTIME_DIR=/tmp \
    -e DISPLAY=$DISPLAY \
    -e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
    -v $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:/tmp/$WAYLAND_DISPLAY \
    -e QT_QPA_PLATFORM=wayland \
    pwnenv_ubuntu24
```

关键点：把宿主的 Wayland socket 文件挂到容器 /tmp 下，并通过环境变量告诉 Qt 等程序走 Wayland。

### 2. For X11

```bash
docker run \
    -d \
    -p "25000:22" \
    --name=pwn24 \
    -v ~/Desktop/CTF:/CTF \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=$DISPLAY \
    pwnenv_ubuntu24
```

关键点：挂载 X11 Unix domain socket，DISPLAY 直接复用宿主值。

### 3. 配合 pwntools

ctf-wiki 还指出：pwntools 的 `gdb.attach()` 会创建新窗口，容器内直接运行会失败，必须接入本地图形服务。运行前需配置：

```python
context.terminal = ['konsole', '-e', 'sh', '-c']        # for KDE
context.terminal = ['gnome-terminal', '-e', 'sh', '-c']  # for Gnome
```

也可改用 tmux 多窗口绕开图形化需求：

```python
context.terminal = ['tmux', 'splitw', '-h']
```

---

## 三、可行性结论

可行。当前 `--privileged` 与挂载 `/root` 都不阻碍图形化，只需补齐 DISPLAY 与 X11/Wayland socket 挂载，并在宿主侧准备 X Server。Windows 宿主有两条主流路径：

| 方案 | 适用宿主 | 复杂度 | 体验 |
|------|----------|--------|------|
| A. VcXsrv + TCP（host.docker.internal） | Windows 原生 Docker Desktop | 中 | 原生弹出窗口 |
| B. WSL2 + WSLg（Wayland/X11 自动透传） | Windows 11 + WSL2 | 低 | 原生弹出窗口，最省心 |
| C. tmux 多窗口绕开图形化 | 任意 | 低 | 不弹窗，pwntools 在 tmux 里分屏 |

注：Windows 原生 Docker 没有 `/tmp/.X11-unix`，方案 A 必须走 TCP（host.docker.internal:0），不能照搬 Linux 宿主的 socket 挂载写法。

---

## 四、改造方案

下面给出三套改造示例，仅作参考。原 run_kali.bat 保持不变，用户可另存为新文件使用。

### 方案 A：Windows + VcXsrv（TCP 模式）

前置：在 Windows 安装 VcXsrv，启动 XLaunch，选择 Multiple windows、Display number 0，勾选 Disable access control，并在防火墙允许 VcXsrv 通过。

新文件示例 run_kali_gui.bat：

```bat
docker run --privileged -dit --name kali ^
  -v D:\docker_env\kali:/root ^
  -e DISPLAY=host.docker.internal:0 ^
  kalilinux/kali-rolling /bin/bash
```

注意：Windows 原生 Docker 没有 /tmp/.X11-unix，所以走 TCP，DISPLAY 必须是 host.docker.internal:0，不能用 :0。host.docker.internal 是 Docker Desktop 提供的指向宿主的特殊主机名。

进入容器后验证：

```bash
apt update && apt install -y x11-apps
xeyes    # 应在 Windows 桌面弹出眼睛窗口
```

### 方案 B：WSL2 + WSLg（推荐，Windows 11）

前置：Windows 11 + WSL2 + WSLg（默认随 WSL2 安装）。在 WSL2 内运行 docker，DISPLAY 与 WAYLAND_DISPLAY 由 WSLg 自动注入。

新文件示例 run_kali_wslg.sh：

```bash
docker run --privileged -dit --name kali \
  -v /mnt/d/docker_env/kali:/root \
  -e DISPLAY=$DISPLAY \
  -e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
  -e XDG_RUNTIME_DIR=/tmp \
  -v $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:/tmp/$WAYLAND_DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  kalilinux/kali-rolling /bin/bash
```

WSLg 同时提供 X11 和 Wayland，可两套都挂上，让程序自选。

### 方案 C：tmux 绕开图形化（最低成本）

不改 docker run，进入容器后用 tmux 分屏跑 gdb.attach：

```bash
apt install -y tmux gdb
tmux
# 在 python 脚本中
python3 -c "from pwn import *; context.terminal = ['tmux', 'splitw', '-h']; gdb.attach(process('./pwn'))"
```

适合 pwntools 调试场景，但对 Burp Suite、Wireshark GUI、Firefox 等 GUI 工具无效。

---

## 五、镜像侧需补的工具

kalilinux/kali-rolling 是最小镜像，无论选哪个方案，图形化跑起来后还要装 GUI 工具本身：

```bash
apt update && apt install -y \
  kali-desktop-xfce \      # 可选：完整桌面（若走 VNC）
  firefox-esr \            # 浏览器
  burpsuite \              # Web 渗透
  wireshark \              # 流量分析（命令行可用 tshark 替代）
  ghidra \                 # 逆向
  x11-apps \               # xeyes 等测试小程序
  dbus-x11                 # 部分 GUI 程序依赖
```

若只想要 pwntools 弹窗，装最小集即可：

```bash
apt install -y gdb python3-pip x11-apps
pip3 install pwntools
# 容器内还需要终端模拟器才能弹窗
apt install -y xterm
# 在 python 脚本中
context.terminal = ['xterm', '-e']
```

ctf-wiki 的示例用 konsole（KDE）或 gnome-terminal（Gnome），但 Kali 容器内通常没装这两个，建议直接用 xterm，体积小、依赖少。

---

## 六、验证步骤

按方案 A 为例的完整验证流程：

1. 启动 VcXsrv（XLaunch），勾选 Disable access control。
2. 用改造后的 run_kali_gui.bat 启动容器。
3. 进入容器：`docker exec -it kali bash`。
4. 安装测试小程序：`apt update && apt install -y x11-apps`。
5. 运行 `xeyes`，Windows 桌面应弹出一双跟随鼠标的眼睛。
6. 若 xeyes 成功，burpsuite、firefox、wireshark 等 GUI 工具同理可用。
7. 若失败，按以下顺序排查：
   - 容器内 `echo $DISPLAY` 是否为 host.docker.internal:0。
   - Windows 防火墙是否放行 VcXsrv（专用网络与公用网络都勾上）。
   - VcXsrv 是否勾选 Disable access control（等同 xhost +，允许任意客户端连接）。
   - 用 `docker logs kali` 查看容器是否因 DISPLAY 异常退出。

---

## 七、风险与注意事项

1. `--privileged` + X11 转发等于把宿主 X Server 完全暴露给容器，任何能连到 host.docker.internal:0 的进程都能操作你的桌面。仅适合本机学习/做题场景，不要在生产环境这么做。
2. Kali 镜像默认 root，挂载 /root 到 D:\docker_env\kali 意味着宿主该目录下文件被容器完全掌控，注意别把敏感文件放进去。
3. kalilinux/kali-rolling 滚动更新，某次 apt upgrade 后 GUI 工具可能依赖变动，建议 commit 成自定义镜像固化版本。
4. 原则上图形化方案与现有 `--privileged -dit` 兼容，只新增 -e 与 -v 参数，不破坏原有持久化与运行模式。

---

## 八、与项目其他文档的关系

- [Docker部署Kali无界面使用指南.md](../../Docker部署Kali无界面使用指南.md) — 无界面（headless）场景的总览，第七章已涉及 X11 转发与 VNC，本文档针对 pure_kaili/run_kali.bat 这个具体 bat 文件做针对性分析，是该指南第七章在 Windows 宿主场景下的落地补充。
- 原文件 run_kali.bat 保持不变，本文档仅作分析与方案备份，不修改原文件。

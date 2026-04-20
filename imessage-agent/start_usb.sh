#!/bin/bash

set -e

echo "======================================"
echo "  iPhone 群控 - USB 连接检查与启动"
echo "======================================"

DEVICES=$(idevice_id -l 2>/dev/null)
DEVICE_COUNT=$(echo "$DEVICES" | grep -c . || echo 0)

if [ "$DEVICE_COUNT" -eq 0 ]; then
    echo "❌ 未检测到 iPhone 设备"
    echo ""
    echo "请检查："
    echo "  1. iPhone 已通过 USB 数据线连接到 Mac"
    echo "  2. 数据线支持数据传输（不是仅充电线）"
    echo "  3. iPhone 上已点击「信任此电脑」"
    echo "  4. 已安装 libimobiledevice: brew install libimobiledevice"
    exit 1
fi

echo "📱 检测到 $DEVICE_COUNT 台 iPhone 设备"
echo "--------------------------------------"

PORT=8100
for UDID in $DEVICES; do
    NAME=$(ideviceinfo -u $UDID -k DeviceName 2>/dev/null || echo "Unknown")
    IOS_VER=$(ideviceinfo -u $UDID -k ProductVersion 2>/dev/null || echo "?")
    echo "  📱 $NAME (iOS $IOS_VER) - UDID: ${UDID:0:12}... → 端口 $PORT"
    PORT=$((PORT + 100))
done

echo ""
echo "正在启动端口映射..."
echo "--------------------------------------"

PORT=8100
PIDS=()

for UDID in $DEVICES; do
    NAME=$(ideviceinfo -u $UDID -k DeviceName 2>/dev/null || echo "Unknown")

    lsof -i :$PORT > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "  ⚠️  端口 $PORT 已被占用，跳过 ($NAME)"
    else
        iproxy $PORT 8100 -u $UDID > /dev/null 2>&1 &
        PIDS+=($!)
        echo "  ✅ $NAME → localhost:$PORT (PID: $!)"
    fi

    PORT=$((PORT + 100))
done

echo ""
echo "等待端口映射就绪..."
sleep 2

echo ""
echo "验证连接..."
echo "--------------------------------------"

PORT=8100
ONLINE=0
OFFLINE=0

for UDID in $DEVICES; do
    NAME=$(ideviceinfo -u $UDID -k DeviceName 2>/dev/null || echo "Unknown")

    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/status 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "  ✅ $NAME (localhost:$PORT) - WDA 在线"
        ONLINE=$((ONLINE + 1))
    else
        echo "  ⚠️  $NAME (localhost:$PORT) - WDA 离线（需先部署 WebDriverAgent）"
        OFFLINE=$((OFFLINE + 1))
    fi

    PORT=$((PORT + 100))
done

echo ""
echo "======================================"
echo "  在线: $ONLINE | 离线: $OFFLINE"
echo "======================================"

if [ "$OFFLINE" -gt 0 ]; then
    echo ""
    echo "⚠️  有设备 WDA 离线，请先部署 WebDriverAgent："
    echo ""
    echo "  方法一：Xcode GUI"
    echo "    1. 打开 WebDriverAgent.xcodeproj"
    echo "    2. 配置签名 (Signing & Capabilities)"
    echo "    3. 选择 iPhone 设备 → 长按 Run → Test"
    echo "    4. iPhone 上信任开发者证书"
    echo ""
    echo "  方法二：命令行"
    PORT=8100
    for UDID in $DEVICES; do
        echo "    xcodebuild -project WebDriverAgent.xcodeproj -scheme WebDriverAgentRunner -destination 'id=$UDID' test &"
        PORT=$((PORT + 100))
    done
fi

echo ""
echo "端口映射进程运行中，按 Ctrl+C 停止"
echo ""

trap "echo '正在停止端口映射...'; kill ${PIDS[@]} 2>/dev/null; echo '已停止'; exit 0" SIGINT SIGTERM

wait

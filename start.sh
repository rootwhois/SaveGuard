#!/bin/bash

echo "Starting SaveGuard..."
echo ""
echo "正在启动 SaveGuard 程序监控工具..."
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.6+"
    exit 1
fi

# 检查依赖是否安装
python3 -c "import PyQt5, psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "正在安装依赖包..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败"
        exit 1
    fi
fi

# 启动程序
echo "启动SaveGuard..."
python3 run.py

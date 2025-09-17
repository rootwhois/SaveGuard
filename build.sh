#!/bin/bash
# SaveGuard 构建脚本 (Linux/macOS)

set -e  # 遇到错误立即退出

echo "🚀 SaveGuard 构建脚本"
echo "================================================"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

echo "✅ Python已安装"
python3 --version

# 检查是否在正确的目录
if [ ! -f "run.py" ]; then
    echo "❌ 请在SaveGuard项目根目录运行此脚本"
    exit 1
fi

echo "✅ 项目文件检查通过"

# 安装构建依赖
echo ""
echo "📦 安装构建依赖..."
python3 -m pip install -r requirements-build.txt
if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

echo "✅ 依赖安装完成"

# 执行构建
echo ""
echo "🔨 开始构建..."
python3 build_all.py
if [ $? -ne 0 ]; then
    echo "❌ 构建失败"
    exit 1
fi

echo ""
echo "🎉 构建完成！"
echo ""
echo "📁 构建文件位置:"
if [ -d "dist" ]; then
    ls -la dist/SaveGuard-* 2>/dev/null || echo "  无构建文件"
fi

if [ -d "release" ]; then
    echo ""
    echo "📁 发布包位置:"
    ls -la release/SaveGuard-* 2>/dev/null || echo "  无发布包"
fi

echo ""
echo "💡 使用说明:"
echo "1. 在 release 目录中找到对应您系统的可执行文件"
echo "2. 双击运行即可，无需安装Python环境"
echo "3. 首次运行可能需要执行权限: chmod +x SaveGuard-*"
echo ""

#!/bin/bash
# SaveGuard macOS 构建脚本
# 专门处理 macOS 上的 PyQt5 安装和构建问题

set -e  # 遇到错误立即退出

echo "🍎 SaveGuard macOS 构建脚本"
echo "================================================"

# 检查是否在 macOS 上运行
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ 此脚本仅适用于 macOS"
    exit 1
fi

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python 3.7+"
    exit 1
fi

echo "✅ Python 已安装"
python3 --version

# 检查是否在正确的目录
if [ ! -f "run.py" ]; then
    echo "❌ 请在 SaveGuard 项目根目录运行此脚本"
    exit 1
fi

echo "✅ 项目文件检查通过"

# 检查 Homebrew
if ! command -v brew &> /dev/null; then
    echo "❌ 未找到 Homebrew，请先安装 Homebrew"
    echo "安装命令: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "✅ Homebrew 已安装"

# 安装 Qt5
echo ""
echo "🍺 安装 Qt5..."
if ! brew list qt@5 &> /dev/null; then
    brew install qt@5
    echo "✅ Qt5 安装完成"
else
    echo "✅ Qt5 已安装"
fi

# 设置 Qt5 环境变量
QT_DIR=$(brew --prefix qt@5)
export QT_DIR
export PATH="$QT_DIR/bin:$PATH"
export PKG_CONFIG_PATH="$QT_DIR/lib/pkgconfig:$PKG_CONFIG_PATH"
export LDFLAGS="-L$QT_DIR/lib"
export CPPFLAGS="-I$QT_DIR/include"

echo "🔧 Qt5 环境变量已设置"
echo "QT_DIR: $QT_DIR"

# 验证 qmake
if command -v qmake &> /dev/null; then
    echo "✅ qmake 可用"
    qmake --version
else
    echo "❌ qmake 不可用"
    exit 1
fi

# 升级 pip
echo ""
echo "📦 升级 pip..."
python3 -m pip install --upgrade pip

# 安装依赖
echo ""
echo "📦 安装 Python 依赖..."

# 先尝试安装预编译的 PyQt5
echo "尝试安装预编译 PyQt5..."
if python3 -m pip install PyQt5==5.15.10 --only-binary=all --no-cache-dir; then
    echo "✅ 预编译 PyQt5 安装成功"
else
    echo "⚠️ 预编译 PyQt5 安装失败，尝试从源码编译..."
    
    # 安装 SIP
    echo "安装 SIP..."
    python3 -m pip install sip>=6.0.0 --no-cache-dir
    
    # 从源码编译 PyQt5
    echo "从源码编译 PyQt5..."
    if python3 -m pip install PyQt5==5.15.10 --no-binary=PyQt5 --no-cache-dir --config-settings="--qmake=$QT_DIR/bin/qmake"; then
        echo "✅ 源码编译 PyQt5 成功"
    else
        echo "⚠️ 源码编译失败，尝试使用 PyQt5 5.15.9..."
        if python3 -m pip install PyQt5==5.15.9 --no-cache-dir; then
            echo "✅ PyQt5 5.15.9 安装成功"
        else
            echo "❌ PyQt5 安装失败"
            exit 1
        fi
    fi
fi

# 安装其他依赖
echo "安装其他依赖..."
python3 -m pip install psutil==5.9.5 pygame==2.5.2 pynput==1.7.6 --no-cache-dir
python3 -m pip install pyinstaller>=5.13.0 --no-cache-dir

# 验证 PyQt5 安装
echo ""
echo "🔍 验证 PyQt5 安装..."
if python3 -c "import PyQt5; from PyQt5.QtCore import QT_VERSION_STR; print(f'Qt 版本: {QT_VERSION_STR}')"; then
    echo "✅ PyQt5 验证成功"
else
    echo "❌ PyQt5 验证失败"
    exit 1
fi

# 执行构建
echo ""
echo "🔨 开始构建..."
python3 build_all.py --platforms macos --force

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 构建完成！"
    echo ""
    echo "📁 构建文件位置:"
    if [ -d "dist" ]; then
        ls -la dist/SaveGuard-Macos-* 2>/dev/null || echo "  无构建文件"
    fi
    
    if [ -d "release" ]; then
        echo ""
        echo "📁 发布包位置:"
        ls -la release/SaveGuard-Macos-* 2>/dev/null || echo "  无发布包"
    fi
    
    echo ""
    echo "💡 使用说明:"
    echo "1. 在 release 目录中找到对应您系统的可执行文件"
    echo "2. 双击运行即可，无需安装 Python 环境"
    echo "3. 首次运行可能需要执行权限: chmod +x SaveGuard-Macos-*"
    echo ""
else
    echo "❌ 构建失败"
    exit 1
fi

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS 依赖安装脚本
专门处理 macOS 上的 PyQt5 安装问题
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def run_command(cmd, check=True, timeout=300):
    """运行命令并处理错误"""
    try:
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, 
            check=check, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            encoding='utf-8',
            errors='ignore'
        )
        if result.stdout:
            print(f"输出: {result.stdout}")
        return result
    except subprocess.TimeoutExpired:
        print(f"❌ 命令超时: {' '.join(cmd)}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令失败: {' '.join(cmd)}")
        if e.stderr:
            print(f"错误: {e.stderr}")
        return None
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return None

def check_brew():
    """检查 Homebrew 是否安装"""
    result = run_command(["brew", "--version"], check=False)
    return result is not None and result.returncode == 0

def install_qt5():
    """安装 Qt5"""
    print("🍺 安装 Qt5...")
    
    # 检查是否已安装
    result = run_command(["brew", "list", "qt@5"], check=False)
    if result and result.returncode == 0:
        print("✅ Qt5 已安装")
        return True
    
    # 安装 Qt5
    result = run_command(["brew", "install", "qt@5"])
    if result and result.returncode == 0:
        print("✅ Qt5 安装成功")
        return True
    else:
        print("❌ Qt5 安装失败")
        return False

def setup_qt5_environment():
    """设置 Qt5 环境变量"""
    print("🔧 设置 Qt5 环境变量...")
    
    # 获取 Qt5 路径
    result = run_command(["brew", "--prefix", "qt@5"], check=False)
    if not result or result.returncode != 0:
        print("❌ 无法获取 Qt5 路径")
        return False
    
    qt_dir = result.stdout.strip()
    print(f"Qt5 路径: {qt_dir}")
    
    # 设置环境变量
    env_vars = {
        'QT_DIR': qt_dir,
        'PATH': f"{qt_dir}/bin:{os.environ.get('PATH', '')}",
        'PKG_CONFIG_PATH': f"{qt_dir}/lib/pkgconfig:{os.environ.get('PKG_CONFIG_PATH', '')}",
        'LDFLAGS': f"-L{qt_dir}/lib",
        'CPPFLAGS': f"-I{qt_dir}/include",
        'QMAKE': f"{qt_dir}/bin/qmake"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"设置 {key}={value}")
    
    # 验证 qmake
    result = run_command(["qmake", "--version"], check=False)
    if result and result.returncode == 0:
        print("✅ qmake 验证成功")
        return True
    else:
        print("❌ qmake 验证失败")
        return False

def install_pyqt5_with_fallback():
    """使用多种方法安装 PyQt5"""
    print("🐍 安装 PyQt5...")
    
    # 方法1: 尝试安装预编译版本
    print("方法1: 尝试安装预编译版本...")
    result = run_command([
        sys.executable, "-m", "pip", "install", 
        "PyQt5==5.15.10", 
        "--only-binary=all",
        "--no-cache-dir"
    ], check=False, timeout=180)
    
    if result and result.returncode == 0:
        print("✅ 预编译版本安装成功")
        return True
    
    print("⚠️ 预编译版本安装失败，尝试从源码编译...")
    
    # 方法2: 从源码编译
    print("方法2: 从源码编译...")
    result = run_command([
        sys.executable, "-m", "pip", "install", 
        "PyQt5==5.15.10",
        "--no-binary=PyQt5",
        "--no-cache-dir",
        "--config-settings", f"--qmake={os.environ.get('QMAKE', 'qmake')}"
    ], check=False, timeout=600)
    
    if result and result.returncode == 0:
        print("✅ 源码编译成功")
        return True
    
    print("⚠️ 源码编译失败，尝试使用 SIP...")
    
    # 方法3: 先安装 SIP，再安装 PyQt5
    print("方法3: 安装 SIP 后安装 PyQt5...")
    
    # 安装 SIP
    sip_result = run_command([
        sys.executable, "-m", "pip", "install", 
        "sip>=6.0.0",
        "--no-cache-dir"
    ], check=False, timeout=300)
    
    if sip_result and sip_result.returncode == 0:
        print("✅ SIP 安装成功")
        
        # 再次尝试安装 PyQt5
        result = run_command([
            sys.executable, "-m", "pip", "install", 
            "PyQt5==5.15.10",
            "--no-cache-dir"
        ], check=False, timeout=600)
        
        if result and result.returncode == 0:
            print("✅ PyQt5 安装成功")
            return True
    
    print("⚠️ 所有方法都失败了，尝试使用 PyQt5 5.15.9...")
    
    # 方法4: 尝试使用较旧版本
    result = run_command([
        sys.executable, "-m", "pip", "install", 
        "PyQt5==5.15.9",
        "--no-cache-dir"
    ], check=False, timeout=600)
    
    if result and result.returncode == 0:
        print("✅ PyQt5 5.15.9 安装成功")
        return True
    
    print("❌ 所有 PyQt5 安装方法都失败了")
    return False

def install_other_dependencies():
    """安装其他依赖"""
    print("📦 安装其他依赖...")
    
    dependencies = [
        "psutil==5.9.5",
        "pygame==2.5.2", 
        "pynput==1.7.6",
        "pyinstaller>=5.13.0"
    ]
    
    for dep in dependencies:
        print(f"安装 {dep}...")
        result = run_command([
            sys.executable, "-m", "pip", "install", 
            dep,
            "--no-cache-dir"
        ], check=False, timeout=300)
        
        if result and result.returncode == 0:
            print(f"✅ {dep} 安装成功")
        else:
            print(f"❌ {dep} 安装失败")
            return False
    
    return True

def verify_installation():
    """验证安装"""
    print("🔍 验证安装...")
    
    try:
        import PyQt5
        print("✅ PyQt5 导入成功")
        
        from PyQt5.QtCore import QT_VERSION_STR
        print(f"✅ Qt 版本: {QT_VERSION_STR}")
        
        from PyQt5.QtWidgets import QApplication
        app = QApplication([])
        print("✅ PyQt5 应用创建成功")
        app.quit()
        
        return True
    except Exception as e:
        print(f"❌ PyQt5 验证失败: {e}")
        return False

def main():
    """主函数"""
    print("🍎 macOS 依赖安装脚本")
    print("=" * 50)
    
    # 检查平台
    if platform.system() != "Darwin":
        print("❌ 此脚本仅适用于 macOS")
        return False
    
    # 检查 Python 版本
    if sys.version_info < (3, 7):
        print("❌ 需要 Python 3.7 或更高版本")
        return False
    
    print(f"✅ Python 版本: {sys.version}")
    
    # 检查 Homebrew
    if not check_brew():
        print("❌ 未找到 Homebrew，请先安装 Homebrew")
        print("安装命令: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return False
    
    print("✅ Homebrew 已安装")
    
    # 安装 Qt5
    if not install_qt5():
        return False
    
    # 设置 Qt5 环境
    if not setup_qt5_environment():
        return False
    
    # 安装 PyQt5
    if not install_pyqt5_with_fallback():
        return False
    
    # 安装其他依赖
    if not install_other_dependencies():
        return False
    
    # 验证安装
    if not verify_installation():
        return False
    
    print("\n🎉 所有依赖安装完成！")
    print("现在可以运行构建脚本了:")
    print("python build_all.py --platforms macos --force")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SaveGuard 启动脚本
"""

import sys
import os
from pathlib import Path

# 检查是否在PyInstaller打包环境中
if getattr(sys, 'frozen', False):
    # 如果是打包后的可执行文件
    base_path = Path(sys._MEIPASS)
    src_dir = base_path / 'src'
else:
    # 如果是开发环境
    current_dir = Path(__file__).parent
    src_dir = current_dir / 'src'

# 添加src目录到Python路径
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

# 导入saveguard模块
try:
    from saveguard import main
except ImportError as e:
    print(f"导入错误: {e}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本目录: {Path(__file__).parent}")
    print(f"src目录: {src_dir}")
    print(f"Python路径: {sys.path}")
    print(f"是否打包环境: {getattr(sys, 'frozen', False)}")
    
    # 尝试直接导入
    try:
        import saveguard
        main = saveguard.main
    except ImportError:
        print("无法导入saveguard模块")
        sys.exit(1)

if __name__ == "__main__":
    main()

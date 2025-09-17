# SaveGuard

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version](https://img.shields.io/badge/Version-1.0-green.svg)](https://github.com/rootwhois/SaveGuard)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/rootwhois/SaveGuard)

> 跨平台程序保存提醒工具 - 让您永远不会忘记保存工作成果

## 📖 项目简介

SaveGuard 是一款智能的程序监控和保存提醒工具，专为程序员、设计师、办公人员等需要频繁保存工作成果的用户设计。它能够实时监控指定程序的运行状态，在程序运行超过设定时间后自动提醒用户保存，并提供一键保存功能，有效防止因意外断电、程序崩溃等原因导致的工作成果丢失。

## ✨ 主要功能

### 🔍 程序监控
- **实时监控** - 自动检测指定程序的启动和关闭
- **智能识别** - 支持多种程序类型（代码编辑器、办公软件、设计工具等）
- **启动检测** - 软件启动时自动检测已运行的目标程序

### ⏰ 定时提醒
- **自定义间隔** - 可设置提醒间隔（10秒-60分钟）
- **智能提醒** - 根据程序类型显示不同的提醒消息
- **声音提醒** - 支持系统声音提醒

### 💬 优雅界面
- **气泡提示** - 半透明气泡提醒，不干扰工作
- **系统托盘** - 最小化到系统托盘，随时访问
- **拖拽移动** - 浮窗可自由拖拽到任意位置

### 💾 自动保存
- **聚焦保存** - 用户回到程序时自动执行Ctrl+S
- **一键保存** - 气泡提示中的立即保存按钮
- **智能切换** - 自动切换到目标程序并执行保存

### 🕐 整点提醒
- **定时提醒** - 每小时整点自动提醒保存
- **工作节奏** - 帮助建立良好的保存习惯

### 📊 历史记录
- **提醒历史** - 记录所有提醒操作
- **统计分析** - 查看提醒频率和模式

### 🌍 多语言支持
- **国际化** - 支持中文、英文、日文、韩文
- **动态切换** - 运行时切换语言无需重启

## 🚀 快速开始

### 系统要求

- **操作系统**: Windows 7+, macOS 10.12+, Linux (Ubuntu 16.04+)
- **Python版本**: 3.7 或更高版本
- **内存**: 至少 100MB 可用内存
- **磁盘空间**: 至少 50MB 可用空间

### 安装方式

#### 方式一：直接下载可执行文件（推荐）

1. 访问 [Releases页面](https://github.com/rootwhois/SaveGuard/releases)
2. 根据您的操作系统下载对应的可执行文件
3. 双击运行即可，无需安装Python环境

#### 方式二：从源码运行

1. **克隆项目**
   ```bash
   git clone https://github.com/rootwhois/SaveGuard.git
   cd SaveGuard
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   # Windows
   start.bat
   
   # macOS/Linux
   ./start.sh
   
   # 或直接运行
   python run.py
   ```

### 使用说明

1. **首次运行** - 程序会自动检测已运行的程序
2. **选择程序** - 右键点击浮窗或托盘图标，选择"选择应用程序"
3. **设置提醒** - 在设置中调整提醒间隔和其他选项
4. **开始监控** - 程序将自动监控选定的应用程序

## 📋 支持的程序

### 代码编辑器
- Visual Studio Code
- Sublime Text
- Atom
- Notepad++
- Vim/Emacs
- PyCharm
- IntelliJ IDEA
- WebStorm
- CLion
- Rider

### 办公软件
- Microsoft Word
- Microsoft Excel
- Microsoft PowerPoint
- WPS Office
- Typora
- Obsidian

### 设计工具
- Adobe Photoshop
- Adobe Illustrator
- Figma
- Sketch
- Blender

### 浏览器
- Google Chrome
- Mozilla Firefox
- Microsoft Edge

## ⚙️ 配置选项

### 基本设置
- **提醒间隔**: 10秒 - 60分钟
- **气泡显示时长**: 1-10秒
- **声音提醒**: 开启/关闭
- **语言设置**: 中文/英文/日文/韩文

### 高级功能
- **聚焦时自动保存**: 用户回到程序时自动执行保存
- **整点提醒**: 每小时整点提醒保存
- **欢迎消息**: 程序启动时显示欢迎消息
- **自动选择应用**: 启动时自动选择常见应用程序

### 自定义消息
- **默认消息**: 通用提醒消息
- **代码编辑器**: 代码编辑专用消息
- **办公软件**: 文档编辑专用消息
- **设计工具**: 设计工作专用消息
- **欢迎消息**: 程序启动欢迎消息
- **整点提醒**: 整点提醒专用消息

## 🔧 开发说明

### 项目结构
```
SaveGuard/
├── src/                    # 源代码目录
│   ├── saveguard.py       # 主程序文件
│   ├── language_manager.py # 多语言管理器
│   └── languages/         # 语言文件目录
│       ├── zh_CN.json     # 中文语言包
│       ├── en_US.json     # 英文语言包
│       ├── ja_JP.json     # 日文语言包
│       └── ko_KR.json     # 韩文语言包
├── build/                 # 构建输出目录
├── dist/                  # 分发文件目录
├── release/               # 发布包目录
├── specs/                 # PyInstaller规格文件
├── doc/                   # 文档目录
├── requirements.txt       # Python依赖
├── build_all.py          # 多平台构建脚本
├── run.py                # 启动脚本
├── start.bat             # Windows启动脚本
├── start.sh              # Unix启动脚本
└── LICENSE               # Apache 2.0许可证
```

### 构建说明

#### 构建所有平台
```bash
python build_all.py
```

#### 构建特定平台
```bash
# 只构建当前平台
python build_all.py --current-only

# 构建指定平台
python build_all.py --platforms windows linux

# 智能模式（推荐）
python build_all.py --smart
```

### 技术栈
- **GUI框架**: PyQt5
- **进程监控**: psutil
- **键盘模拟**: pynput
- **声音播放**: pygame, winsound
- **多语言**: 自定义JSON语言包
- **打包工具**: PyInstaller

## 🤝 贡献指南

我们欢迎所有形式的贡献！请查看 [贡献指南](doc/CONTRIBUTING.md) 了解详细信息。

### 如何贡献
1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

### 报告问题
如果您发现了bug或有功能建议，请通过 [Issues页面](https://github.com/rootwhois/SaveGuard/issues) 报告。

## 📄 许可证

本项目采用 Apache 2.0 许可证 - 查看 [LICENSE](LICENSE) 文件了解详细信息。

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户！

## 📞 联系我们

- **项目地址**: https://github.com/rootwhois/SaveGuard
- **问题反馈**: https://github.com/rootwhois/SaveGuard/issues

---

**SaveGuard** - 让保存成为一种习惯，让工作更加安心！ 🛡️
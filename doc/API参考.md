# SaveGuard API 参考

## 目录
- [核心类](#核心类)
- [配置管理](#配置管理)
- [多语言系统](#多语言系统)
- [进程监控](#进程监控)
- [自动保存](#自动保存)
- [用户界面](#用户界面)
- [工具函数](#工具函数)

## 核心类

### SaveGuardWidget
主窗口控件类，继承自QWidget。

```python
class SaveGuardWidget(QWidget):
    """主浮窗控件"""
    
    def __init__(self):
        """初始化主窗口"""
        pass
    
    def init_ui(self):
        """初始化用户界面"""
        pass
    
    def setup_tray_icon(self):
        """设置系统托盘图标"""
        pass
```

**主要方法**:
- `select_applications()`: 选择要监控的应用程序
- `manage_programs()`: 管理监控程序列表
- `show_settings()`: 显示设置对话框
- `start_monitoring()`: 开始监控程序
- `quit_application()`: 退出应用程序

### SaveGuardApp
主应用程序类，继承自QApplication。

```python
class SaveGuardApp(QApplication):
    """主应用程序"""
    
    def __init__(self, argv):
        """初始化应用程序"""
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)
```

## 配置管理

### RemindConfig
提醒配置管理类。

```python
class RemindConfig:
    """提醒配置类"""
    
    def __init__(self):
        self.interval_seconds = 300          # 提醒间隔（秒）
        self.sound_enabled = True            # 是否启用声音
        self.bubble_duration = 5000          # 气泡显示时长（毫秒）
        self.remind_frequency = "repeat"     # 提醒频率
        self.focus_auto_save_enabled = False # 聚焦时自动保存
        self.hourly_remind_enabled = False   # 整点提醒
        self.welcome_message_enabled = True  # 欢迎消息
        self.auto_select_apps = True         # 自动选择应用
        self.language = "zh_CN"              # 语言设置
        self.remind_messages = {}            # 提醒消息字典
```

**主要方法**:
- `to_dict() -> Dict`: 将配置转换为字典
- `from_dict(data: Dict)`: 从字典加载配置

**配置项说明**:
- `interval_seconds`: 程序运行多长时间后提醒（10-3600秒）
- `sound_enabled`: 是否播放声音提醒
- `bubble_duration`: 气泡提示显示时长（1000-10000毫秒）
- `focus_auto_save_enabled`: 用户回到程序时是否自动保存
- `hourly_remind_enabled`: 是否启用整点提醒
- `welcome_message_enabled`: 程序启动时是否显示欢迎消息
- `auto_select_apps`: 启动时是否自动选择常见应用程序
- `language`: 界面语言（zh_CN, en_US, ja_JP, ko_KR）

### RemindHistory
提醒历史记录管理类。

```python
class RemindHistory:
    """提醒历史记录"""
    
    def __init__(self):
        self.history = []           # 历史记录列表
        self.max_records = 100      # 最大记录数
    
    def add_record(self, program_name: str, remind_type: str, timestamp: datetime):
        """添加提醒记录"""
        pass
    
    def get_recent_records(self, count: int = 10) -> List[Dict]:
        """获取最近的记录"""
        pass
```

## 多语言系统

### LanguageManager
多语言管理器，继承自QObject。

```python
class LanguageManager(QObject):
    """多语言管理器"""
    
    language_changed = pyqtSignal(str)  # 语言切换信号
    
    def __init__(self):
        self.current_language = "zh_CN"
        self.translations = {}
        self.supported_languages = {
            "zh_CN": "简体中文",
            "en_US": "English",
            "ja_JP": "日本語",
            "ko_KR": "한국어",
        }
```

**主要方法**:
- `get_supported_languages() -> Dict[str, str]`: 获取支持的语言列表
- `get_current_language() -> str`: 获取当前语言
- `set_language(language_code: str) -> bool`: 设置语言
- `translate(key: str, **kwargs) -> str`: 翻译文本
- `tr(key: str, **kwargs) -> str`: 翻译文本的简写方法

**全局函数**:
- `get_language_manager() -> LanguageManager`: 获取全局语言管理器实例
- `tr(key: str, **kwargs) -> str`: 全局翻译函数

**语言文件格式**:
```json
{
  "main_window": {
    "title": "SaveGuard",
    "monitoring": "监控中...",
    "waiting": "等待程序..."
  },
  "messages": {
    "default": "请记得保存您的劳动成果！",
    "code": "代码已修改，记得保存！"
  }
}
```

## 进程监控

### ProgramMonitorThread
程序监控线程，继承自QThread。

```python
class ProgramMonitorThread(QThread):
    """程序监控线程"""
    
    program_started = pyqtSignal(str, str)  # 程序启动信号 (程序名, 进程ID)
    program_stopped = pyqtSignal(str)       # 程序停止信号 (程序名)
    
    def __init__(self, target_programs: List[str]):
        self.target_programs = target_programs
        self.running_programs = {}  # 运行中的程序字典
        self.running = True
```

**主要方法**:
- `run()`: 主监控循环
- `_get_running_programs() -> Dict[str, int]`: 获取当前运行的程序
- `stop()`: 停止监控线程

**信号说明**:
- `program_started`: 当检测到目标程序启动时发射
- `program_stopped`: 当检测到目标程序停止时发射

## 自动保存

### AutoSaveManager
聚焦时自动保存管理器。

```python
class AutoSaveManager:
    """聚焦时自动保存管理器"""
    
    def __init__(self, target_programs: List[str]):
        self.target_programs = target_programs
        self.focus_auto_save_enabled = False
        self.keyboard_controller = None
        self.pending_save_programs = set()
```

**主要方法**:
- `enable_auto_save(enabled: bool)`: 启用/禁用自动保存
- `add_pending_save(program_name: str)`: 添加等待保存的程序
- `check_and_save()`: 检查当前聚焦程序并执行保存
- `perform_auto_save(program_name: str) -> bool`: 执行一键保存
- `get_focused_program() -> Optional[str]`: 获取当前聚焦的程序
- `is_currently_focused(program_name: str) -> bool`: 检查是否聚焦在指定程序
- `switch_to_program(program_name: str) -> bool`: 切换到目标程序

**依赖模块**:
- `pynput.keyboard`: 键盘模拟
- `win32gui`: Windows窗口管理
- `psutil`: 进程信息获取

## 用户界面

### BubbleTooltip
气泡提示组件，继承自QWidget。

```python
class BubbleTooltip(QWidget):
    """气泡提示组件"""
    
    auto_save_clicked = pyqtSignal(str)  # 自动保存按钮点击信号
    
    def __init__(self, parent=None):
        self.timer = QTimer()
        self.current_program = None
```

**主要方法**:
- `show_bubble(message: str, duration: int, program_name: str, show_auto_save: bool)`: 显示气泡提示
- `hide_bubble()`: 隐藏气泡
- `on_auto_save_clicked()`: 自动保存按钮点击处理

### HourlyReminder
整点提醒线程，继承自QThread。

```python
class HourlyReminder(QThread):
    """整点提醒线程"""
    
    remind_signal = pyqtSignal(str)  # 整点提醒信号
    
    def __init__(self):
        self.running = True
        self.last_hour = -1
```

**主要方法**:
- `run()`: 主提醒循环
- `stop()`: 停止提醒线程

## 对话框类

### AppSelectionDialog
应用程序选择对话框。

```python
class AppSelectionDialog(QDialog):
    """应用程序选择对话框"""
    
    def __init__(self, parent=None):
        self.selected_apps = []
        self.common_apps = [...]  # 预置应用程序列表
```

**主要方法**:
- `load_running_apps()`: 加载正在运行的应用程序
- `get_selected_apps() -> List[str]`: 获取选中的应用程序

### AdvancedSettingsDialog
高级设置对话框。

```python
class AdvancedSettingsDialog(QDialog):
    """高级设置对话框"""
    
    def __init__(self, config: RemindConfig, parent=None):
        self.config = config
```

**主要方法**:
- `get_config() -> RemindConfig`: 获取配置对象

### ProgramManagerDialog
程序管理对话框。

```python
class ProgramManagerDialog(QDialog):
    """程序管理对话框"""
    
    def __init__(self, programs: List[str], parent=None):
        self.programs = programs.copy()
```

**主要方法**:
- `add_program()`: 添加程序
- `remove_program()`: 删除程序
- `get_programs() -> List[str]`: 获取程序列表

### HistoryDialog
提醒历史对话框。

```python
class HistoryDialog(QDialog):
    """提醒历史对话框"""
    
    def __init__(self, history: RemindHistory, parent=None):
        self.history = history
```

**主要方法**:
- `clear_history()`: 清空历史记录

## 工具函数

### 全局常量
```python
VERSION = "1.0"                                    # 版本号
GITHUB_URL = "https://github.com/rootwhois/saveguard"  # 项目地址
```

### 信号处理器
```python
def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n收到信号 {signum}，正在强制退出...")
    sys.exit(0)
```

### 主函数
```python
def main():
    """主函数"""
    # 检查依赖
    # 设置信号处理
    # 创建并运行应用程序
    pass
```

## 错误处理

### 异常类型
- `ImportError`: 模块导入错误
- `PermissionError`: 权限错误
- `psutil.AccessDenied`: 进程访问被拒绝
- `psutil.NoSuchProcess`: 进程不存在
- `psutil.ZombieProcess`: 僵尸进程

### 错误处理策略
1. **依赖检查**: 启动时检查必要的模块是否安装
2. **权限处理**: 自动检测并提示需要管理员权限
3. **进程访问**: 优雅处理进程访问权限问题
4. **信号处理**: 正确处理程序退出信号

## 性能优化

### 内存管理
- 使用弱引用避免循环引用
- 及时清理不需要的对象
- 限制历史记录数量

### 线程安全
- 使用Qt信号槽机制进行线程间通信
- 避免在非主线程中直接操作UI
- 使用线程安全的数据结构

### 资源管理
- 及时释放系统资源
- 使用上下文管理器
- 正确处理异常情况

---

**注意**: 本API参考基于SaveGuard v1.0编写，如有更新请查看最新版本。

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SaveGuard - 跨平台文件保存提醒浮窗控件
监控指定文件，提醒用户定期保存

版本: 1.0
Github: https://github.com/rootwhois/saveguard
"""

import sys
import os
import time
import threading
import json
import signal
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta

# 导入语言管理器
from language_manager import get_language_manager, tr

# 版本信息
VERSION = "1.0"
GITHUB_URL = "https://github.com/rootwhois/saveguard"

# 跨平台声音支持
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

# 键盘模拟支持
try:
    from pynput import keyboard
    from pynput.keyboard import Key, Listener
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QMenu, QSystemTrayIcon,
                           QMessageBox, QInputDialog, QFileDialog, QSpinBox,
                           QCheckBox, QGroupBox, QTextEdit, QFrame, QComboBox,
                           QSlider, QTabWidget, QListWidget, QListWidgetItem,
                           QDialog, QDialogButtonBox, QFormLayout, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint, QSettings
from PyQt5.QtGui import QIcon, QPixmap, QFont, QCursor, QPainter, QColor
import psutil


class ProgramMonitorThread(QThread):
    """程序监控线程"""
    program_started = pyqtSignal(str, str)  # 程序启动信号 (程序名, 进程ID)
    program_stopped = pyqtSignal(str)  # 程序停止信号 (程序名)
    
    def __init__(self, target_programs: List[str]):
        super().__init__()
        self.target_programs = [p.lower() for p in target_programs]  # 转换为小写便于比较
        self.running = True
        self.running_programs = {}  # {程序名: 进程ID}
        self._stop_event = threading.Event()
        
    def run(self):
        while self.running and not self._stop_event.is_set():
            try:
                current_running = self._get_running_programs()
                
                # 检查新启动的程序
                for program_name, pid in current_running.items():
                    if program_name not in self.running_programs:
                        self.program_started.emit(program_name, str(pid))
                        self.running_programs[program_name] = pid
                
                # 检查停止的程序
                for program_name in list(self.running_programs.keys()):
                    if program_name not in current_running:
                        self.program_stopped.emit(program_name)
                        del self.running_programs[program_name]
                        
            except Exception as e:
                print(f"程序监控错误: {e}")
            
            # 使用事件等待，可以更快响应停止信号
            if self._stop_event.wait(2):  # 等待2秒或直到停止事件
                break
    
    def _get_running_programs(self) -> Dict[str, int]:
        """获取当前运行的目标程序列表"""
        running_programs = {}
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_info = proc.info
                    if proc_info['name']:
                        proc_name = proc_info['name'].lower()
                        # 移除.exe扩展名进行匹配
                        proc_name_no_ext = proc_name.replace('.exe', '')
                        # 检查是否为目标程序
                        for target in self.target_programs:
                            target_lower = target.lower()
                            target_no_ext = target_lower.replace('.exe', '')
                            # 支持多种匹配方式
                            if (target_lower == proc_name or 
                                target_lower == proc_name_no_ext or
                                target_no_ext == proc_name or
                                target_no_ext == proc_name_no_ext or
                                (target_lower in proc_name and len(target_lower) > 3) or
                                (proc_name in target_lower and len(proc_name) > 3)):
                                running_programs[target_lower] = proc_info['pid']
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            print(f"获取运行程序列表错误: {e}")
        return running_programs
    
    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.isRunning():
            self.quit()
            self.wait(3000)  # 最多等待3秒


class RemindConfig:
    """提醒配置类"""
    def __init__(self):
        self.interval_seconds = 300  # 提醒间隔（秒），默认5分钟
        self.sound_enabled = True  # 是否启用声音
        self.bubble_duration = 5000  # 气泡显示时长（毫秒）
        self.remind_frequency = "repeat"  # 提醒频率: repeat
        self.focus_auto_save_enabled = False  # 是否启用聚焦时自动保存
        self.hourly_remind_enabled = False  # 是否启用整点提醒
        self.welcome_message_enabled = True  # 是否显示程序打开欢迎消息
        self.auto_select_apps = True  # 是否自动选择应用程序
        self.language = "zh_CN"  # 语言设置
        self.remind_messages = {
            "default": tr("messages.default"),
            "code": tr("messages.code"),
            "document": tr("messages.document"),
            "design": tr("messages.design"),
            "welcome": tr("messages.welcome"),
            "hourly": tr("messages.hourly")
        }
        
    def to_dict(self):
        return {
            'interval_seconds': self.interval_seconds,
            'sound_enabled': self.sound_enabled,
            'bubble_duration': self.bubble_duration,
            'remind_frequency': self.remind_frequency,
            'focus_auto_save_enabled': self.focus_auto_save_enabled,
            'hourly_remind_enabled': self.hourly_remind_enabled,
            'welcome_message_enabled': self.welcome_message_enabled,
            'auto_select_apps': self.auto_select_apps,
            'language': self.language,
            'remind_messages': self.remind_messages
        }
    
    def from_dict(self, data):
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


class RemindHistory:
    """提醒历史记录"""
    def __init__(self):
        self.history = []
        self.max_records = 100
        
    def add_record(self, program_name: str, remind_type: str, timestamp: datetime):
        record = {
            'program': program_name,
            'type': remind_type,
            'timestamp': timestamp,
            'message': f"{program_name} - {remind_type} 提醒"
        }
        self.history.insert(0, record)
        if len(self.history) > self.max_records:
            self.history = self.history[:self.max_records]
    
    def get_recent_records(self, count: int = 10):
        return self.history[:count]


class BubbleTooltip(QWidget):
    """气泡提示组件"""
    
    # 信号定义
    auto_save_clicked = pyqtSignal(str)  # 自动保存按钮点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.hide)
        self.current_program = None
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setFixedSize(380, 140)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建半透明背景
        self.background_frame = QFrame()
        self.background_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(50, 50, 50, 220);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 150);
            }
        """)
        
        # 内容布局
        content_layout = QVBoxLayout(self.background_frame)
        content_layout.setContentsMargins(15, 10, 15, 10)
        
        # 标题
        self.title_label = QLabel(tr("bubble.title"))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #FFD700;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        
        # 消息
        self.message_label = QLabel()
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
            }
        """)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 立即保存按钮
        self.auto_save_btn = QPushButton(tr("bubble.save_now"))
        self.auto_save_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 150, 0, 200);
                color: white;
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: rgba(0, 180, 0, 200);
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 0, 200);
            }
        """)
        self.auto_save_btn.clicked.connect(self.on_auto_save_clicked)
        self.auto_save_btn.hide()  # 默认隐藏
        
        button_layout.addStretch()  # 左侧弹性空间
        button_layout.addWidget(self.auto_save_btn)
        button_layout.addStretch()  # 右侧弹性空间
        
        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.message_label)
        content_layout.addLayout(button_layout)
        
        main_layout.addWidget(self.background_frame)
        self.setLayout(main_layout)
    
    def show_bubble(self, message: str, duration: int = 3000, program_name: str = None, show_auto_save: bool = False):
        """显示气泡提示"""
        self.message_label.setText(message)
        self.current_program = program_name
        
        # 显示/隐藏自动保存按钮
        if show_auto_save and program_name:
            self.auto_save_btn.show()
        else:
            self.auto_save_btn.hide()
        
        # 计算位置（在父窗口旁边）
        if self.parent_widget:
            parent_rect = self.parent_widget.geometry()
            # 显示在父窗口右侧
            x = parent_rect.right() + 10
            y = parent_rect.top()
            self.move(x, y)
        
        self.show()
        self.raise_()
        
        # 设置自动隐藏
        self.timer.start(duration)
    
    def on_auto_save_clicked(self):
        """自动保存按钮点击处理"""
        if self.current_program:
            self.auto_save_clicked.emit(self.current_program)
        self.hide()
    
    def hide_bubble(self):
        """隐藏气泡"""
        self.hide()
        self.timer.stop()


class AutoSaveManager:
    """聚焦时自动保存管理器"""
    
    def __init__(self, target_programs: List[str]):
        self.target_programs = target_programs
        self.focus_auto_save_enabled = False
        self.keyboard_controller = None
        self.pending_save_programs = set()  # 等待保存的程序列表
        
        if HAS_PYNPUT:
            self.keyboard_controller = keyboard.Controller()
    
    def enable_auto_save(self, enabled: bool):
        """启用/禁用聚焦时自动保存"""
        self.focus_auto_save_enabled = enabled
        if not enabled:
            self.pending_save_programs.clear()  # 清空等待保存列表
    
    def add_pending_save(self, program_name: str):
        """添加等待保存的程序"""
        if self.focus_auto_save_enabled:
            self.pending_save_programs.add(program_name)
            print(f"[OK] {program_name} 已添加到等待保存列表")
    
    def check_and_save(self):
        """检查当前聚焦程序并执行自动保存"""
        if not self.focus_auto_save_enabled or not self.keyboard_controller:
            return
        
        try:
            # 检查当前聚焦的程序
            focused_program = self.get_focused_program()
            if focused_program:
                # 检查是否有等待保存的程序匹配当前聚焦的程序
                for pending_program in list(self.pending_save_programs):
                    if self.is_program_match(focused_program, pending_program):
                        # 执行自动保存
                        self.keyboard_controller.press(Key.ctrl)
                        self.keyboard_controller.press('s')
                        self.keyboard_controller.release('s')
                        self.keyboard_controller.release(Key.ctrl)
                        
                        # 从等待列表中移除
                        self.pending_save_programs.discard(pending_program)
                        print(f"[OK] 已为聚焦的 {focused_program} 执行自动保存（匹配 {pending_program}）")
                        return True
        except Exception as e:
            print(f"[ERROR] 聚焦时自动保存失败: {e}")
            return False
    
    def get_focused_program(self) -> Optional[str]:
        """获取当前聚焦的程序"""
        try:
            if sys.platform == "win32":
                import win32gui
                import win32process
                
                # 获取当前活动窗口
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    # 获取进程ID
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    # 获取进程信息
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    
                    # 检查是否为目标程序
                    for target in self.target_programs:
                        if target in process_name or process_name in target:
                            return process_name
        except Exception as e:
            print(f"检查聚焦程序失败: {e}")
        
        return None
    
    def is_currently_focused(self, program_name: str) -> bool:
        """检查当前是否聚焦在指定程序上"""
        try:
            if sys.platform == "win32":
                import win32gui
                import win32process
                
                # 获取当前活动窗口
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    # 获取进程ID
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    # 获取进程信息
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    
                    # 检查是否匹配目标程序
                    target_name = program_name.lower()
                    return (target_name in process_name or 
                            process_name in target_name or
                            target_name.replace('.exe', '') == process_name.replace('.exe', ''))
        except Exception as e:
            print(f"检查聚焦状态失败: {e}")
        
        return False
    
    def is_program_match(self, focused_program: str, target_program: str) -> bool:
        """检查聚焦的程序是否匹配目标程序"""
        try:
            focused_lower = focused_program.lower()
            target_lower = target_program.lower()
            
            # 移除.exe扩展名进行比较
            focused_no_ext = focused_lower.replace('.exe', '')
            target_no_ext = target_lower.replace('.exe', '')
            
            # 多种匹配方式
            return (target_lower in focused_lower or 
                    focused_lower in target_lower or
                    target_no_ext == focused_no_ext or
                    focused_no_ext == target_no_ext)
        except Exception as e:
            print(f"程序匹配检查失败: {e}")
            return False
    
    def perform_auto_save(self, program_name: str):
        """执行一键保存（立即保存）"""
        if not self.keyboard_controller:
            return False
        
        try:
            # 检查当前是否已经聚焦在目标程序上
            if self.is_currently_focused(program_name):
                # 如果已经聚焦，直接执行Ctrl+S
                self.keyboard_controller.press(Key.ctrl)
                self.keyboard_controller.press('s')
                self.keyboard_controller.release('s')
                self.keyboard_controller.release(Key.ctrl)
                print(f"[OK] 当前聚焦在 {program_name}，直接执行自动保存")
                return True
            else:
                # 如果未聚焦，先尝试切换到目标程序
                if self.switch_to_program(program_name):
                    # 等待一下让窗口切换完成
                    time.sleep(0.5)
                    # 执行Ctrl+S
                    self.keyboard_controller.press(Key.ctrl)
                    self.keyboard_controller.press('s')
                    self.keyboard_controller.release('s')
                    self.keyboard_controller.release(Key.ctrl)
                    print(f"[OK] 已切换到 {program_name} 并执行自动保存")
                    return True
                else:
                    print(f"[WARNING] 无法切换到 {program_name}，尝试直接保存")
                    # 如果无法切换，尝试直接保存
                    self.keyboard_controller.press(Key.ctrl)
                    self.keyboard_controller.press('s')
                    self.keyboard_controller.release('s')
                    self.keyboard_controller.release(Key.ctrl)
                    return False
        except Exception as e:
            print(f"[ERROR] 自动保存失败: {e}")
            return False
    
    def switch_to_program(self, program_name: str) -> bool:
        """切换到目标程序"""
        try:
            if sys.platform == "win32":
                import win32gui
                import win32process
                
                # 查找目标程序的窗口
                target_hwnd = self.find_program_window(program_name)
                if target_hwnd:
                    # 切换到目标窗口
                    win32gui.SetForegroundWindow(target_hwnd)
                    win32gui.ShowWindow(target_hwnd, 1)  # SW_SHOWNORMAL
                    return True
            return False
        except Exception as e:
            print(f"[ERROR] 切换程序失败: {e}")
            return False
    
    def find_program_window(self, program_name: str):
        """查找目标程序的窗口"""
        try:
            if sys.platform == "win32":
                import win32gui
                import win32process
                
                target_name = program_name.lower()
                target_hwnd = None
                
                def enum_windows_callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            proc_name = proc.name().lower()
                            
                            # 检查进程名是否匹配
                            if target_name in proc_name or proc_name in target_name:
                                windows.append(hwnd)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    return True
                
                windows = []
                win32gui.EnumWindows(enum_windows_callback, windows)
                
                # 返回第一个找到的窗口
                return windows[0] if windows else None
            return None
        except Exception as e:
            print(f"[ERROR] 查找程序窗口失败: {e}")
            return None


class HourlyReminder(QThread):
    """整点提醒线程"""
    
    remind_signal = pyqtSignal(str)  # 整点提醒信号
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.last_hour = -1
        self._stop_event = threading.Event()
    
    def run(self):
        while self.running and not self._stop_event.is_set():
            try:
                current_hour = datetime.now().hour
                if current_hour != self.last_hour and current_hour > 0:  # 避免午夜提醒
                    self.remind_signal.emit(f"整点提醒：{current_hour}:00")
                    self.last_hour = current_hour
            except Exception as e:
                print(f"整点提醒错误: {e}")
            
            # 使用事件等待，可以更快响应停止信号
            if self._stop_event.wait(60):  # 等待60秒或直到停止事件
                break
    
    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.isRunning():
            self.quit()
            self.wait(3000)  # 最多等待3秒




class SaveGuardWidget(QWidget):
    """主浮窗控件"""
    
    def __init__(self):
        super().__init__()
        self.target_programs = []  # 目标程序列表
        self.monitor_thread = None
        self.save_timers = {}  # 程序保存计时器
        self.remind_config = RemindConfig()  # 提醒配置
        self.remind_history = RemindHistory()  # 提醒历史
        self.auto_save_manager = None  # 自动保存管理器
        self.hourly_reminder = None  # 整点提醒
        self.bubble_tooltip = None  # 气泡提示
        self.is_dragging = False
        self.drag_position = QPoint()
        self.settings = QSettings("SaveGuard", "SaveGuard")  # 配置存储
        
        # 加载保存的配置
        self.load_settings()
        
        # 初始化自动保存和整点提醒
        self.init_auto_save()
        self.init_hourly_reminder()
        self.init_bubble_tooltip()
        
        # 连接语言切换信号
        lang_manager = get_language_manager()
        lang_manager.language_changed.connect(self.on_language_changed)
        
        self.init_ui()
        self.setup_tray_icon()
        
        # 设置主窗口图标
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # 检测已运行的程序（在UI初始化后）
        self.check_running_programs_on_startup()
    
    def init_auto_save(self):
        """初始化聚焦时自动保存管理器"""
        self.auto_save_manager = AutoSaveManager(self.target_programs)
        self.auto_save_manager.enable_auto_save(self.remind_config.focus_auto_save_enabled)
        
        # 创建定时器检查聚焦状态
        self.focus_timer = QTimer()
        self.focus_timer.timeout.connect(self.check_focus_and_save)
        
        # 只有在启用时才启动定时器
        if self.remind_config.focus_auto_save_enabled:
            self.focus_timer.start(2000)  # 每2秒检查一次
    
    def init_hourly_reminder(self):
        """初始化整点提醒"""
        if self.remind_config.hourly_remind_enabled:
            self.hourly_reminder = HourlyReminder()
            self.hourly_reminder.remind_signal.connect(self.on_hourly_remind)
            self.hourly_reminder.start()
    
    def init_bubble_tooltip(self):
        """初始化气泡提示"""
        self.bubble_tooltip = BubbleTooltip(self)
        self.bubble_tooltip.auto_save_clicked.connect(self.on_auto_save_from_bubble)
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(280, 140)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建半透明背景
        self.background_frame = QFrame()
        self.background_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(50, 50, 50, 200);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 100);
            }
        """)
        
        # 内容布局
        content_layout = QVBoxLayout(self.background_frame)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        self.title_label = QLabel(tr("main_window.title"))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 16px;
            }
        """)
        
        # 状态标签
        self.status_label = QLabel(tr("main_window.monitoring"))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #90EE90;
                font-size: 12px;
            }
        """)
        
        # 监控程序数量
        self.program_count_label = QLabel(tr("main_window.programs") + ": 0")
        self.program_count_label.setAlignment(Qt.AlignCenter)
        self.program_count_label.setStyleSheet("""
            QLabel {
                color: #87CEEB;
                font-size: 11px;
            }
        """)
        
        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.status_label)
        content_layout.addWidget(self.program_count_label)
        
        main_layout.addWidget(self.background_frame)
        self.setLayout(main_layout)
        
        # 设置鼠标事件
        self.background_frame.mousePressEvent = self.mouse_press_event
        self.background_frame.mouseMoveEvent = self.mouse_move_event
        self.background_frame.mouseReleaseEvent = self.mouse_release_event
        self.background_frame.contextMenuEvent = self.context_menu_event
        
    def setup_tray_icon(self):
        """设置系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # 尝试加载自定义图标
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # 回退到系统默认图标
            self.tray_icon.setIcon(self.style().standardIcon(QApplication.style().SP_ComputerIcon))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 选择应用程序
        select_apps_action = tray_menu.addAction(tr("menu.select_apps"))
        select_apps_action.triggered.connect(self.select_applications)
        
        # 程序管理
        manage_programs_action = tray_menu.addAction(tr("menu.manage_programs"))
        manage_programs_action.triggered.connect(self.manage_programs)
        
        # 设置
        settings_action = tray_menu.addAction(tr("menu.settings"))
        settings_action.triggered.connect(self.show_settings)
        
        # 提醒历史
        history_action = tray_menu.addAction(tr("menu.history"))
        history_action.triggered.connect(self.show_history)
        
        # 聚焦时自动保存
        self.auto_save_action = tray_menu.addAction(tr("menu.auto_save"))
        self.auto_save_action.setCheckable(True)
        self.auto_save_action.setChecked(self.remind_config.focus_auto_save_enabled)
        self.auto_save_action.triggered.connect(self.toggle_auto_save)
        
        # 整点提醒
        self.hourly_remind_action = tray_menu.addAction(tr("menu.hourly_remind"))
        self.hourly_remind_action.setCheckable(True)
        self.hourly_remind_action.setChecked(self.remind_config.hourly_remind_enabled)
        self.hourly_remind_action.triggered.connect(self.toggle_hourly_remind)
        
        tray_menu.addSeparator()
        
        # 检查更新
        check_update_action = tray_menu.addAction(tr("menu.check_update"))
        check_update_action.triggered.connect(self.check_for_updates)
        
        # 关于
        about_action = tray_menu.addAction(tr("menu.about"))
        about_action.triggered.connect(self.show_about)
        
        # 退出
        quit_action = tray_menu.addAction(tr("menu.quit"))
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
    def mouse_press_event(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouse_move_event(self, event):
        """鼠标移动事件"""
        if event.buttons() == Qt.LeftButton and self.is_dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            
    def mouse_release_event(self, event):
        """鼠标释放事件"""
        self.is_dragging = False
        event.accept()
        
    def context_menu_event(self, event):
        """右键菜单事件"""
        menu = QMenu(self)
        
        select_apps_action = menu.addAction(tr("menu.select_apps"))
        select_apps_action.triggered.connect(self.select_applications)
        
        manage_programs_action = menu.addAction(tr("menu.manage_programs"))
        manage_programs_action.triggered.connect(self.manage_programs)
        
        settings_action = menu.addAction(tr("menu.settings"))
        settings_action.triggered.connect(self.show_settings)
        
        history_action = menu.addAction(tr("menu.history"))
        history_action.triggered.connect(self.show_history)
        
        menu.addSeparator()
        
        # 自动保存
        auto_save_action = menu.addAction(tr("menu.auto_save"))
        auto_save_action.setCheckable(True)
        auto_save_action.setChecked(self.remind_config.focus_auto_save_enabled)
        auto_save_action.triggered.connect(self.toggle_auto_save)
        
        # 整点提醒
        hourly_remind_action = menu.addAction(tr("menu.hourly_remind"))
        hourly_remind_action.setCheckable(True)
        hourly_remind_action.setChecked(self.remind_config.hourly_remind_enabled)
        hourly_remind_action.triggered.connect(self.toggle_hourly_remind)
        
        menu.addSeparator()
        
        # 检查更新
        check_update_action = menu.addAction(tr("menu.check_update"))
        check_update_action.triggered.connect(self.check_for_updates)
        
        about_action = menu.addAction(tr("menu.about"))
        about_action.triggered.connect(self.show_about)
        
        quit_action = menu.addAction(tr("menu.quit"))
        quit_action.triggered.connect(self.quit_application)
        
        menu.exec_(event.globalPos())
        
    def tray_icon_activated(self, reason):
        """托盘图标点击事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            
    def select_applications(self):
        """选择应用程序"""
        dialog = AppSelectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            selected_apps = dialog.get_selected_apps()
            if selected_apps:
                # 提取程序名（去掉.exe扩展名）
                self.target_programs = [app.replace('.exe', '') for app in selected_apps]
                self.start_monitoring()
                self.update_program_count()
                self.save_settings()
                
                # 显示气泡提示
                if self.bubble_tooltip:
                    message = f"已选择 {len(selected_apps)} 个应用程序进行监控"
                    self.bubble_tooltip.show_bubble(message, 3000)
    
    def manage_programs(self):
        """管理程序对话框"""
        dialog = ProgramManagerDialog(self.target_programs, self)
        if dialog.exec_() == QDialog.Accepted:
            self.target_programs = dialog.get_programs()
            self.start_monitoring()
            self.update_program_count()
            self.save_settings()
            
    def show_settings(self):
        """显示设置对话框"""
        dialog = AdvancedSettingsDialog(self.remind_config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.remind_config = dialog.get_config()
            self.save_settings()
    
    def show_history(self):
        """显示提醒历史"""
        dialog = HistoryDialog(self.remind_history, self)
        dialog.exec_()
            
    def start_monitoring(self):
        """开始监控"""
        if not self.target_programs:
            return
            
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            
        self.monitor_thread = ProgramMonitorThread(self.target_programs)
        self.monitor_thread.program_started.connect(self.on_program_started)
        self.monitor_thread.program_stopped.connect(self.on_program_stopped)
        self.monitor_thread.start()
        
    def on_program_started(self, program_name: str, pid: str):
        """程序启动处理"""
        self.status_label.setText(f"{tr('main_window.monitoring')}: {program_name}")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #90EE90;
                font-size: 10px;
            }
        """)
        
        # 更新程序计数显示
        self.update_program_count()
        
        # 显示欢迎消息
        if self.remind_config.welcome_message_enabled:
            self.show_welcome_message(program_name)
        
        # 启动保存计时器
        if program_name not in self.save_timers:
            timer = QTimer()
            timer.timeout.connect(lambda: self.remind_save(program_name))
            
            # 根据程序类型调整提醒间隔
            interval = self.get_remind_interval_for_program(program_name)
            timer.start(interval * 1000)  # 转换为毫秒
            self.save_timers[program_name] = timer
            
    def on_program_stopped(self, program_name: str):
        """程序停止处理"""
        # 停止保存计时器
        if program_name in self.save_timers:
            self.save_timers[program_name].stop()
            del self.save_timers[program_name]
        
        # 更新程序计数显示
        self.update_program_count()
            
        if not self.save_timers:
            self.status_label.setText(tr("main_window.waiting"))
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #FFB6C1;
                    font-size: 10px;
                }
            """)
            
    def remind_save(self, program_name: str):
        """提醒保存"""
        # 记录提醒历史
        self.remind_history.add_record(program_name, "保存提醒", datetime.now())
        
        # 获取提醒消息
        message = self.get_remind_message_for_program(program_name)
        
        # 播放声音提醒
        if self.remind_config.sound_enabled:
            self.play_remind_sound()
        
        # 如果启用聚焦时自动保存，检查当前聚焦状态并处理
        if self.remind_config.focus_auto_save_enabled and self.auto_save_manager:
            # 检查当前是否聚焦在目标程序
            if self.auto_save_manager.is_currently_focused(program_name):
                # 如果当前聚焦在目标程序，立即执行自动保存
                print(f"[OK] 当前聚焦在 {program_name}，立即执行自动保存")
                self.auto_save_manager.perform_auto_save(program_name)
            else:
                # 如果未聚焦在目标程序，添加到等待列表
                print(f"[WARNING] 当前未聚焦在 {program_name}，等待聚焦时自动保存")
                self.auto_save_manager.add_pending_save(program_name)
        
        # 显示气泡提醒
        if self.bubble_tooltip:
            interval_minutes = self.remind_config.interval_seconds // 60
            bubble_message = f"程序 '{program_name}' 已运行超过 {interval_minutes} 分钟\n{message}"
            duration = self.remind_config.bubble_duration
            # 始终显示立即保存按钮，与聚焦时自动保存功能独立
            self.bubble_tooltip.show_bubble(bubble_message, duration, program_name, True)
    
    def on_auto_save_from_bubble(self, program_name: str):
        """从气泡执行自动保存"""
        if self.auto_save_manager:
            self.auto_save_manager.perform_auto_save(program_name)
    
    def check_focus_and_save(self):
        """检查聚焦状态并执行自动保存"""
        if self.auto_save_manager:
            self.auto_save_manager.check_and_save()
    
    def check_running_programs_on_startup(self):
        """启动时检测已运行的程序"""
        if not self.target_programs:
            print("[WARNING] 没有设置目标程序，跳过检测")
            return
        
        print("检测已运行的程序...")
        print(f"目标程序: {self.target_programs}")
        
        # 使用与监控线程相同的逻辑检测程序
        found_programs = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_info = proc.info
                    if proc_info['name']:
                        proc_name = proc_info['name'].lower()
                        proc_name_no_ext = proc_name.replace('.exe', '')
                        
                        # 检查是否为目标程序
                        for target in self.target_programs:
                            target_lower = target.lower()
                            target_no_ext = target_lower.replace('.exe', '')
                            
                            # 使用与监控线程相同的匹配逻辑
                            if (target_lower == proc_name or 
                                target_lower == proc_name_no_ext or
                                target_no_ext == proc_name or
                                target_no_ext == proc_name_no_ext or
                                (target_lower in proc_name and len(target_lower) > 3) or
                                (proc_name in target_lower and len(proc_name) > 3)):
                                if target_lower not in found_programs:
                                    found_programs.append(target_lower)
                                    print(f"发现已运行程序: {target_lower} (PID: {proc_info['pid']})")
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            print(f"检测运行程序时出错: {e}")
        
        print(f"共发现 {len(found_programs)} 个已运行的程序")
        
        if found_programs:
            # 更新UI状态
            self.status_label.setText(f"监控: {found_programs[0]}")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #90EE90;
                    font-size: 10px;
                }
            """)
            # 更新程序计数显示
            self.update_program_count()
            # 启动监控
            self.start_monitoring()
            # 显示欢迎消息
            if self.remind_config.welcome_message_enabled:
                self.show_startup_welcome_message(found_programs)
        else:
            print("没有发现已运行的目标程序")
            # 更新UI状态为等待程序
            self.status_label.setText("等待程序...")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #FFB6C1;
                    font-size: 10px;
                }
            """)
            # 即使没有发现程序，也要启动监控线程以检测后续启动的程序
            self.start_monitoring()
    
    
    def show_startup_welcome_message(self, programs):
        """显示启动时的欢迎消息"""
        if not programs:
            return
        
        if len(programs) == 1:
            message = f"检测到已打开 {programs[0]} 程序，请记得及时保存劳动成果！"
        else:
            program_list = "、".join(programs)
            message = f"检测到已打开 {program_list} 等程序，请记得及时保存劳动成果！"
        
        # 使用气泡显示欢迎消息
        if self.bubble_tooltip:
            self.bubble_tooltip.show_bubble(message, 4000)  # 显示4秒
    
    def get_remind_interval_for_program(self, program_name: str) -> int:
        """获取提醒间隔（秒）"""
        return self.remind_config.interval_seconds
    
    def get_remind_message_for_program(self, program_name: str) -> str:
        """根据程序类型获取提醒消息"""
        program_lower = program_name.lower()
        
        if any(editor in program_lower for editor in ['code', 'notepad++', 'sublime', 'atom']):
            return self.remind_config.remind_messages.get('code', self.remind_config.remind_messages['default'])
        elif any(tool in program_lower for tool in ['photoshop', 'illustrator', 'figma', 'sketch']):
            return self.remind_config.remind_messages.get('design', self.remind_config.remind_messages['default'])
        elif any(app in program_lower for app in ['word', 'excel', 'powerpoint']):
            return self.remind_config.remind_messages.get('document', self.remind_config.remind_messages['default'])
        else:
            return self.remind_config.remind_messages['default']
    
    def play_remind_sound(self):
        """播放提醒声音"""
        try:
            if sys.platform == "win32" and HAS_WINSOUND:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            elif HAS_PYGAME:
                # 使用pygame播放系统声音
                pygame.mixer.music.load("data/remind.wav")  # 需要提供声音文件
                pygame.mixer.music.play()
            else:
                # 使用Qt的系统声音
                QApplication.beep()
        except Exception as e:
            print(f"播放声音失败: {e}")
        
    def update_program_count(self):
        """更新程序数量显示"""
        # 计算当前运行的目标程序数量
        running_count = 0
        if hasattr(self, 'monitor_thread') and self.monitor_thread:
            running_count = len(self.monitor_thread.running_programs)
        
        self.program_count_label.setText(f"{tr('main_window.programs')}: {running_count}/{len(self.target_programs)}")
    
    def show_welcome_message(self, program_name: str):
        """显示程序打开欢迎消息"""
        message = self.remind_config.remind_messages.get('welcome', '').format(program=program_name)
        
        # 使用气泡显示欢迎消息
        if self.bubble_tooltip:
            self.bubble_tooltip.show_bubble(message, 3000)  # 显示3秒
    
    def on_hourly_remind(self, message: str):
        """整点提醒处理"""
        if self.remind_config.hourly_remind_enabled:
            # 记录提醒历史
            self.remind_history.add_record("系统", "整点提醒", datetime.now())
            
            # 播放声音
            if self.remind_config.sound_enabled:
                self.play_remind_sound()
            
            # 显示气泡提醒
            if self.bubble_tooltip:
                self.bubble_tooltip.show_bubble(message, 4000)  # 显示4秒
    
    def toggle_auto_save(self):
        """切换聚焦时自动保存状态"""
        self.remind_config.focus_auto_save_enabled = not self.remind_config.focus_auto_save_enabled
        self.auto_save_action.setChecked(self.remind_config.focus_auto_save_enabled)
        
        if self.auto_save_manager:
            self.auto_save_manager.enable_auto_save(self.remind_config.focus_auto_save_enabled)
        
        # 控制聚焦检查定时器
        if hasattr(self, 'focus_timer'):
            if self.remind_config.focus_auto_save_enabled:
                self.focus_timer.start(2000)  # 启动定时器
            else:
                self.focus_timer.stop()  # 停止定时器
        
        self.save_settings()
        
        status = "启用" if self.remind_config.focus_auto_save_enabled else "禁用"
    
    def toggle_hourly_remind(self):
        """切换整点提醒状态"""
        self.remind_config.hourly_remind_enabled = not self.remind_config.hourly_remind_enabled
        self.hourly_remind_action.setChecked(self.remind_config.hourly_remind_enabled)
        
        if self.remind_config.hourly_remind_enabled:
            if not self.hourly_reminder:
                self.hourly_reminder = HourlyReminder()
                self.hourly_reminder.remind_signal.connect(self.on_hourly_remind)
                self.hourly_reminder.start()
        else:
            if self.hourly_reminder and self.hourly_reminder.isRunning():
                self.hourly_reminder.stop()
                # 不等待，避免卡死
                self.hourly_reminder = None
        
        self.save_settings()
        
        status = "启用" if self.remind_config.hourly_remind_enabled else "禁用"
    
    def load_settings(self):
        """加载设置"""
        # 加载程序列表
        programs = self.settings.value("target_programs", [])
        if programs:
            self.target_programs = programs
        
        # 加载提醒配置
        config_data = self.settings.value("remind_config", {})
        if config_data:
            self.remind_config.from_dict(config_data)
    
    def save_settings(self):
        """保存设置"""
        # 保存程序列表
        self.settings.setValue("target_programs", self.target_programs)
        
        # 保存提醒配置
        self.settings.setValue("remind_config", self.remind_config.to_dict())
        self.settings.sync()
        
        # 自动同步设置
        self.sync_settings()
    
    def sync_settings(self):
        """同步设置到各个组件"""
        try:
            # 同步自动保存设置
            if hasattr(self, 'auto_save_manager') and self.auto_save_manager:
                self.auto_save_manager.enable_auto_save(self.remind_config.focus_auto_save_enabled)
            
            # 同步聚焦检查定时器
            if hasattr(self, 'focus_timer'):
                if self.remind_config.focus_auto_save_enabled:
                    if not self.focus_timer.isActive():
                        self.focus_timer.start(2000)  # 启动定时器
                else:
                    if self.focus_timer.isActive():
                        self.focus_timer.stop()  # 停止定时器
            
            # 同步整点提醒
            if self.remind_config.hourly_remind_enabled:
                if not self.hourly_reminder or not self.hourly_reminder.isRunning():
                    if self.hourly_reminder:
                        self.hourly_reminder.stop()
                    self.hourly_reminder = HourlyReminder()
                    self.hourly_reminder.remind_signal.connect(self.on_hourly_remind)
                    self.hourly_reminder.start()
            else:
                if self.hourly_reminder and self.hourly_reminder.isRunning():
                    self.hourly_reminder.stop()
                    self.hourly_reminder = None
            
            # 同步托盘菜单状态
            if hasattr(self, 'auto_save_action'):
                self.auto_save_action.setChecked(self.remind_config.focus_auto_save_enabled)
            if hasattr(self, 'hourly_remind_action'):
                self.hourly_remind_action.setChecked(self.remind_config.hourly_remind_enabled)
            
            print("[OK] 设置已自动同步到各个组件")
            
        except Exception as e:
            print(f"[WARNING] 设置同步时出现错误: {e}")
    
    def check_for_updates(self):
        """检查更新 - 直接跳转到GitHub Release页面"""
        import webbrowser
        
        try:
            # 直接打开GitHub Release页面
            webbrowser.open(GITHUB_URL + "/releases")
            QMessageBox.information(
                self, 
                tr("update.title"), 
                tr("update.opened_release_page")
            )
        except Exception as e:
            QMessageBox.warning(
                self, 
                tr("update.open_failed"), 
                f"{tr('update.open_failed_msg')}: {e}"
            )
    
    def on_update_found(self, update_info: dict):
        """发现更新"""
        dialog = UpdateDialog(update_info, self)
        dialog.exec_()
    
    def on_update_check_completed(self, success: bool, message: str):
        """更新检查完成"""
        if success:
            QMessageBox.information(self, tr("update.check_completed"), message)
        else:
            QMessageBox.warning(self, tr("update.check_failed"), message)
    
    def show_about(self):
        """显示关于对话框"""
        about_text = f"""
        <div style="text-align: center;">
            <h2 style="color: #0078d4; margin-bottom: 10px;">SaveGuard v{VERSION}</h2>
            <p style="font-size: 14px; color: #666; margin-bottom: 20px;">跨平台程序保存提醒工具</p>
        </div>
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h3 style="color: #333; margin-top: 0;">🎯 主要功能</h3>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li>🔍 <b>程序监控</b> - 实时监控指定程序运行状态</li>
                <li>⏰ <b>定时提醒</b> - 程序运行超时后智能提醒保存</li>
                <li>💬 <b>气泡提醒</b> - 优雅的气泡提示界面</li>
                <li>💾 <b>聚焦保存</b> - 用户回到程序时自动执行Ctrl+S</li>
                <li>🕐 <b>整点提醒</b> - 每小时整点自动提醒</li>
                <li>📊 <b>提醒历史</b> - 记录和查看提醒历史</li>
                <li>🎛️ <b>应用选择</b> - 预置常见应用程序列表</li>
                <li>🔍 <b>启动检测</b> - 软件启动时检测已运行程序</li>
            </ul>
        </div>
        
        <div style="background-color: #e8f4fd; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h3 style="color: #0078d4; margin-top: 0;">⚙️ 技术特性</h3>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li>🖥️ <b>跨平台</b> - 支持 Windows 和 macOS</li>
                <li>⚡ <b>高性能</b> - 异步加载，不阻塞界面</li>
                <li>🔧 <b>易配置</b> - 丰富的自定义选项</li>
                <li>💾 <b>持久化</b> - 自动保存用户设置</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 20px 0;">
            <p style="margin: 5px 0;"><b>📁 项目地址</b></p>
            <p style="margin: 5px 0;"><a href="{GITHUB_URL}" style="color: #0078d4; text-decoration: none;">{GITHUB_URL}</a></p>
            <p style="margin: 5px 0; color: #666; font-size: 12px;">© 2025 SaveGuard. All rights reserved.</p>
        </div>
        """
        
        msg = QMessageBox()
        msg.setWindowTitle("关于 SaveGuard")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setIcon(QMessageBox.Information)
        
        # 添加检查更新按钮
        check_update_btn = msg.addButton("检查更新", QMessageBox.ActionRole)
        msg.addButton(QMessageBox.Ok)
        
        result = msg.exec_()
        
        # 处理检查更新按钮点击
        if msg.clickedButton() == check_update_btn:
            self.check_for_updates()
    
    def on_language_changed(self, language_code: str):
        """语言切换处理"""
        # 更新配置中的语言
        self.remind_config.language = language_code
        
        # 重新加载提醒消息
        self.remind_config.remind_messages = {
            "default": tr("messages.default"),
            "code": tr("messages.code"),
            "document": tr("messages.document"),
            "design": tr("messages.design"),
            "welcome": tr("messages.welcome"),
            "hourly": tr("messages.hourly")
        }
        
        # 更新UI文本
        self.title_label.setText(tr("main_window.title"))
        self.status_label.setText(tr("main_window.monitoring"))
        self.update_program_count()
        
        # 更新气泡提示
        if self.bubble_tooltip:
            self.bubble_tooltip.title_label.setText(tr("bubble.title"))
            self.bubble_tooltip.auto_save_btn.setText(tr("bubble.save_now"))
        
        # 更新托盘菜单
        self.setup_tray_icon()
        
        # 保存设置
        self.save_settings()
    
    def quit_application(self):
        """退出应用"""
        print(f"正在退出SaveGuard v{VERSION}...")
        
        # 停止程序监控线程
        if self.monitor_thread and self.monitor_thread.isRunning():
            print("停止程序监控线程...")
            self.monitor_thread.stop()
            # 不等待，避免卡死
        
        # 停止整点提醒线程
        if self.hourly_reminder and self.hourly_reminder.isRunning():
            print("停止整点提醒线程...")
            self.hourly_reminder.stop()
            # 不等待，避免卡死
        
        # 停止聚焦检查定时器
        if hasattr(self, 'focus_timer') and self.focus_timer:
            print("停止聚焦检查定时器...")
            self.focus_timer.stop()
        
        # 停止所有计时器
        for timer in self.save_timers.values():
            if timer.isActive():
                timer.stop()
        
        print("退出完成")
        QApplication.quit()


class ProgramManagerDialog(QDialog):
    """程序管理对话框"""
    
    def __init__(self, programs: List[str], parent=None):
        super().__init__(parent)
        self.programs = programs.copy()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(tr("program_manager.title"))
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        
        # 程序列表
        self.program_list = QListWidget()
        for program in self.programs:
            self.program_list.addItem(program)
        layout.addWidget(QLabel(tr("program_manager.program_list") + ":"))
        layout.addWidget(self.program_list)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton(tr("program_manager.add_program"))
        add_btn.clicked.connect(self.add_program)
        
        remove_btn = QPushButton(tr("program_manager.remove_program"))
        remove_btn.clicked.connect(self.remove_program)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 确定/取消按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def add_program(self):
        program_name, ok = QInputDialog.getText(self, tr("program_manager.add_program"), tr("program_manager.program_name") + ":")
        if ok and program_name and program_name.lower() not in self.programs:
            self.programs.append(program_name.lower())
            self.program_list.addItem(program_name.lower())
    
    def remove_program(self):
        current_item = self.program_list.currentItem()
        if current_item:
            self.programs.remove(current_item.text())
            self.program_list.takeItem(self.program_list.row(current_item))
    
    def get_programs(self) -> List[str]:
        return self.programs


class AdvancedSettingsDialog(QDialog):
    """高级设置对话框"""
    
    def __init__(self, config: RemindConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(tr("settings.title"))
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 基本设置选项卡
        basic_tab = QWidget()
        basic_layout = QFormLayout()
        
        # 语言选择
        self.language_combo = QComboBox()
        lang_manager = get_language_manager()
        for lang_code, lang_name in lang_manager.get_supported_languages().items():
            self.language_combo.addItem(lang_name, lang_code)
        # 设置当前语言
        current_lang = getattr(self.config, 'language', 'zh_CN')
        index = self.language_combo.findData(current_lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        basic_layout.addRow(tr("settings.language") + ":", self.language_combo)
        
        # 提醒间隔（秒）
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 3600)  # 10秒到60分钟
        self.interval_spin.setValue(self.config.interval_seconds)
        self.interval_spin.setSuffix(" 秒")
        basic_layout.addRow(tr("settings.remind_interval") + ":", self.interval_spin)
        
        # 间隔说明标签
        interval_label = QLabel("(10秒-60分钟，建议300秒=5分钟)")
        interval_label.setStyleSheet("color: gray; font-size: 9px;")
        basic_layout.addRow("", interval_label)
        
        # 气泡显示时长
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1000, 10000)  # 1-10秒
        self.duration_spin.setValue(self.config.bubble_duration)
        self.duration_spin.setSuffix(" 毫秒")
        basic_layout.addRow(tr("settings.bubble_duration") + ":", self.duration_spin)
        
        # 提醒频率（固定为重复提醒）
        frequency_label = QLabel("重复提醒")
        frequency_label.setStyleSheet("font-size: 12px; color: #666;")
        basic_layout.addRow(tr("settings.remind_frequency") + ":", frequency_label)
        
        # 复选框
        self.sound_check = QCheckBox(tr("settings.sound_enabled"))
        self.sound_check.setChecked(self.config.sound_enabled)
        basic_layout.addRow(self.sound_check)
        
        
        # 聚焦时自动保存
        self.auto_save_check = QCheckBox(tr("settings.focus_auto_save_enabled"))
        self.auto_save_check.setChecked(self.config.focus_auto_save_enabled)
        basic_layout.addRow(self.auto_save_check)
        
        # 整点提醒
        self.hourly_remind_check = QCheckBox(tr("settings.hourly_remind_enabled"))
        self.hourly_remind_check.setChecked(self.config.hourly_remind_enabled)
        basic_layout.addRow(self.hourly_remind_check)
        
        # 欢迎消息
        self.welcome_msg_check = QCheckBox(tr("settings.welcome_message_enabled"))
        self.welcome_msg_check.setChecked(self.config.welcome_message_enabled)
        basic_layout.addRow(self.welcome_msg_check)
        
        # 自动选择应用程序
        self.auto_select_check = QCheckBox(tr("settings.auto_select_apps"))
        self.auto_select_check.setChecked(self.config.auto_select_apps)
        basic_layout.addRow(self.auto_select_check)
        
        basic_tab.setLayout(basic_layout)
        tab_widget.addTab(basic_tab, tr("settings.basic_settings"))
        
        # 消息设置选项卡
        message_tab = QWidget()
        message_layout = QFormLayout()
        
        # 自定义消息
        self.default_msg = QLineEdit(self.config.remind_messages.get('default', ''))
        message_layout.addRow(tr("settings.default_message") + ":", self.default_msg)
        
        self.code_msg = QLineEdit(self.config.remind_messages.get('code', ''))
        message_layout.addRow(tr("settings.code_message") + ":", self.code_msg)
        
        self.document_msg = QLineEdit(self.config.remind_messages.get('document', ''))
        message_layout.addRow(tr("settings.document_message") + ":", self.document_msg)
        
        self.design_msg = QLineEdit(self.config.remind_messages.get('design', ''))
        message_layout.addRow(tr("settings.design_message") + ":", self.design_msg)
        
        self.welcome_msg = QLineEdit(self.config.remind_messages.get('welcome', ''))
        message_layout.addRow(tr("settings.welcome_message") + ":", self.welcome_msg)
        
        self.hourly_msg = QLineEdit(self.config.remind_messages.get('hourly', ''))
        message_layout.addRow(tr("settings.hourly_message") + ":", self.hourly_msg)
        
        message_tab.setLayout(message_layout)
        tab_widget.addTab(message_tab, tr("settings.message_settings"))
        
        layout.addWidget(tab_widget)
        
        # 确定/取消按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_config(self) -> RemindConfig:
        """获取配置"""
        # 获取语言设置
        selected_lang = self.language_combo.currentData()
        if selected_lang and selected_lang != self.config.language:
            # 语言发生变化，更新语言管理器
            lang_manager = get_language_manager()
            lang_manager.set_language(selected_lang)
            self.config.language = selected_lang
        
        self.config.interval_seconds = self.interval_spin.value()
        self.config.bubble_duration = self.duration_spin.value()
        
        # 提醒频率固定为重复提醒
        self.config.remind_frequency = "repeat"
        
        self.config.sound_enabled = self.sound_check.isChecked()
        self.config.focus_auto_save_enabled = self.auto_save_check.isChecked()
        self.config.hourly_remind_enabled = self.hourly_remind_check.isChecked()
        self.config.welcome_message_enabled = self.welcome_msg_check.isChecked()
        self.config.auto_select_apps = self.auto_select_check.isChecked()
        
        self.config.remind_messages = {
            'default': self.default_msg.text(),
            'code': self.code_msg.text(),
            'document': self.document_msg.text(),
            'design': self.design_msg.text(),
            'welcome': self.welcome_msg.text(),
            'hourly': self.hourly_msg.text()
        }
        
        return self.config


class HistoryDialog(QDialog):
    """提醒历史对话框"""
    
    def __init__(self, history: RemindHistory, parent=None):
        super().__init__(parent)
        self.history = history
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(tr("history.title"))
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # 历史列表
        self.history_list = QListWidget()
        records = self.history.get_recent_records(50)
        for record in records:
            item_text = f"{record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {record['message']}"
            self.history_list.addItem(item_text)
        
        layout.addWidget(QLabel(tr("history.recent_records") + ":"))
        layout.addWidget(self.history_list)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton(tr("history.clear_history"))
        clear_btn.clicked.connect(self.clear_history)
        
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        
        close_btn = QPushButton(tr("history.close"))
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def clear_history(self):
        self.history.history.clear()
        self.history_list.clear()


class AppSelectionDialog(QDialog):
    """应用程序选择对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("app_selection.title"))
        self.setModal(True)
        self.resize(600, 500)
        
        self.selected_apps = []
        self.common_apps = [
            'notepad.exe', 'notepad++.exe', 'code.exe', 'sublime_text.exe',
            'atom.exe', 'vim.exe', 'emacs.exe', 'chrome.exe', 'firefox.exe',
            'edge.exe', 'photoshop.exe', 'illustrator.exe', 'figma.exe',
            'sketch.exe', 'blender.exe', 'word.exe', 'excel.exe', 'powerpoint.exe',
            'wps.exe', 'typora.exe', 'obsidian.exe', 'vscode.exe', 'idea64.exe',
            'pycharm64.exe', 'webstorm64.exe', 'clion64.exe', 'rider64.exe'
        ]
        self.init_ui()
        self.load_running_apps_async()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 说明标签
        info_label = QLabel(tr("app_selection.select_apps") + ":")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(info_label)
        
        # 加载进度标签
        self.loading_label = QLabel(tr("app_selection.loading"))
        self.loading_label.setStyleSheet("font-size: 12px; color: #666; padding: 5px;")
        self.loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.loading_label)
        
        # 应用程序列表
        self.app_list = QListWidget()
        self.app_list.setStyleSheet("""
            QListWidget {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
        self.app_list.setSelectionMode(QListWidget.MultiSelection)
        self.app_list.hide()  # 初始隐藏，加载完成后显示
        layout.addWidget(self.app_list)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 刷新按钮
        refresh_btn = QPushButton(tr("app_selection.refresh"))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_apps)
        
        # 全选按钮
        select_all_btn = QPushButton(tr("app_selection.select_all"))
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        select_all_btn.clicked.connect(self.select_all)
        
        # 清空选择按钮
        clear_btn = QPushButton(tr("app_selection.clear_selection"))
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        clear_btn.clicked.connect(self.clear_selection)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 确定/取消按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_running_apps_async(self):
        """异步加载正在运行的应用程序"""
        # 使用QTimer延迟执行，避免阻塞UI
        QTimer.singleShot(100, self.load_running_apps)
    
    def load_running_apps(self):
        """加载正在运行的应用程序"""
        self.app_list.clear()
        
        try:
            # 先添加常见应用程序（无论是否运行）
            for app in self.common_apps:
                item = QListWidgetItem(f"📱 {app}")
                item.setData(Qt.UserRole, app)
                self.app_list.addItem(item)
            
            # 异步检查哪些应用程序正在运行
            QTimer.singleShot(50, self.check_running_apps)
            
        except Exception as e:
            print(f"[ERROR] 加载应用程序列表失败: {e}")
            self.loading_label.setText("加载失败，请重试")
    
    def check_running_apps(self):
        """检查哪些应用程序正在运行"""
        try:
            # 获取当前运行的进程（只检查进程名）
            running_processes = set()
            for proc in psutil.process_iter(['name']):
                try:
                    proc_info = proc.info
                    if proc_info['name']:
                        running_processes.add(proc_info['name'].lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 标记正在运行的应用程序
            for i in range(self.app_list.count()):
                item = self.app_list.item(i)
                app_name = item.data(Qt.UserRole)
                if app_name in running_processes:
                    item.setText(f"🟢 {app_name} ({tr('app_selection.running')})")
                    item.setBackground(QColor(240, 248, 255))  # 浅蓝色背景
                else:
                    item.setText(f"⚪ {app_name} ({tr('app_selection.not_running')})")
                    item.setBackground(QColor(255, 255, 255))  # 白色背景
            
            # 隐藏加载提示，显示列表
            self.loading_label.hide()
            self.app_list.show()
            
            print(f"[OK] 加载完成，找到 {len(running_processes)} 个运行中的进程")
            
        except Exception as e:
            print(f"[ERROR] 检查运行状态失败: {e}")
            self.loading_label.setText("检查运行状态失败")
    
    def select_all(self):
        """全选"""
        for i in range(self.app_list.count()):
            self.app_list.item(i).setSelected(True)
    
    def clear_selection(self):
        """清空选择"""
        self.app_list.clearSelection()
    
    def refresh_apps(self):
        """刷新应用程序列表"""
        self.loading_label.setText(tr("app_selection.loading"))
        self.loading_label.show()
        self.app_list.hide()
        self.load_running_apps_async()
    
    def get_selected_apps(self):
        """获取选中的应用程序"""
        selected = []
        for item in self.app_list.selectedItems():
            app_name = item.data(Qt.UserRole)
            if app_name:
                selected.append(app_name)
        return selected


class SaveGuardApp(QApplication):
    """主应用程序"""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出应用
        
        # 设置应用信息
        self.setApplicationName("SaveGuard")
        self.setApplicationVersion("1.0.0")
        
        # 创建主窗口
        self.main_widget = SaveGuardWidget()
        self.main_widget.show()
        
        print(f"SaveGuard v{VERSION} 已启动")
        print("右键点击浮窗或系统托盘图标来管理程序")
        print(f"项目地址: {GITHUB_URL}")


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n收到信号 {signum}，正在强制退出...")
    sys.exit(0)

def main():
    """主函数"""
    # 检查依赖
    if not HAS_PYNPUT:
        print("[WARNING] 警告: pynput未安装，自动保存功能将不可用")
        print("请运行: pip install pynput")
    
    if not HAS_WINSOUND and not HAS_PYGAME:
        print("[WARNING] 警告: 声音模块未安装，声音提醒功能将不可用")
        print("请运行: pip install pygame")
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        app = SaveGuardApp(sys.argv)
        
        # 设置应用图标
        icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        
        # 运行应用
        result = app.exec_()
        print("应用程序正常退出")
        return result
        
    except KeyboardInterrupt:
        print("程序被用户中断")
        return 0
    except Exception as e:
        print(f"程序运行出错: {e}")
        return 1


if __name__ == "__main__":
    main()

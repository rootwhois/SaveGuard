#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SaveGuard 多语言支持管理器
Language Manager for SaveGuard
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QSettings


class LanguageManager(QObject):
    """多语言管理器"""
    
    # 语言切换信号
    language_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.current_language = "zh_CN"  # 默认中文
        self.translations = {}
        self.settings = QSettings("SaveGuard", "SaveGuard")
        
        # 支持的语言列表
        self.supported_languages = {
            "zh_CN": "简体中文",
            "en_US": "English",
            "ja_JP": "日本語",
            "ko_KR": "한국어",
        }
        
        # 加载保存的语言设置
        self.load_language_setting()
        
        # 加载当前语言的翻译
        self.load_language(self.current_language)
    
    def load_language_setting(self):
        """加载保存的语言设置"""
        saved_language = self.settings.value("language", "zh_CN")
        if saved_language in self.supported_languages:
            self.current_language = saved_language
    
    def save_language_setting(self):
        """保存语言设置"""
        self.settings.setValue("language", self.current_language)
        self.settings.sync()
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.supported_languages.copy()
    
    def get_current_language(self) -> str:
        """获取当前语言"""
        return self.current_language
    
    def set_language(self, language_code: str) -> bool:
        """设置语言"""
        if language_code not in self.supported_languages:
            return False
        
        if self.current_language != language_code:
            self.current_language = language_code
            self.load_language(language_code)
            self.save_language_setting()
            self.language_changed.emit(language_code)
        return True
    
    def load_language(self, language_code: str):
        """加载指定语言的翻译"""
        try:
            # 获取语言文件路径
            lang_file = self.get_language_file_path(language_code)
            
            if os.path.exists(lang_file):
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations[language_code] = json.load(f)
            else:
                # 如果语言文件不存在，使用中文作为默认语言
                print(f"⚠ 语言文件不存在: {lang_file}")
                if language_code != "zh_CN":
                    # 尝试加载中文语言文件
                    if "zh_CN" not in self.translations:
                        self.load_language("zh_CN")
                    # 如果中文翻译已存在，直接使用
                    if "zh_CN" in self.translations:
                        self.translations[language_code] = self.translations["zh_CN"]
                    else:
                        # 如果连中文都没有，使用空字典
                        self.translations[language_code] = {}
                else:
                    # 如果连中文都没有，使用空字典
                    self.translations[language_code] = {}
        except Exception as e:
            print(f"✗ 加载语言文件失败: {e}")
            # 使用空字典
            self.translations[language_code] = {}
    
    def get_language_file_path(self, language_code: str) -> str:
        """获取语言文件路径"""
        current_dir = Path(__file__).parent
        return current_dir / "languages" / f"{language_code}.json"
    
    
    def translate(self, key: str, **kwargs) -> str:
        """翻译文本"""
        try:
            # 分割键路径
            keys = key.split('.')
            value = self.translations.get(self.current_language, {})
            
            # 遍历键路径
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    # 如果找不到翻译，尝试使用中文作为默认语言
                    if self.current_language != "zh_CN":
                        value = self.translations.get("zh_CN", {})
                        for k in keys:
                            if isinstance(value, dict) and k in value:
                                value = value[k]
                            else:
                                return key  # 返回原始键
                    else:
                        return key  # 返回原始键
            
            # 格式化字符串
            if isinstance(value, str) and kwargs:
                try:
                    return value.format(**kwargs)
                except (KeyError, ValueError):
                    return value
            
            return str(value) if value is not None else key
            
        except Exception as e:
            print(f"✗ 翻译失败: {e}")
            return key
    
    def tr(self, key: str, **kwargs) -> str:
        """翻译文本的简写方法"""
        return self.translate(key, **kwargs)


# 全局语言管理器实例
_language_manager = None

def get_language_manager() -> LanguageManager:
    """获取全局语言管理器实例"""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager

def tr(key: str, **kwargs) -> str:
    """全局翻译函数"""
    return get_language_manager().tr(key, **kwargs)

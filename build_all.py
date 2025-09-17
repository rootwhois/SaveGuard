#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SaveGuard 多平台构建脚本
自动构建所有平台和架构的单一可执行文件
支持 Windows, macOS, Linux 的多种架构
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# 设置控制台编码为UTF-8，解决Windows环境下的Unicode编码问题
def setup_console_encoding():
    """设置控制台编码为UTF-8"""
    if sys.platform == "win32":
        # Windows环境下设置控制台编码
        try:
            # 尝试设置控制台代码页为UTF-8
            os.system("chcp 65001 >nul 2>&1")
            # 设置环境变量
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            # 设置标准输出编码
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        except:
            pass

# 安全打印函数，处理Unicode编码错误
def safe_print(text: str, fallback: str = None):
    """安全打印函数，处理Unicode编码错误"""
    def clean_text(text: str) -> str:
        """移除所有非ASCII字符"""
        import re
        return re.sub(r'[^\x00-\x7F]+', '', text)
    
    try:
        print(text)
    except UnicodeEncodeError:
        # 如果Unicode编码失败，使用fallback文本或移除emoji
        if fallback:
            try:
                print(fallback)
            except UnicodeEncodeError:
                # 如果fallback也失败，移除所有非ASCII字符
                print(clean_text(fallback))
        else:
            # 移除emoji和特殊字符，保留基本文本
            print(clean_text(text))

# 初始化控制台编码
setup_console_encoding()

# 构建矩阵配置
BUILD_MATRIX = {
    "windows": {
        "x64": {"arch": "x64", "ext": ".exe", "python_arch": "win_amd64"},
        "x86": {"arch": "x86", "ext": ".exe", "python_arch": "win32"},
        "arm64": {"arch": "arm64", "ext": ".exe", "python_arch": "win_arm64"}
    },
    "macos": {
        "x86_64": {"arch": "x86_64", "ext": "", "python_arch": "macosx_10_9_x86_64"},
        "arm64": {"arch": "arm64", "ext": "", "python_arch": "macosx_11_0_arm64"},
        "universal": {"arch": "universal", "ext": "", "python_arch": "universal"}
    },
    "linux": {
        "x86_64": {"arch": "x86_64", "ext": "", "python_arch": "linux_x86_64"},
        "aarch64": {"arch": "aarch64", "ext": "", "python_arch": "linux_aarch64"},
        "armv7l": {"arch": "armv7l", "ext": "", "python_arch": "linux_armv7l"}
    }
}

class BuildConfig:
    """构建配置类"""
    def __init__(self, platform_name: str, arch: str, config: Dict):
        self.platform = platform_name
        self.arch = arch
        self.ext = config["ext"]
        self.python_arch = config["python_arch"]
        self.name = f"SaveGuard-{platform_name.title()}-{arch}{self.ext}"
        
    def __str__(self):
        return f"{self.platform}-{self.arch}"

class MultiPlatformBuilder:
    """多平台构建器"""
    
    def __init__(self):
        system_name = platform.system().lower()
        # 标准化平台名称
        if system_name == "darwin":
            self.current_platform = "macos"
        else:
            self.current_platform = system_name
        self.current_arch = self._get_current_arch()
        self.build_results = []
        self.dist_dir = Path("dist")
        self.release_dir = Path("release")
        
    def _get_current_arch(self) -> str:
        """获取当前架构"""
        machine = platform.machine().lower()
        if self.current_platform == "windows":
            return "x64" if machine.endswith('64') else "x86"
        elif self.current_platform == "macos":
            return "arm64" if machine == "arm64" else "x86_64"
        elif self.current_platform == "linux":
            return "aarch64" if machine == "aarch64" else "x86_64"
        return "unknown"
    
    def _get_icon_path(self, platform_name: str) -> Optional[str]:
        """获取平台对应的图标路径"""
        icon_paths = {
            "windows": "assets/icon.ico",
            "macos": "assets/icon.icns", 
            "linux": "assets/icon.png"
        }
        
        icon_path = icon_paths.get(platform_name)
        if icon_path and os.path.exists(icon_path):
            return icon_path
        
        # 如果首选图标不存在，尝试备用图标
        fallback_paths = {
            "windows": ["assets/icons/saveguard.ico", "assets/icon.png"],
            "macos": ["assets/icon.png", "assets/icon.ico"],
            "linux": ["assets/icons/saveguard-256x256.png", "assets/icon.ico"]
        }
        
        for fallback in fallback_paths.get(platform_name, []):
            if os.path.exists(fallback):
                return fallback
        
        return None
    
    def check_python_version(self) -> bool:
        """检查Python版本"""
        if sys.version_info < (3, 7):
            safe_print("❌ 需要Python 3.7或更高版本", "[ERROR] Python 3.7 or higher required")
            safe_print(f"当前版本: {sys.version}", f"Current version: {sys.version}")
            return False
        safe_print(f"✅ Python版本检查通过: {sys.version}", f"[OK] Python version check passed: {sys.version}")
        return True
    
    def check_dependencies(self) -> bool:
        """检查构建依赖"""
        safe_print("\n📦 检查构建依赖...", "\n[INFO] Checking build dependencies...")
        
        # 检查必要文件
        required_files = ["run.py", "src/saveguard.py", "requirements.txt"]
        missing_files = [f for f in required_files if not os.path.exists(f)]
        
        if missing_files:
            safe_print(f"❌ 缺少必要文件: {', '.join(missing_files)}", f"[ERROR] Missing required files: {', '.join(missing_files)}")
            return False
        
        safe_print("✅ 必要文件检查通过", "[OK] Required files check passed")
        
        # macOS 特殊处理
        if self.current_platform == "macos":
            return self._check_macos_dependencies()
        
        # 其他平台的依赖检查
        return self._check_standard_dependencies()
    
    def _check_macos_dependencies(self) -> bool:
        """检查 macOS 依赖"""
        safe_print("🍎 检查 macOS 依赖...", "[INFO] Checking macOS dependencies...")
        
        # 检查是否有专门的 macOS 安装脚本
        if os.path.exists("install_macos_deps.py"):
            safe_print("发现 macOS 依赖安装脚本，建议先运行:", "[INFO] Found macOS dependency installer, recommend running:")
            safe_print("python install_macos_deps.py", "python install_macos_deps.py")
        
        # 检查 Homebrew
        try:
            result = subprocess.run(["brew", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                safe_print("⚠️ 未找到 Homebrew，PyQt5 安装可能失败", "[WARNING] Homebrew not found, PyQt5 installation may fail")
        except:
            safe_print("⚠️ 无法检查 Homebrew 状态", "[WARNING] Cannot check Homebrew status")
        
        # 尝试安装依赖
        try:
            safe_print("安装 macOS 依赖...", "Installing macOS dependencies...")
            
            # 设置 Qt5 环境变量
            qt_result = subprocess.run(["brew", "--prefix", "qt@5"], 
                                     capture_output=True, text=True, timeout=10)
            if qt_result.returncode == 0:
                qt_dir = qt_result.stdout.strip()
                env = os.environ.copy()
                env.update({
                    'QT_DIR': qt_dir,
                    'PATH': f"{qt_dir}/bin:{env.get('PATH', '')}",
                    'PKG_CONFIG_PATH': f"{qt_dir}/lib/pkgconfig:{env.get('PKG_CONFIG_PATH', '')}",
                    'LDFLAGS': f"-L{qt_dir}/lib",
                    'CPPFLAGS': f"-I{qt_dir}/include"
                })
            else:
                env = os.environ.copy()
            
            # 安装 PyInstaller
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "pyinstaller>=5.13.0"
            ], check=True, capture_output=True, text=True, encoding='utf-8', env=env)
            safe_print("✅ PyInstaller安装完成", "[OK] PyInstaller installation completed")
            
            # 尝试安装 PyQt5
            safe_print("安装 PyQt5...", "Installing PyQt5...")
            pyqt_result = subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "PyQt5==5.15.10", "--no-cache-dir"
            ], capture_output=True, text=True, encoding='utf-8', 
            env=env, timeout=300)
            
            if pyqt_result.returncode == 0:
                safe_print("✅ PyQt5安装完成", "[OK] PyQt5 installation completed")
            else:
                safe_print("⚠️ PyQt5安装失败，但继续构建", "[WARNING] PyQt5 installation failed, but continuing build")
                if pyqt_result.stderr:
                    safe_print(f"PyQt5错误: {pyqt_result.stderr[:200]}...", f"PyQt5 error: {pyqt_result.stderr[:200]}...")
            
            return True
            
        except subprocess.CalledProcessError as e:
            safe_print(f"❌ macOS依赖安装失败: {e}", f"[ERROR] macOS dependency installation failed: {e}")
            if e.stderr:
                safe_print(f"错误详情: {e.stderr}", f"Error details: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            safe_print("❌ macOS依赖安装超时", "[ERROR] macOS dependency installation timeout")
            return False
        except Exception as e:
            safe_print(f"❌ macOS安装过程异常: {e}", f"[ERROR] macOS installation exception: {e}")
            return False
    
    def _check_standard_dependencies(self) -> bool:
        """检查标准依赖"""
        try:
            safe_print("安装PyInstaller...", "Installing PyInstaller...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "pyinstaller>=5.13.0"
            ], check=True, capture_output=True, text=True, encoding='utf-8')
            safe_print("✅ PyInstaller安装完成", "[OK] PyInstaller installation completed")
            return True
        except subprocess.CalledProcessError as e:
            safe_print(f"❌ PyInstaller安装失败: {e}", f"[ERROR] PyInstaller installation failed: {e}")
            if e.stderr:
                safe_print(f"错误详情: {e.stderr}", f"Error details: {e.stderr}")
            return False
        except Exception as e:
            safe_print(f"❌ 安装过程异常: {e}", f"[ERROR] Installation exception: {e}")
            return False
    
    def get_build_configs(self, platforms: Optional[List[str]] = None) -> List[BuildConfig]:
        """获取构建配置列表"""
        if platforms is None:
            platforms = list(BUILD_MATRIX.keys())
        
        configs = []
        for platform_name in platforms:
            if platform_name not in BUILD_MATRIX:
                safe_print(f"⚠️ 不支持的平台: {platform_name}", f"[WARNING] Unsupported platform: {platform_name}")
                continue
                
            for arch, config in BUILD_MATRIX[platform_name].items():
                configs.append(BuildConfig(platform_name, arch, config))
        
        return configs
    
    def can_build_cross_platform(self, target_platform: str) -> bool:
        """检查是否可以交叉编译到目标平台"""
        if target_platform == self.current_platform:
            return True
        
        # 检查是否有Docker支持
        if self._check_docker_available():
            return True
        
        # 检查是否有WSL支持（Windows上）
        if self.current_platform == "windows" and target_platform == "linux":
            return self._check_wsl_available()
        
        # 检查是否有对应的Python环境或工具链
        if target_platform == "windows" and self.current_platform == "linux":
            # Linux可以交叉编译到Windows（需要wine或mingw）
            return False  # 暂时不支持
        elif target_platform == "macos" and self.current_platform != "macos":
            # 只有macOS可以构建macOS版本
            return False
        elif target_platform == "linux" and self.current_platform == "windows":
            # Windows可以交叉编译到Linux（需要WSL或Docker）
            return False  # 暂时不支持
        
        return False
    
    def get_buildable_configs(self, platforms: Optional[List[str]] = None) -> List[BuildConfig]:
        """获取可构建的配置列表（智能模式）"""
        if platforms is None:
            platforms = list(BUILD_MATRIX.keys())
        
        configs = []
        for platform_name in platforms:
            if platform_name not in BUILD_MATRIX:
                continue
                
            for arch, config in BUILD_MATRIX[platform_name].items():
                build_config = BuildConfig(platform_name, arch, config)
                
                # 检查是否可以构建
                if self.can_build_cross_platform(platform_name):
                    configs.append(build_config)
                else:
                    safe_print(f"⚠️ 跳过 {platform_name}-{arch} (无法在当前平台构建)", f"[SKIP] {platform_name}-{arch} (cannot build on current platform)")
        
        return configs
    
    def _check_docker_available(self) -> bool:
        """检查Docker是否可用"""
        try:
            result = subprocess.run(["docker", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_wsl_available(self) -> bool:
        """检查WSL是否可用（Windows上）"""
        try:
            result = subprocess.run(["wsl", "--status"], 
                                  capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, UnicodeDecodeError):
            return False
    
    def build_single_platform(self, config: BuildConfig, force: bool = False) -> bool:
        """构建单个平台"""
        safe_print(f"\n🔨 构建 {config.platform}-{config.arch}...", f"\n[BUILD] Building {config.platform}-{config.arch}...")
        
        # 检查是否已存在
        output_file = self.dist_dir / config.name
        if output_file.exists() and not force:
            size_mb = output_file.stat().st_size / (1024 * 1024)
            safe_print(f"⏭️ 跳过 {config.name} (已存在, {size_mb:.1f} MB)", f"[SKIP] {config.name} (already exists, {size_mb:.1f} MB)")
            self.build_results.append({
                "config": config,
                "file": output_file,
                "size_mb": size_mb,
                "success": True,
                "skipped": True
            })
            return True
        
        # 检查是否可以构建
        if not self.can_build_cross_platform(config.platform):
            safe_print(f"⚠️ 无法在 {self.current_platform} 上构建 {config.platform} 版本", f"[WARNING] Cannot build {config.platform} version on {self.current_platform}")
            return False
        
        # 尝试使用Docker构建
        if config.platform != self.current_platform and self._check_docker_available():
            safe_print(f"🐳 尝试使用Docker构建 {config.platform}-{config.arch}...", f"[DOCKER] Trying to build {config.platform}-{config.arch} with Docker...")
            if self._build_with_docker(config, force):
                return True
            else:
                safe_print(f"⚠️ Docker构建失败，尝试其他方法...", "[WARNING] Docker build failed, trying other methods...")
        
        # 尝试使用WSL构建（Windows上构建Linux）
        if (self.current_platform == "windows" and config.platform == "linux" and 
            self._check_wsl_available()):
            safe_print(f"🐧 尝试使用WSL构建 {config.platform}-{config.arch}...", f"[WSL] Trying to build {config.platform}-{config.arch} with WSL...")
            if self._build_with_wsl(config, force):
                return True
            else:
                safe_print(f"⚠️ WSL构建失败，尝试其他方法...", "[WARNING] WSL build failed, trying other methods...")
        
        # 如果无法交叉编译，提供友好的错误信息
        if config.platform != self.current_platform:
            safe_print(f"❌ 无法在 {self.current_platform} 上构建 {config.platform} 版本", f"[ERROR] Cannot build {config.platform} version on {self.current_platform}")
            safe_print(f"💡 建议:", "[SUGGESTION] Recommendations:")
            safe_print(f"   - 在 {config.platform} 系统上直接运行此脚本", f"   - Run this script directly on {config.platform} system")
            safe_print(f"   - 使用Docker Desktop并确保Docker服务正在运行", "   - Use Docker Desktop and ensure Docker service is running")
            safe_print(f"   - 使用虚拟机运行目标平台", "   - Use virtual machine to run target platform")
            return False
        
        # 构建参数
        args = [
            "pyinstaller",
            "--onefile",
            "--noconfirm",
            "--clean",
            "--noconsole",
            "--name", config.name,
            "--distpath", str(self.dist_dir),
            "--workpath", "build",
            "--specpath", "specs",
        ]
        
        # 添加数据文件
        if os.path.exists("src/languages"):
            languages_path = os.path.abspath("src/languages")
            args.extend(["--add-data", f"{languages_path}{os.pathsep}languages"])
        
        if os.path.exists("src"):
            src_path = os.path.abspath("src")
            args.extend(["--add-data", f"{src_path}{os.pathsep}src"])
        
        # 排除不必要的模块
        exclude_modules = [
            "tkinter", "matplotlib", "numpy", "pandas", "scipy",
            "PIL", "cv2", "tensorflow", "torch", "jupyter",
            "notebook", "IPython", "unittest", "test", "tests"
        ]
        
        for module in exclude_modules:
            args.extend(["--exclude-module", module])
        
        # 隐藏导入
        hidden_imports = [
            "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
            "psutil", "pynput", "pygame", "json", "os", "sys",
            "time", "threading", "pathlib", "datetime", "signal", "typing"
        ]
        
        # 平台特定隐藏导入
        if config.platform == "windows":
            hidden_imports.extend([
                "winsound", "win32gui", "win32process", "win32api", "win32con"
            ])
        elif config.platform == "macos":
            hidden_imports.extend([
                "AppKit", "Foundation", "Quartz", "Cocoa"
            ])
        elif config.platform == "linux":
            hidden_imports.extend([
                "Xlib", "Xlib.display", "Xlib.X", "Xlib.XK", "Xlib.Xutil"
            ])
        
        for module in hidden_imports:
            args.extend(["--hidden-import", module])
        
        # 添加图标配置
        icon_path = self._get_icon_path(config.platform)
        if icon_path and os.path.exists(icon_path):
            # 使用绝对路径避免PyInstaller路径解析问题
            abs_icon_path = os.path.abspath(icon_path)
            args.extend(["--icon", abs_icon_path])
        
        # 添加主程序
        args.append("run.py")
        
        safe_print(f"执行命令: {' '.join(args)}", f"Executing command: {' '.join(args)}")
        
        try:
            # 执行构建
            result = subprocess.run(args, check=True, capture_output=True, text=True)
            
            # 检查生成的文件
            if output_file.exists():
                size_mb = output_file.stat().st_size / (1024 * 1024)
                safe_print(f"✅ 构建成功: {config.name} ({size_mb:.1f} MB)", f"[SUCCESS] Build successful: {config.name} ({size_mb:.1f} MB)")
                self.build_results.append({
                    "config": config,
                    "file": output_file,
                    "size_mb": size_mb,
                    "success": True
                })
                return True
            else:
                safe_print(f"❌ 未找到生成文件: {config.name}", f"[ERROR] Generated file not found: {config.name}")
                self.build_results.append({
                    "config": config,
                    "file": None,
                    "size_mb": 0,
                    "success": False
                })
                return False
                
        except subprocess.CalledProcessError as e:
            safe_print(f"❌ 构建失败: {e}", f"[ERROR] Build failed: {e}")
            if e.stderr:
                safe_print(f"错误详情: {e.stderr}", f"Error details: {e.stderr}")
            self.build_results.append({
                "config": config,
                "file": None,
                "size_mb": 0,
                "success": False,
                "error": str(e)
            })
            return False
        except Exception as e:
            safe_print(f"❌ 构建异常: {e}", f"[ERROR] Build exception: {e}")
            self.build_results.append({
                "config": config,
                "file": None,
                "size_mb": 0,
                "success": False,
                "error": str(e)
            })
            return False
    
    def _build_with_docker(self, config: BuildConfig, force: bool = False) -> bool:
        """使用Docker构建"""
        safe_print(f"🐳 使用Docker构建 {config.platform}-{config.arch}...", f"[DOCKER] Building {config.platform}-{config.arch} with Docker...")
        
        # 检查Docker是否可用
        if not self._check_docker_available():
            safe_print("❌ Docker不可用，跳过Docker构建", "[ERROR] Docker not available, skipping Docker build")
            return False
        
        # 创建Dockerfile
        dockerfile_content = self._generate_dockerfile(config)
        dockerfile_path = Path("Dockerfile.build")
        
        try:
            with open(dockerfile_path, 'w', encoding='utf-8') as f:
                f.write(dockerfile_content)
            
            # 构建Docker镜像
            image_name = f"saveguard-builder-{config.platform}-{config.arch}"
            build_cmd = [
                "docker", "build", 
                "-f", str(dockerfile_path),
                "-t", image_name,
                "--no-cache",  # 避免缓存问题
                "."
            ]
            
            safe_print(f"执行Docker构建: {' '.join(build_cmd)}", f"Executing Docker build: {' '.join(build_cmd)}")
            result = subprocess.run(build_cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
            
            # 运行Docker容器并复制文件
            container_name = f"saveguard-build-{config.platform}-{config.arch}"
            run_cmd = [
                "docker", "run", 
                "--name", container_name,
                "-v", f"{Path.cwd()}/dist:/output",
                "--rm",  # 自动清理容器
                image_name
            ]
            
            safe_print(f"运行Docker容器: {' '.join(run_cmd)}", f"Running Docker container: {' '.join(run_cmd)}")
            result = subprocess.run(run_cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=180)
            
            # 检查输出文件
            output_file = self.dist_dir / config.name
            if output_file.exists():
                size_mb = output_file.stat().st_size / (1024 * 1024)
                safe_print(f"✅ Docker构建成功: {config.name} ({size_mb:.1f} MB)", f"[SUCCESS] Docker build successful: {config.name} ({size_mb:.1f} MB)")
                self.build_results.append({
                    "config": config,
                    "file": output_file,
                    "size_mb": size_mb,
                    "success": True
                })
                return True
            else:
                safe_print(f"❌ Docker构建失败: 未找到输出文件 {config.name}", f"[ERROR] Docker build failed: output file not found {config.name}")
                return False
                
        except subprocess.TimeoutExpired:
            safe_print(f"❌ Docker构建超时: {config.platform}-{config.arch}", f"[ERROR] Docker build timeout: {config.platform}-{config.arch}")
            return False
        except subprocess.CalledProcessError as e:
            safe_print(f"❌ Docker构建失败: {e}", f"[ERROR] Docker build failed: {e}")
            if e.stderr:
                safe_print(f"错误详情: {e.stderr}", f"Error details: {e.stderr}")
            return False
        except Exception as e:
            safe_print(f"❌ Docker构建异常: {e}", f"[ERROR] Docker build exception: {e}")
            return False
        finally:
            # 清理Dockerfile
            if dockerfile_path.exists():
                dockerfile_path.unlink()
            
            # 清理Docker镜像和容器
            try:
                subprocess.run(["docker", "rmi", image_name], capture_output=True, timeout=10)
            except:
                pass  # 忽略清理错误
    
    def _build_with_wsl(self, config: BuildConfig, force: bool = False) -> bool:
        """使用WSL构建Linux版本"""
        safe_print(f"🐧 使用WSL构建 {config.platform}-{config.arch}...", f"[WSL] Building {config.platform}-{config.arch} with WSL...")
        
        # 准备WSL命令
        wsl_cmd = [
            "wsl", "--",
            "bash", "-c",
            f"""
            cd /mnt/c/Users/root/code/SaveGuard &&
            python3 -m pip install pyinstaller>=5.13.0 &&
            python3 -m pip install -r requirements.txt &&
            python3 -c "
            import subprocess
            import sys
            import os
            
            args = [
                'pyinstaller',
                '--onefile',
                '--noconfirm',
                '--clean',
                '--noconsole',
                '--name', '{config.name}',
                '--distpath', 'dist',
                '--workpath', 'build',
                '--specpath', 'specs',
            ]
            
            # 添加数据文件
            if os.path.exists('src/languages'):
                args.extend(['--add-data', 'src/languages:languages'])
            if os.path.exists('src'):
                args.extend(['--add-data', 'src:src'])
            
            # 排除模块
            exclude_modules = ['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2', 'tensorflow', 'torch', 'jupyter', 'notebook', 'IPython', 'unittest', 'test', 'tests']
            for module in exclude_modules:
                args.extend(['--exclude-module', module])
            
            # 隐藏导入
            hidden_imports = ['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'psutil', 'pynput', 'pygame', 'json', 'os', 'sys', 'time', 'threading', 'pathlib', 'datetime', 'signal', 'typing', 'Xlib', 'Xlib.display', 'Xlib.X', 'Xlib.XK', 'Xlib.Xutil']
            for module in hidden_imports:
                args.extend(['--hidden-import', module])
            
            args.append('run.py')
            
            result = subprocess.run(args, check=True)
            safe_print('WSL构建完成', 'WSL build completed')
            "
            """
        ]
        
        try:
            safe_print(f"执行WSL构建命令...", "Executing WSL build command...")
            result = subprocess.run(wsl_cmd, check=True, capture_output=True, text=True)
            
            # 检查输出文件
            output_file = self.dist_dir / config.name
            if output_file.exists():
                size_mb = output_file.stat().st_size / (1024 * 1024)
                safe_print(f"✅ WSL构建成功: {config.name} ({size_mb:.1f} MB)", f"[SUCCESS] WSL build successful: {config.name} ({size_mb:.1f} MB)")
                self.build_results.append({
                    "config": config,
                    "file": output_file,
                    "size_mb": size_mb,
                    "success": True
                })
                return True
            else:
                safe_print(f"❌ WSL构建失败: 未找到输出文件 {config.name}", f"[ERROR] WSL build failed: output file not found {config.name}")
                return False
                
        except subprocess.CalledProcessError as e:
            safe_print(f"❌ WSL构建失败: {e}", f"[ERROR] WSL build failed: {e}")
            if e.stderr:
                safe_print(f"错误详情: {e.stderr}", f"Error details: {e.stderr}")
            return False
        except Exception as e:
            safe_print(f"❌ WSL构建异常: {e}", f"[ERROR] WSL build exception: {e}")
            return False
    
    def _generate_dockerfile(self, config: BuildConfig) -> str:
        """生成Dockerfile"""
        if config.platform == "linux":
            base_image = "python:3.11-slim"
        elif config.platform == "macos":
            base_image = "python:3.11-slim"  # 注意：macOS Docker构建有限制
        else:
            base_image = "python:3.11-slim"
        
        # 平台特定的隐藏导入
        hidden_imports = [
            "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
            "psutil", "pynput", "pygame", "json", "os", "sys",
            "time", "threading", "pathlib", "datetime", "signal", "typing"
        ]
        
        if config.platform == "windows":
            hidden_imports.extend([
                "winsound", "win32gui", "win32process", "win32api", "win32con"
            ])
        elif config.platform == "macos":
            hidden_imports.extend([
                "AppKit", "Foundation", "Quartz", "Cocoa"
            ])
        elif config.platform == "linux":
            hidden_imports.extend([
                "Xlib", "Xlib.display", "Xlib.X", "Xlib.XK", "Xlib.Xutil"
            ])
        
        # 构建隐藏导入参数
        hidden_import_args = " \\\n    ".join([f"--hidden-import {imp}" for imp in hidden_imports])
        
        dockerfile = f"""FROM {base_image}

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    build-essential \\
    libx11-dev \\
    libxext-dev \\
    libxrender-dev \\
    libxtst-dev \\
    libxi-dev \\
    libxrandr-dev \\
    libxss-dev \\
    libgconf-2-4 \\
    libxss1 \\
    libasound2-dev \\
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir pyinstaller>=5.13.0
RUN pip install --no-cache-dir -r requirements.txt

# 创建输出目录
RUN mkdir -p /output

# 构建命令
RUN pyinstaller \\
    --onefile \\
    --noconfirm \\
    --clean \\
    --noconsole \\
    --name {config.name} \\
    --distpath /output \\
    --workpath build \\
    --specpath specs \\
    --add-data src/languages:languages \\
    --add-data src:src \\
    --exclude-module tkinter \\
    --exclude-module matplotlib \\
    --exclude-module numpy \\
    --exclude-module pandas \\
    --exclude-module scipy \\
    --exclude-module PIL \\
    --exclude-module cv2 \\
    --exclude-module tensorflow \\
    --exclude-module torch \\
    --exclude-module jupyter \\
    --exclude-module notebook \\
    --exclude-module IPython \\
    --exclude-module unittest \\
    --exclude-module test \\
    --exclude-module tests \\
    {hidden_import_args} \\
    run.py

# 设置输出目录
VOLUME ["/output"]

# 默认命令
CMD ["echo", "Build completed"]
"""
        return dockerfile
    
    def create_release_package(self) -> bool:
        """创建发布包"""
        safe_print("\n📦 创建发布包...", "\n[PACKAGE] Creating release package...")
        
        # 创建release目录
        self.release_dir.mkdir(exist_ok=True)
        
        # 复制构建文件
        for result in self.build_results:
            if result["success"] and result["file"]:
                dest_file = self.release_dir / result["file"].name
                shutil.copy2(result["file"], dest_file)
                safe_print(f"📋 复制: {result['file'].name}", f"[COPY] Copying: {result['file'].name}")
        
        # 创建README文件
        readme_content = self._generate_readme()
        readme_file = self.release_dir / "README.txt"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        safe_print(f"📄 创建说明文件: {readme_file.name}", f"[CREATE] Creating documentation file: {readme_file.name}")
        
        return True
    
    def _generate_readme(self) -> str:
        """生成README文件内容"""
        content = f"""SaveGuard v1.0 发布包
====================

构建时间: {platform.system()} {platform.release()}
Python版本: {sys.version}

包含的可执行文件:
"""
        
        for result in self.build_results:
            if result["success"]:
                content += f"- {result['config'].name} ({result['size_mb']:.1f} MB)\n"
        
        content += f"""
使用说明:
1. 根据您的操作系统和架构选择对应的可执行文件
2. 双击运行即可，无需安装Python环境
3. 首次运行可能需要管理员权限

支持的平台:
- Windows: x64, x86, arm64
- macOS: x86_64, arm64, universal
- Linux: x86_64, aarch64, armv7l

项目地址: https://github.com/rootwhois/saveguard
"""
        return content
    
    def show_results(self):
        """显示构建结果"""
        safe_print("\n📊 构建结果:", "\n[RESULTS] Build Results:")
        safe_print("=" * 60)
        
        # 统计信息
        total_builds = len(self.build_results)
        successful_builds = sum(1 for r in self.build_results if r["success"])
        failed_builds = total_builds - successful_builds
        
        safe_print(f"总构建数: {total_builds}", f"Total builds: {total_builds}")
        safe_print(f"成功: {successful_builds}", f"Successful: {successful_builds}")
        safe_print(f"失败: {failed_builds}", f"Failed: {failed_builds}")
        
        # 显示成功构建的文件
        if successful_builds > 0:
            safe_print(f"\n✅ 成功构建的文件:", f"\n[SUCCESS] Successfully built files:")
            for result in self.build_results:
                if result["success"]:
                    status = "⏭️ 跳过" if result.get("skipped", False) else "✅ 新建"
                    status_fallback = "[SKIP]" if result.get("skipped", False) else "[NEW]"
                    safe_print(f"  {status} {result['config'].name} ({result['size_mb']:.1f} MB)", f"  {status_fallback} {result['config'].name} ({result['size_mb']:.1f} MB)")
        
        # 显示失败构建的文件
        if failed_builds > 0:
            safe_print(f"\n❌ 构建失败的文件:", f"\n[FAILED] Failed builds:")
            for result in self.build_results:
                if not result["success"]:
                    error_msg = result.get("error", "未知错误")
                    safe_print(f"  ❌ {result['config'].name} - {error_msg}", f"  [ERROR] {result['config'].name} - {error_msg}")
        
        # 显示文件位置
        if self.dist_dir.exists():
            safe_print(f"\n📁 构建文件目录: {self.dist_dir.absolute()}", f"\n[DIR] Build files directory: {self.dist_dir.absolute()}")
        
        if self.release_dir.exists():
            safe_print(f"📁 发布包目录: {self.release_dir.absolute()}", f"[DIR] Release package directory: {self.release_dir.absolute()}")
    
    def build_all(self, platforms: Optional[List[str]] = None, force: bool = False, smart: bool = False) -> bool:
        """构建所有平台"""
        safe_print("🚀 SaveGuard 多平台构建脚本", "[SaveGuard] Multi-platform Build Script")
        safe_print("=" * 60)
        safe_print(f"🖥️ 当前系统: {platform.system()} {platform.release()}", f"Current System: {platform.system()} {platform.release()}")
        safe_print(f"🏗️ 当前架构: {self.current_arch}", f"Current Architecture: {self.current_arch}")
        safe_print(f"🐍 Python版本: {sys.version}", f"Python Version: {sys.version}")
        safe_print(f"📁 工作目录: {Path.cwd()}", f"Working Directory: {Path.cwd()}")
        
        # 检查Python版本
        if not self.check_python_version():
            return False
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 获取构建配置
        if smart:
            configs = self.get_buildable_configs(platforms)
            safe_print(f"\n📋 智能模式：计划构建 {len(configs)} 个版本（仅构建当前平台支持的版本）", f"\n[SMART] Smart mode: planning to build {len(configs)} versions (only current platform supported)")
        else:
            configs = self.get_build_configs(platforms)
            safe_print(f"\n📋 计划构建 {len(configs)} 个版本", f"\n[PLAN] Planning to build {len(configs)} versions")
        
        # 构建所有配置
        success_count = 0
        for i, config in enumerate(configs, 1):
            safe_print(f"\n[{i}/{len(configs)}] 构建 {config.platform}-{config.arch}", f"\n[{i}/{len(configs)}] Building {config.platform}-{config.arch}")
            if self.build_single_platform(config, force):
                success_count += 1
        
        # 创建发布包
        if success_count > 0:
            self.create_release_package()
        
        # 显示结果
        self.show_results()
        
        safe_print(f"\n🎉 构建完成! 成功构建 {success_count}/{len(configs)} 个版本", f"\n[COMPLETE] Build completed! Successfully built {success_count}/{len(configs)} versions")
        
        if success_count > 0:
            safe_print("\n💡 使用说明:", "\n[USAGE] Usage instructions:")
            safe_print("1. 在 release 目录中找到对应您系统的可执行文件", "1. Find the executable file for your system in the release directory")
            safe_print("2. 双击运行即可，无需安装Python环境", "2. Double-click to run, no Python environment required")
            safe_print("3. 首次运行可能需要管理员权限", "3. Administrator privileges may be required for first run")
            safe_print("\n📖 更多信息请查看项目文档: https://github.com/rootwhois/saveguard", "\n[DOCS] More information: https://github.com/rootwhois/saveguard")
        
        return success_count > 0

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SaveGuard 多平台构建脚本")
    parser.add_argument("--platforms", nargs="+", 
                       choices=["windows", "macos", "linux"],
                       help="指定要构建的平台 (默认: 所有平台)")
    parser.add_argument("--force", action="store_true",
                       help="强制重新构建已存在的文件")
    parser.add_argument("--current-only", action="store_true",
                       help="只构建当前平台")
    parser.add_argument("--smart", action="store_true",
                       help="智能模式：只构建当前平台能构建的版本")
    
    args = parser.parse_args()
    
    builder = MultiPlatformBuilder()
    
    # 确定要构建的平台
    if args.smart:
        # 智能模式：只构建当前平台能构建的版本
        platforms = [builder.current_platform]
        safe_print(f"🧠 智能模式：只构建 {builder.current_platform} 平台", f"[SMART] Smart mode: only building {builder.current_platform} platform")
    elif args.current_only:
        platforms = [builder.current_platform]
    elif args.platforms:
        platforms = args.platforms
    else:
        platforms = None  # 所有平台
    
    # 执行构建
    success = builder.build_all(platforms, args.force, args.smart)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

# core/config.py
from pathlib import Path

class Config:
    """全局配置"""

    class LOG:
        """日志相关配置"""
        DIR = "logs"
        LEVEL = "info"
        FILENAME = "teatime.log"

    class WORK:
        """工作目录相关配置"""
        ROOT = Path("work")
        CACHE_DIR = ROOT / "cache"
        TASK_DIR = ROOT / "tasks"

    class BROWSER:
        """浏览器相关配置（预留）"""
        TIMEOUT = 30000  # 默认超时，单位毫秒

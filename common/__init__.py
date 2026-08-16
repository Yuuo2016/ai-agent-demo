# AI Agent 实战题 公共模块
import os

# 加载项目根目录下的 .env 配置文件
try:
    from dotenv import load_dotenv

    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass

"""
配置加载模块
"""
import yaml
import os

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置文件路径
CONFIG_FILE = os.path.join(BASE_DIR, "config.yaml")

def load_config():
    """加载配置文件"""
    config_path = CONFIG_FILE if os.path.isfile(CONFIG_FILE) else os.path.join(BASE_DIR, 'config.yaml.template')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

# 全局配置对象
config = load_config()

# 本地数据功能不依赖模型密钥；实际调用模型时再检查配置。
API_KEY = (os.environ.get("DEEPSEEK_API_KEY") or config['api'].get('deepseek_api_key') or '').strip()
if API_KEY == "在这里填入您的API密钥":
    API_KEY = ''
API_ENDPOINT = config['api'].get('endpoint', 'https://api.deepseek.com').rstrip('/')
TEXT_MODEL = config['api']['models'].get('text_generation', 'deepseek-v4-flash')
API_TIMEOUT = int(config['api'].get('timeout_seconds', 120))

# 数据库配置
DB_TYPE = config['database']['type']
DB_PATH = os.environ.get("SPARK_DB_PATH") or os.path.join(BASE_DIR, config['database']['path'])
DB_PATH = os.path.abspath(DB_PATH)

# 存储配置
UPLOAD_PATH = os.path.join(BASE_DIR, config['storage']['upload_path'])
EXPORT_PATH = os.path.join(BASE_DIR, config['storage']['export_path'])

# UI配置
UI_CONFIG = config['ui']

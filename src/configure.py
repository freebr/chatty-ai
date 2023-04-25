import os
import yaml
from dataclasses import dataclass, field
from definition.cls import Singleton
from definition.const import DIR_CONFIG
from logging import getLogger, Logger
from typing import Dict

@dataclass
class ConfigData:
    access_tokens: Dict[str, any] = field(default_factory=dict)
    api_keys: Dict[str, any] = field(default_factory=dict)
    articles: Dict[str, Dict] = field(default_factory=dict)
    autoreplies: Dict[str, str] = field(default_factory=dict)
    chatgroups: Dict[str, any] = field(default_factory=dict)
    databases: Dict[str, dict] = field(default_factory=dict)
    features: Dict[str, any] = field(default_factory=dict)
    wxpay: Dict[str, str] = field(default_factory=dict)

CONFIG_MAPPING = {
    'AccessTokens': 'access_tokens',
    'APIKeys': 'api_keys',
    'Articles': 'articles',
    'Autoreplies': 'autoreplies',
    'Chatgroups': 'chatgroups',
    'Databases': 'databases',
    'Features': 'features',
    'WxPay': 'wxpay',
}

class Config(metaclass=Singleton):
    config_file: str
    data: ConfigData
    logger: Logger = None
    def __init__(self, **kwargs):
        """
        初始化配置类
        """
        self.logger = getLogger('CONFIG')
        self.config_file = kwargs.get('config_file', os.path.join(DIR_CONFIG, 'config.yaml'))
        self.load()

    def load(self):
        """
        加载配置
        """
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.load(f, Loader=yaml.FullLoader)
                mapped_dict = self.get_mapped_dict(config_data, 'load')
                self.data = ConfigData(**mapped_dict)
            self.logger.info('加载配置成功')
        except Exception as e:
            self.logger.error('加载配置失败：%s', str(e))

    def save(self):
        """
        保存配置
        """
        try:
            mapped_dict = self.get_mapped_dict(self.data, 'save')
            with open(self.config_file, mode='w', encoding='utf-8', errors='ignore') as f:
                yaml.dump(mapped_dict, f, allow_unicode=True)
                self.logger.info('保存配置成功')
        except Exception as e:
            self.logger.error('保存配置失败：%s', str(e))

    def get_mapped_dict(self, config_data, mode):
        """
        返回配置映射字典
        """
        ret = {}
        if mode == 'load':
            for key, value in CONFIG_MAPPING.items():
                ret[value] = config_data.get(key)
        elif mode == 'save':
            for key, value in CONFIG_MAPPING.items():
                ret[key] = config_data.__dict__.get(value)
        else: pass
        return ret
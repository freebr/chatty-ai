from logging import Logger
from os import path
import yaml

KEYTOKEN_NAME = {
    'api_keys': 'API Key 列表',
    'access_tokens': 'Access Token 列表',
}
class KeyTokenManager:
    workdir: str
    file_path: dict
    configs: dict
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.workdir = kwargs['workdir']
        self.file_path = {
            'api_keys': path.abspath(path.join(self.workdir, 'api-keys.yml')),
            'access_tokens': path.abspath(path.join(self.workdir, 'access-tokens.yml')),
        }
        self.configs = {}
        self.read('api_keys')
        self.read('access_tokens')
        
    def read(self, list_type):
        try:
            list_name = KEYTOKEN_NAME.get(list_type, list_type)
            file_path = self.file_path.get(list_type)
            self.configs[list_type] = {}
            configs = self.configs[list_type]
            if not file_path: raise Exception('找不到类型 %s(%s) 的密钥配置文件' % (list_type, list_name))
            if not path.isfile(file_path):
                self.logger.error('%s 加载失败，找不到文件：%s', list_name, file_path)
                return False
            result:dict
            with open(file_path, 'r') as f:
                result = yaml.load(f, Loader=yaml.FullLoader)
            if not result: raise Exception('%s 加载失败' % list_name)
            for service_name, service_keys in result.items():
                if list_type == 'api_keys' and isinstance(service_keys, str): service_keys = [service_keys]
                configs[service_name] = service_keys
            if configs == {}:
                self.logger.warn('没有可用的 %s' % list_name)
            else:
                self.logger.info('%s 加载成功，数量：%d', list_name, len(configs))
            return True
        except Exception as e:
            self.logger.error('%s 加载失败：%s', list_name, str(e))
            return False

    def save(self, list_type):
        try:
            list_name = KEYTOKEN_NAME.get(list_type, list_type)
            file_path = self.file_path.get(list_type)
            configs = self.configs[list_type]
            with open(file_path, mode='w', encoding='utf-8', errors='ignore') as f:
                yaml.dump(configs, f)
            self.logger.info('%s 保存成功，数量：%d', list_name, len(configs))
            return True
        except Exception as e:
            self.logger.error('%s 保存失败：', list_name, str(e))
            return False
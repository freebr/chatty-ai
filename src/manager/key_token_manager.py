from configure import Config
from definition.cls import Singleton
from logging import getLogger, Logger

cfg = Config()
class KeyTokenManager(metaclass=Singleton):
    access_tokens: dict
    api_keys: dict
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger(self.__class__.__name__)
        self.load()
        
    def load(self):
        try:
            self.access_tokens = cfg.data.access_tokens or {}
            self.api_keys = cfg.data.api_keys or {}
            for service_name, service_keys in self.api_keys.items():
                if isinstance(service_keys, str): service_keys = [service_keys]
                self.api_keys[service_name] = service_keys
            cfg.data.access_tokens = self.access_tokens
            cfg.data.api_keys = self.api_keys
            if self.access_tokens == {}:
                self.logger.warn('没有可用的 Access Token')
            else:
                self.logger.info('Access Token 加载成功，数量：%d', len(self.access_tokens))
            if self.api_keys == {}:
                self.logger.warn('没有可用的 API Key')
            else:
                self.logger.info('API Key 加载成功，数量：%d', len(self.api_keys))
            return True
        except Exception as e:
            self.logger.error('Access Token/API Key 加载失败：%s', str(e))
            return False

    def save(self):
        return cfg.save()

    def get_app_param(self):
        """
        返回微信公众号 APP_PARAM 信息
        """
        return {
            name: self.api_keys.get('App').get(name)
            for name in ['APPID', 'APPSECRET', 'APPTOKEN', 'ENCODING_AES_KEY']
        }
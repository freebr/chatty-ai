from configure import Config
from definition.cls import Singleton
from logging import getLogger, Logger

cfg = Config()
class AutoReplyManager(metaclass=Singleton):
    autoreplies: dict
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = getLogger('AUTOREPLYMGR')
        self.load()
    
    def load(self):
        try:
            self.autoreplies = cfg.data.autoreplies
            self.logger.info('自动回复消息模板加载成功')
            return True
        except Exception as e:
            self.logger.error('自动回复消息模板加载失败：%s', str(e))
            return False

    def get(self, name):
        if name not in self.autoreplies: return ''
        return self.autoreplies[name]

    def set(self, name, value):
        self.autoreplies[name] = value
        cfg.save()
        return True
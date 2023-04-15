from const import DIR_CONFIG
from os import path
from logging import Logger

class AutoReplyManager:
    file_path: str = path.join(DIR_CONFIG, 'autoreply.yml')
    autoreplies: dict = {}
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.read()
    
    def read(self):
        if not path.isfile(self.file_path):
            self.logger.error('自动回复消息模板加载失败，找不到文件：%s', self.file_path)
            return False
        with open(self.file_path, mode='r', encoding='utf-8', errors='ignore') as f:
            self.autoreplies['welcome'] = f.read().strip()
        self.logger.info('自动回复消息模板加载成功')
        return True

    def save(self):
        with open(self.file_path, mode='w', encoding='utf-8', errors='ignore')  as f:
            f.write(self.autoreplies['welcome'])

    def get(self, name):
        if name not in self.autoreplies: return ''
        return self.autoreplies[name]

    def set(self, name, value):
        self.autoreplies[name] = value
        self.save()
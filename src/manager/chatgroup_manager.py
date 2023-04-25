from configure import Config
from definition.cls import Singleton
from logging import getLogger, Logger
from random import random

cfg = Config()
class ChatgroupManager(metaclass=Singleton):
    chatgroups: dict
    qrcodes: list
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = getLogger('CHATGROUPMGR')
        self.load()
        
    def load(self):
        try:
            self.chatgroups = cfg.data.chatgroups
            self.qrcodes = cfg.data.chatgroups.get('QRCodes', [])
            self.chatgroups['QRCodes'] = self.qrcodes
            self.logger.info('群聊信息加载成功，数量：%d', len(self.chatgroups))
            return True
        except Exception as e:
            self.logger.error('群聊信息加载失败：%s', str(e))
            return False

    def add_qrcode(self, qrcode_id=''):
        if qrcode_id in self.qrcodes: return True
        self.qrcodes.append(qrcode_id)
        cfg.save()
        return True

    def remove_qrcode(self, qrcode_id=''):
        if qrcode_id not in self.qrcodes: return False
        self.qrcodes.remove(qrcode_id)
        cfg.save()
        return True

    def shuffle_get_qrcode(self):
        """
        随机抽取一个群聊二维码图片并返回 id
        """
        index = int(random() * len(self.qrcodes))
        return self.qrcodes[index]
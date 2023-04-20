from definition.const import DIR_CONFIG
from os import path
from random import random
from logging import Logger
import yaml

class GroupChatManager:
    file_path: str = path.join(DIR_CONFIG, 'group-chat-qrcode.yml')
    qrcodes: list = []
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.read()
        
    def read(self):
        try:
            if not path.isfile(self.file_path):
                self.logger.error('群聊二维码列表加载失败，找不到文件：%s', self.file_path)
                return False
            result:dict
            with open(self.file_path, 'r') as f:
                result = yaml.load(f, Loader=yaml.FullLoader)
            if not result: raise Exception('群聊二维码列表加载失败')
            qrcodes = result['QRCodes']
            self.qrcodes = []
            for qrcode in qrcodes:
                self.qrcodes.append(qrcode)
            self.logger.info('群聊二维码列表加载成功，数量：%d', len(self.qrcodes))
            return True
        except Exception as e:
            self.logger.error(e)
            return False


    def save(self):
        with open(self.file_path, mode='w', encoding='utf-8', errors='ignore')  as f:
            f.write('\n'.join(self.qrcodes))

    def add_qrcode(self, qrcode_id=''):
        if qrcode_id in self.qrcodes: return True
        self.qrcodes.append(qrcode_id)
        self.save()
        return True

    def remove_qrcode(self, qrcode_id=''):
        if qrcode_id not in self.qrcodes: return False
        self.qrcodes.remove(qrcode_id)
        self.save()
        return True

    def shuffle_get_qrcode(self):
        """
        随机抽取一个群聊二维码图片并返回 id
        """
        index = int(random() * len(self.qrcodes))
        return self.qrcodes[index]
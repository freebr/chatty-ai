from definition.const import DIR_CONFIG
from logging import Logger
from os import path
import yaml

class FeatureManager:
    # 等级特性字典
    features:dict
    features_file_path = path.join(DIR_CONFIG, 'features.yml')
    logger: Logger = None

    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.features = {}
        self.read_features()

    def read_features(self):
        """
        加载等级特性字典
        """
        try:
            if not path.isfile(self.features_file_path):
                self.logger.error('等级特性字典加载失败，找不到文件：%s', self.file_path)
                return False
            result:dict
            with open(self.features_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                result = yaml.load(f, Loader=yaml.FullLoader)
            if not result: raise Exception('等级特性字典加载失败')
            self.features = result
            self.logger.info('等级特性字典加载成功')
            return True
        except Exception as e:
            self.logger.error('等级特性字典加载失败：%s', str(e))
            return False

    def can_use_feature(self, user:dict, feature_path:str):
        """
        返回指定用户是否可以使用指定特性
        """
        level = user.get('level')
        expr = 'self.features["' + feature_path.replace('.', '"]["') + '"]'
        try:
            level_list = eval(expr)
            if type(level_list) != list: return False
            return level in level_list
        except Exception as e:
            self.logger.error('查询等级特性失败：%s', str(e))
            return False
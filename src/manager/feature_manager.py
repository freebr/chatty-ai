from configure import Config
from definition.cls import Singleton
from logging import getLogger, Logger
from numpy import Infinity

cfg = Config()
class FeatureManager(metaclass=Singleton):
    # 等级特性字典
    features: dict
    logger: Logger = None

    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.load()

    def load(self):
        """
        加载等级特性字典
        """
        try:
            self.features = cfg.data.features
            self.logger.info('等级特性字典加载成功')
            return True
        except Exception as e:
            self.logger.error('等级特性字典加载失败：%s', str(e))
            return False

    def get_total_feature_credit(self, level: str, feature: str):
        """
        返回指定用户等级可以使用指定特性的额度
        """
        expr = 'self.features.get("' + feature.replace('.', '", {}).get("') + '", {})'
        try:
            rules = eval(expr)
            if type(rules) == list:
                return Infinity if level in rules else 0
            elif type(rules) == dict:
                return rules.get(level) if level in rules else 0
            else:
                raise Exception('特性规则 %s 不存在' % feature)
        except Exception as e:
            self.logger.error('查询等级特性额度失败：%s', str(e))
            return False
import json
import requests.api as requests
from logging import getLogger, Logger

from definition.cls import Singleton

class JokeService(metaclass=Singleton):
    api_key = {}
    semantic_parse: any
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = getLogger("JOKESERVICE")
        self.api_key = kwargs['api_key']
        self.semantic_parse = kwargs['semantic_parse']

    def __real_query(self, count):
        """
        查询笑话信息
        """
        try:
            if len(self.api_key) == 0: raise Exception('没有可用的 API key')
            api_key = self.api_key[0]
            # 笑话信息
            url = f'https://api.jisuapi.com/xiaohua/text?pagenum=1&pagesize={count}&sort=rand&appkey={api_key}'
            res = requests.post(url).json()
            data = res['result']
            if not data:
                self.logger.warn('笑话信息查询结果为空')
            list = data['list']
            result = [{
                'content': joke['content'],
            } for joke in list]
            self.logger.info(result)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            self.logger.error('查询笑话信息失败：%s', str(e))
            return ''

    def invoke(self, args):
        """
        调用服务并返回信息
        """
        count = args.get('count')
        result = self.__real_query(count=count)
        return result
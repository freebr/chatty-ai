from logging import Logger
import json
import re
import requests.api as requests

class JokeService:
    api_key = {}
    semantic_parse: any
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.api_key = kwargs['api_key']
        self.semantic_parse = kwargs['semantic_parse']

    def __real_query(self):
        """
        查询笑话信息
        """
        try:
            if len(self.api_key) == 0: raise Exception('没有可用的 API key')
            api_key = self.api_key[0]
            # 笑话信息
            url = f'https://api.jisuapi.com/xiaohua/text?pagenum=1&pagesize=10&sort=rand&appkey={api_key}'
            res = requests.post(url).json()
            data = res['result']
            if not data:
                self.logger.warn('笑话信息查询结果为空')
            list = data['list']
            result = [{
                'content': joke['content'],
            } for joke in list]
            self.logger.info(result)
            return result
        except Exception as e:
            self.logger.error('查询笑话信息失败：%s', e)
            return ''

    def test(self, message:str):
        """
        从 message 中尝试提取笑话查询信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
        if re.search('笑话|幽默|搞笑|段子|joke|gag', message, re.I):
            return True, (message,)
        return False, None

    def invoke(self, data, **kwargs):
        """
        调用服务并返回信息，否则返回 None
        """
        result = self.__real_query()
        return 'Do not say your jokes, say jokes below:' + json.dumps(result, ensure_ascii=False)

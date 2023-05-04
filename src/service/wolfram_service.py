import requests.api as requests
import web
from logging import getLogger, Logger

from definition.cls import Singleton

class WolframService(metaclass=Singleton):
    semantic_parse: any
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger("WOLFRAMSERVICE")

    def __real_query(self, input):
        """
        查询问题求解信息
        ip_list: IP 地址列表
        """
        try:
            results = {}
            input = web.urlquote(input)
            res = requests.get(f'https://api.wolframalpha.com/v2/query?input={input}&appid=demo&format=image&output=json', timeout=60).json()
            pods = res.get('queryresult').get('pods')
            if not pods:
                didyoumeans = res.get('queryresult').get('didyoumeans')
                if not didyoumeans: return {}
                if type(didyoumeans) == list:
                    question = didyoumeans[0]['val']
                else:
                    question = didyoumeans['val']
                return self.__real_query(question)
            self.logger.info(res.get('queryresult'))
            for pod in pods:
                pod_title = pod['title']
                if pod_title in ['Input', 'Input interpretation']: continue
                subpods = pod['subpods']
                aspect = []
                for subpod in subpods:
                    img = subpod['img']
                    img_src = img['src']
                    desc = img['title']
                    aspect.append('%s\n```image\n![](%s)\n```' % (desc, img_src))
                results[pod_title] = aspect
            return results
        except Exception as e:
            self.logger.error('查询问题求解信息失败：%s', str(e))
            return {}

    def invoke(self, args):
        """
        调用服务并返回信息
        """
        questions = args['question']
        if type(questions) == str: questions = [questions]
        results = []
        for question in questions:
            result = self.__real_query(input=question)
            results.append(f'{question}\n解答：{result}')
        prompt = '根据以下 Wolfram 得到的信息详细回答，不要删除任何 ```image``` 标记\n'
        return prompt + '\n'.join(results)
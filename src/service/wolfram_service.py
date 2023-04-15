from logging import Logger
import json
import re
import requests.api as requests
import web

reMaths = (r'数学|方程|等式|函数|积分|微分|导数|'
r'代数|向量|张量|矩阵|行列式|特征值|'
r'计算|化简|通分|约分|求导|求和|求解|'
r'椭圆|圆锥|圆柱|圆台|曲线|抛物线|图像|'
r'极限|级数|阶乘|伽马|欧拉|高斯|'
r'\b(arc|a)?(sin|cos|tan|cot)\b|\b(exp|lg|log|pow|sqrt?)\b')
class WolframService:
    semantic_parse: any
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.semantic_parse = kwargs['semantic_parse']

    def __real_query(self, message):
        """
        查询问题求解信息
        ip_list: IP 地址列表
        """
        try:
            results = {}
            input = web.urlquote(message)
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
            self.logger.error('查询问题求解信息失败：%s', e)
            return {}

    def test(self, message:str):
        """
        从 message 中尝试提取问题求解信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
        if re.search(reMaths, message):
            return True, (message, 'math')
        return False, None

    def invoke(self, data, **kwargs):
        """
        调用服务并返回信息，否则返回 None
        """
        message, typename = data
        message += '\nOutput:'
        reply = self.semantic_parse(system_prompt='Do not answer the question. Translate input to English. Input:', content=message)
        self.logger.info(reply)
        result = self.__real_query(message=reply)
        if len(result):
            result = '请将以下 json 代码转换成 markdown 代码，开头：“以下是查询 Wolfram 得到的信息”.不要删除<```image>标记.对每一个<```image>标记前面的文字进行翻译.' + json.dumps(result, ensure_ascii=False)
        else:
            result = '没有查询到相关问题求解信息'
        return result
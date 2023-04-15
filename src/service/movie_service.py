from logging import Logger
from time import strftime, localtime
import json
import re
import requests.api as requests

class MovieService:
    api_key = {}
    semantic_parse: any
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.api_key = kwargs['api_key']
        self.semantic_parse = kwargs['semantic_parse']

    def __real_query(self, city, date, movie_name):
        """
        查询电影信息
        """
        try:
            if len(self.api_key) == 0: raise Exception('没有可用的 API key')
            api_key = self.api_key[0]
            # 电影列表
            url = f'https://api.jisuapi.com/movie/on?appkey={api_key}'
            form_data = {
                'city': city,
                'date': date,
            }
            res = requests.post(url, data=form_data).json()
            data = res['result']
            result = {}
            if not data:
                self.logger.warn('电影列表查询结果为空')
            else:
                list = data['list']
                movie_list = [{
                    'id': movie['movieid'],
                    'name': movie['moviename'],
                } for movie in list]
                result['movie_list'] = movie_list
            # 电影详情
            if movie_name:
                url = f'https://api.jisuapi.com/movie/detail?appkey={api_key}'
                form_data = {
                    'moviename': movie_name,
                }
                res = requests.post(url, data=form_data).json()
                data = res['result']
                if not data:
                    self.logger.warn('电影详情查询结果为空')
                else:
                    result['movie_detail'] = data
            return result
        except Exception as e:
            self.logger.error('查询电影信息失败：%s', e)
            return ''

    def test(self, message:str):
        """
        从 message 中尝试提取电影查询信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
        if re.search('电影|影片|影院|movie|film|cinema', message, re.I):
            return True, (message,)
        return False, None

    def invoke(self, data, **kwargs):
        """
        调用服务并返回信息，否则返回 None
        """
        # 获取模型的语义理解结果
        message = data[0]
        today = strftime('%Y-%m-%d', localtime())
        system_prompt = '不要回答用户问题，只从问题提取信息并按 JSON 格式返回：[{"city":"城市（默认为广州）","date":"年-月-日（默认为none）","moviename":"用户给出的电影名称（默认为none）"}...] 数组元素等于问题个数 不要加任何注释'
        reply = self.semantic_parse(system_prompt=system_prompt, content=message)
        self.logger.info(reply)
        # 提取 JSON
        match = re.search(r'\[(.*)\]', reply, re.S)
        # 未提取到 JSON 结构，视为非电影查询问题
        if not match: return
        json_array = match[0]
        questions = json.loads(json_array)
        results = []
        for question in questions:
            city = question['city']
            date = question['date']
            moviename = question['moviename']
            if date == 'none': date = today
            if moviename == 'none': moviename = ''
            results.append(self.__real_query(city=city, date=date, movie_name=moviename))
        return 'System enquired movie info:' + json.dumps(results, ensure_ascii=False)

import json
import requests.api as requests
from itertools import product
from logging import getLogger, Logger
from time import strftime, localtime

from definition.cls import Singleton

DEFAULT_CITY = '广州'
class MovieService(metaclass=Singleton):
    api_key = {}
    semantic_parse: any
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger("MOVIESERVICE")
        self.api_key = kwargs['api_key']

    def __real_query(self, city=DEFAULT_CITY, date='', movie_name=''):
        """
        查询电影信息
        """
        today = strftime('%Y-%m-%d', localtime())
        if not date: date = today
        try:
            if len(self.api_key) == 0: raise Exception('没有可用的 API key')
            api_key = self.api_key[0]
            result = {}
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
                    result[f'{movie_name}介绍'] = data
            else:
                # 电影列表
                url = f'https://api.jisuapi.com/movie/on?appkey={api_key}'
                form_data = {
                    'city': city,
                    'date': date,
                }
                res = requests.post(url, data=form_data).json()
                data = res['result']
                if not data:
                    self.logger.warn('电影列表查询结果为空')
                else:
                    list = data['list']
                    movie_list = [movie['moviename'] for movie in list]
                    result[f'{city}{date}上映电影'] = movie_list
            if not result: return ''
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            self.logger.error('查询电影信息失败：%s', str(e))
            return ''

    def invoke(self, args):
        """
        调用服务并返回信息
        """
        movie_names = args.get('name', '')
        cities = args.get('city', '')
        dates = args.get('date', '')
        if type(movie_names) == str: movie_names = [movie_names]
        if type(cities) == str: cities = [cities]
        if type(dates) == str: dates = [dates]
        movie_lists = []
        for city, date in product(cities, dates):
            # 没有指定城市时，GPT可能会自动填充
            if city == '全国': city = ''
            movie_list = self.__real_query(city=city, date=date)
            movie_lists.append(movie_list)

        movie_details = []
        for movie_name in movie_names:
            movie_detail = self.__real_query(movie_name=movie_name)
            movie_details.append(movie_detail)

        result = ''.join(movie_lists) + ''.join(movie_details)
        return result
import json
import re
import requests.api as requests
import web
from bs4 import BeautifulSoup
from cpca import transform_text_with_addrs
from datetime import datetime
from logging import getLogger, Logger
from numpy import Infinity
from pandas import DataFrame

from configure import Config
from definition.cls import Singleton

cfg = Config()
class WeatherService(metaclass=Singleton):
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger("WEATHERSERVICE")
        self.api_key = kwargs['api_key']

    def __real_query(self, places: list):
        """
        查询天气信息
        places: 地区名称列表
        """
        try:
            if len(self.api_key) == 0: raise Exception('没有可用的 API key')
            api_key = self.api_key[0]
            results = []
            for place in places:
                url = f'https://api.jisuapi.com/weather/query?appkey={api_key}'
                form_data = {
                    'city': place,
                }
                res = requests.post(url, data=form_data)
                data = res.json()
                results.append(f'{place}天气:\n' + json.dumps(data, ensure_ascii=False))
            return ''.join(results)
        except Exception as e:
            self.logger.error('查询天气信息失败：%s', str(e))
            return ''

    def invoke(self, args):
        """
        调用服务并返回信息
        """
        places = args.get('place')
        if type(places) == str: places = [places]
        result = self.__real_query(places=places)
        return result

class WeatherServiceAmap:
    api_key = {}
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger("WEATHERSERVICEAMAP")
        self.api_key = kwargs['api_key']

    def __real_query(self, ad_code_list: list, which_date_list: list):
        """
        查询天气信息（高德）
        ad_code_list: 城市的行政编码
        which_date_list: 天气的日期编码列表
        """
        try:
            if len(self.api_key) == 0: raise Exception('没有可用的 API key')
            api_key = self.api_key[0]
            results = []
            for ad_code, which_date in zip(ad_code_list, which_date_list):
                # 获取实况天气信息
                url = f'https://restapi.amap.com/v3/weather/weatherInfo?city={ad_code}&key={api_key}&extensions=base'
                res = requests.get(url).json()
                live = res.get('lives')[0]
                # 获取预报天气信息
                url = f'https://restapi.amap.com/v3/weather/weatherInfo?city={ad_code}&key={api_key}&extensions=all'
                res = requests.get(url).json()
                forecast = res.get('forecasts')[0].get('casts', ['', '', ''])
                data = {
                    'now': live,
                    'today': forecast[0],
                    'tomorrow': forecast[1],
                    'the day after tomorrow': forecast[2],
                    'in 3 days': forecast[3],
                }
                results.append(json.dumps(data, ensure_ascii=False))
            return results
        except Exception as e:
            self.logger.error('查询天气信息失败：%s', e)
            return []

    def test(self, message: str):
        """
        从 message 中尝试提取天气查询信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
        re_weather = re.compile((
            r'天气|气候|气温|温度|室温|外温|湿度|降水|'
            r'雨|雪|雷|雾|霜|云|风|冰|冷|热|凉'))
        if not re.search(re_weather, message): return False, (None,)
        date_codes = {
            '今天': 0,
            '今日': 0,
            '现在': 0,
            '明天': 1,
            '明日': 1,
            '第二天': 1,
            '第二日': 1,
            '后天': 2,
            '后日': 2,
            '第三天': 2,
            '第三日': 2,
        }
        ad_code_list = []
        which_date_list = []
        try:
            results:DataFrame = transform_text_with_addrs(text_with_addrs=message, pos_sensitive=True)
            results = results.get(['adcode', '省', '市', '区', '省_pos', '市_pos', '区_pos'])
            for index, row in results.iterrows():
                pos_end = 0
                pos_start = row['区_pos']
                if pos_start == -1:
                    pos_start = row['市_pos']
                else:
                    pos_end = pos_start + len(row['区'])
                if pos_start == -1:
                    pos_start = row['省_pos']
                else:
                    pos_end = pos_start + len(row['市'])
                if pos_start == -1:
                    continue
                else:
                    pos_end = pos_start + len(row['省'])
                min_dist = Infinity
                date_code = -1
                for date, code in date_codes.items():
                    index_prefix = message.rfind(date, pos_start)
                    dist_prefix = Infinity if index_prefix == -1 else pos_start - index_prefix
                    index_suffix = message.find(date, pos_end)
                    dist_suffix = Infinity if index_suffix == -1 else index_suffix - pos_end
                    dist = min(dist_prefix, dist_suffix)
                    if dist < min_dist:
                        date_code = code
                        min_dist = dist
                date_code = 0 if date_code == -1 else date_code
                ad_code_list.append(row['adcode'])
                which_date_list.append(date_code)
            if len(ad_code_list) == 0: return False, (None, None)
        except Exception as e:
            return False, (None, None)
        return True, (ad_code_list, which_date_list)

    def invoke(self, data, **kwargs):
        """
        调用服务并返回信息
        """
        ad_code_list, which_date_list = data
        result = self.__real_query(ad_code_list=ad_code_list, which_date_list=which_date_list)
        if len(result):
            result = 'System enquired weather info:' + ''.join(result)
        else:
            result = '没有查询到相关天气信息'
        return result
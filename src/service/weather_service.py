from bs4 import BeautifulSoup
from cpca import transform_text_with_addrs
from logging import Logger
from numpy import Infinity
from pandas import DataFrame
import json
import requests.api as requests
import web

class WeatherServiceBing:
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']

    def __real_query(self, regions:list):
        """
        查询天气信息（必应）
        regions: 地区名称列表
        """
        try:
            results = []
            for region in regions:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63',
                }
                url = f'https://cn.bing.com/?q={web.urlquote(region + "天气")}'
                res = requests.get(url, headers=headers).text
                soup = BeautifulSoup(res, 'lxml')
                if not soup.find(class_='wtr_core'): return []
                # 获取实况天气信息
                now_weather_name = soup.find(class_='wtr_currIcon').attrs['aria-label']
                now_temperature = soup.find(class_='wtr_currTemp').attrs['data-val']
                now_temperature_high = soup.find(class_='wtr_high').next.text
                now_temperature_low = soup.find(class_='wtr_low').next.text
                now_perci = soup.find(class_='wtr_currPerci').next
                now_wind = soup.find(class_='wtr_currWind').next
                now_humidity = soup.find(class_='wtr_currHumi').next
                now = f"当前天气：{now_weather_name} 气温：{now_temperature}摄氏度 最高{now_temperature_high}摄氏度 最低{now_temperature_low}摄氏度 {now_perci} {now_wind} {now_humidity}"
                # 获取预报天气信息
                forecast = []
                for el in soup.find_all(class_='wtr_forecastDay'):
                    forecast.append(el.attrs['aria-label'])
                data = {
                    'now': now,
                    'forecast': forecast,
                }
                self.logger.info(data)
                results.append(json.dumps(data, ensure_ascii=False))
            return results
        except Exception as e:
            self.logger.error('查询天气信息失败：%s', e)
            return []

    def test(self, message:str):
        """
        从 message 中尝试提取天气查询信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
        regions = []
        try:
            results:DataFrame = transform_text_with_addrs(text_with_addrs=message, pos_sensitive=True)
            results = results.get(['省', '市', '区', '省_pos', '市_pos', '区_pos'])
            for index, row in results.iterrows():
                for type in ['区', '市', '省']:
                    pos_start = row[type + '_pos']
                    if pos_start != -1:
                        region = row[type]
                        break
                if pos_start == -1: continue
                regions.append(region)
            if len(regions) == 0: return False, (None,)
        except Exception as e:
            return False, (None,)
        return True, (regions,)

    def invoke(self, data, **kwargs):
        """
        调用服务并返回信息，否则返回 None
        """
        regions, = data
        result = self.__real_query(regions=regions)
        if len(result):
            result = 'System enquired weather info:' + ''.join(result)
        else:
            result = '没有查询到相关天气信息'
        return result

class WeatherServiceAmap:
    api_key = {}
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.api_key = kwargs['api_key']

    def __real_query(self, ad_code_list:list, which_date_list:list):
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

    def test(self, message:str):
        """
        从 message 中尝试提取天气查询信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
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
        调用服务并返回信息，否则返回 None
        """
        ad_code_list, which_date_list = data
        result = self.__real_query(ad_code_list=ad_code_list, which_date_list=which_date_list)
        if len(result):
            result = 'System enquired weather info:' + ''.join(result)
        else:
            result = '没有查询到相关天气信息'
        return result
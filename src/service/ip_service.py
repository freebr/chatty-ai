from logging import Logger
import json
import re
import requests.api as requests

class IpService:
    api_key = {}
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.api_key = kwargs['api_key']

    def __real_query(self, ip_list:list):
        """
        查询 IP 信息
        ip_list: IP 地址列表
        """
        try:
            if len(self.api_key) == 0: raise Exception('没有可用的 API key')
            api_key = self.api_key[0]
            results = []
            user_ip_info = requests.get('http://myip.ipip.net', timeout=60).text
            data = {
                'ip': re.search(r'当前 IP：([\d.]+)', user_ip_info)[1],
                'location': re.search(r'来自于：(.+)\n', user_ip_info)[1].strip(),
                'is user ip': True,
            }
            results.append(json.dumps(data, ensure_ascii=False))
            for ip in ip_list:
                # 获取信息
                url = f'https://restapi.amap.com/v3/ip?ip={ip}&key={api_key}'
                res = requests.get(url).json()
                adcode = res['adcode']
                if not adcode:
                    data = {
                        'ip': ip,
                        'location': 'oversea',
                    }
                else:
                    province = res['province']
                    city = res['city']
                    data = {
                        'ip': ip,
                        'location': province + city,
                    }
                results.append(json.dumps(data, ensure_ascii=False))
            return results
        except Exception as e:
            self.logger.error('查询 IP 地址信息失败：%s', e)
            return []

    def test(self, message:str):
        """
        从 message 中尝试提取 IP 地址查询信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
        ip_list = []
        try:
            for match in re.finditer(r'(?:[^\d]|^)(((25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\.){3}(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d))(?:[^\d]|$)', message):
                ip_list.append(match[1])
            if len(ip_list) == 0:
                if len(re.findall(r'IP', message, re.I)):
                    return True, []
                else:
                    return False, []
        except Exception as e:
            self.logger.error('命中测试出错：%s', e)
            return False, []
        return True, ip_list

    def invoke(self, data, **kwargs):
        """
        调用服务并返回信息，否则返回 None
        """
        ip_list = data
        result = self.__real_query(ip_list=ip_list)
        if len(result):
            result = 'System enquired IP info:' + ''.join(result)
        else:
            result = '没有查询到相关 IP 地址信息'
        return result
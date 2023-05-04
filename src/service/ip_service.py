import json
import re
import requests.api as requests
from logging import getLogger, Logger

from definition.cls import Singleton

class IpService(metaclass=Singleton):
    api_key = {}
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger("IPSERVICE")
        self.api_key = kwargs['api_key']

    def __real_query(self, ips: list):
        """
        查询 IP 信息
        ips: IP 地址列表
        """
        try:
            if len(self.api_key) == 0: raise Exception('没有可用的 API key')
            api_key = self.api_key[0]
            results = []
            for ip in ips:
                # 获取信息
                url = f'https://restapi.amap.com/v3/ip?ip={ip}&key={api_key}'
                res = requests.get(url).json()
                adcode = res['adcode']
                if not adcode:
                    data = {
                        'ip': ip,
                        'location': '海外',
                    }
                else:
                    province = res['province']
                    city = res['city']
                    data = {
                        'ip': ip,
                        'location': province + city,
                    }
                results.append(json.dumps(data, ensure_ascii=False))
            return '\n'.join(results)
        except Exception as e:
            self.logger.error('查询 IP 地址信息失败：%s', str(e))
            return ''

    def invoke(self, args):
        """
        调用服务并返回信息
        """
        ips = args.get('ip')
        if type(ips) == str: ips = [ips]
        result = self.__real_query(ips=ips)
        return result
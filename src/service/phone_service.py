from logging import Logger
import json
import re
import requests.api as requests

class PhoneService:
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']

    def __real_query(self, phone_list:list):
        """
        查询手机归属地和运营商信息
        phone_list: 手机号码列表
        """
        try:
            results = []
            for phone in phone_list:
                # 获取信息
                url = f'http://cx.shouji.360.cn/phonearea.php?number={phone}'
                res = requests.get(url).json()
                phone_data = res['data']
                sp = phone_data['sp']
                if not sp:
                    data = {
                        'phone': phone,
                        'location': 'oversea',
                    }
                else:
                    province = phone_data['province']
                    city = phone_data['city']
                    data = {
                        'ip': phone,
                        'location': province + city,
                        'provider': sp,
                    }
                results.append(json.dumps(data, ensure_ascii=False))
            return results
        except Exception as e:
            self.logger.error('查询手机归属地和运营商信息失败：%s', e)
            return []

    def test(self, message:str):
        """
        从 message 中尝试提取手机归属地和运营商查询信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
        mobile_list = []
        try:
            for match in re.finditer(r'(?:[^\d]|^)(1[3-9]\d{9})(?:[^\d]|$)', message):
                mobile_list.append(match[1])
            if len(mobile_list) == 0: return False, []
        except Exception as e:
            self.logger.error('命中测试出错：%s', e)
            return False, []
        return True, mobile_list

    def invoke(self, data, **kwargs):
        """
        调用服务并返回信息，否则返回 None
        """
        mobile_list = data
        result = self.__real_query(phone_list=mobile_list)
        if len(result):
            result = 'System enquired phone info:' + ''.join(result)
        else:
            result = '没有查询到相关手机号码信息'
        return result
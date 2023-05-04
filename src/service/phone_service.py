import json
import requests.api as requests
from logging import getLogger, Logger

from configure import Config
from definition.cls import Singleton

cfg = Config()
class PhoneService(metaclass=Singleton):
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger("PHONESERVICE")

    def __real_query(self, phone_numbers: list):
        """
        查询手机归属地和运营商信息
        phone_numbers: 手机号码列表
        """
        try:
            results = []
            for phone_number in phone_numbers:
                # 获取信息
                headers = {
                    'User-Agent': cfg.data.features['UserAgent'],
                }
                url = f'http://cx.shouji.360.cn/phonearea.php?number={phone_number}'
                res = requests.get(url, headers=headers).json()
                phone_data = res['data']
                sp = phone_data['sp']
                if not sp:
                    data = {
                        'phone': phone_number,
                        'location': 'oversea',
                    }
                else:
                    province = phone_data['province']
                    city = phone_data['city']
                    data = {
                        'phone': phone_number,
                        'location': province + city,
                        'provider': sp,
                    }
                results.append(f'电话{phone_number}的信息:' + json.dumps(data, ensure_ascii=False))
            return ''.join(results)
        except Exception as e:
            self.logger.error('查询手机归属地和运营商信息失败：%s', str(e))
            return ''

    def invoke(self, args):
        """
        调用服务并返回信息
        """
        phone_numbers = args.get('phone_number')
        if type(phone_numbers) == str: phone_numbers = [phone_numbers]
        result = self.__real_query(phone_numbers=phone_numbers)
        return result
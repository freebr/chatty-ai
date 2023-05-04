import _thread
import inspect
import json
import requests.api as requests
from logging import getLogger, Logger
from time import sleep
from types import FunctionType

from .key_token_manager import KeyTokenManager
from definition.cls import Singleton
from definition.const import URL_WEIXIN_BASE

key_token_mgr = KeyTokenManager()

# 刷新 access token 时的有效期截止时间 5 分钟
MAX_LEFT_TIME_UPDATE_TOKEN = 300
APP_PARAM = key_token_mgr.get_app_param()

class WxAccessTokenManager(metaclass=Singleton):
    __access_token = ''
    __update_left_time = 0
    APPID = ''
    APPSECRET = ''
    stop_signal: bool
    cb_success: FunctionType
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger(self.__class__.__name__)
        self.APPID = APP_PARAM['APPID']
        self.APPSECRET = APP_PARAM['APPSECRET']

    def update_access_token(self):
        try:
            url = f'{URL_WEIXIN_BASE}/stable_token'
            data = {
                'grant_type': 'client_credential',
                'appid': self.APPID,
                'secret': self.APPSECRET,
                'force_refresh': False,
            }
            res = requests.post(url, data=json.dumps(data)).json()
            if 'access_token' not in res: raise Exception('access token 获取失败，响应：{}'.format(json.dumps(res, ensure_ascii=False)))
            self.__access_token = res['access_token']
            self.__update_left_time = res['expires_in']
            self.logger.info('微信 access token 已更新，有效期：%ss', self.__update_left_time)
        except Exception as e:
            self.logger.error('更新微信 access token 失败：%s', str(e))
            return False
        return True

    def get_access_token(self):
        return self.__access_token

    def start(self, cb_success):
        self.stop_signal = False
        self.cb_success = cb_success
        self.work_thread = _thread.start_new_thread(self.main, ())

    def stop(self):
        self.stop_signal = True

    def main(self):
        while not self.stop_signal:
            # 在有效期截止指定时间内刷新 access token
            if self.__update_left_time > MAX_LEFT_TIME_UPDATE_TOKEN:
                sleep(2)
                self.__update_left_time -= 2
            else:
                # 若更新不成功，则等待 10 秒后重试
                if not self.update_access_token():
                    sleep(10)
                    self.__update_left_time = 0
                else:
                    if inspect.isfunction(self.cb_success): self.cb_success(self.__access_token)
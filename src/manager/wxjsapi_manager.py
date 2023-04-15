from helper.formatter import convert_encoding
from logging import Logger
from var import APP_PARAM
import hashlib
import json
import random
import requests
import string
import time

jsapi_ticket_info = {
    'ticket': '',
    'expire_time': 0,
}
class WxJsApiManager(object):
    """
    - 给前端 JSSDK 构造参数，并得到 nonceStr, timestamp, signature 的类，调用`signutareEncryption()`即可
    - signature生成需要以下几个参数：
        - nonceStr
        - timestamp
        - 有效的jsapi_ticket
        - url（公众号页面）
    - 针对指定的 openid 生成和刷新 access token，获取用户信息
    """
    token_info: dict
    """
    access_token	网页授权接口调用凭证,注意：此access_token与基础支持的access_token不同
    expires_in	    access_token接口调用凭证超时时间，单位（秒）
    refresh_token	用户刷新access_token
    openid	        用户唯一标识，请注意，在未关注公众号时，用户访问公众号的网页，也会产生一个用户和公众号唯一的OpenID
    scope	        用户授权的作用域，使用逗号（,）分隔
    is_snapshotuser	是否为快照页模式虚拟账号，只有当用户是快照页模式虚拟账号时返回，值为1
    unionid	        用户统一标识（针对一个微信开放平台帐号下的应用，同一用户的 unionid 是唯一的），只有当scope为"snsapi_userinfo"时返回
    """
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.param_template = {
            'timestamp': self.__create_timestamp(),
            'nonceStr': self.__create_nonce_str(),
        }
        self.token_info = {}

    def update_access_token(self, access_token):
        self.access_token = access_token
        self.url_getticket = f'https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={self.access_token}&type=jsapi'

    def get_sign_param(self, url):
        self.param_template['url'] = url
        result = {
            'timestamp': self.param_template.get('timestamp'),
            'nonceStr': self.param_template.get('nonceStr'),
            'signature': self.__get_sign(),
        }
        return result

    def get_wx_user_info(self, code):
        try:
            access_token, openid = self.__get_wx_jsapi_access_token(code)
            if not access_token: raise Exception('获取网页授权 access token 失败')
            if not openid: raise Exception('获取网页授权 openid 失败')
            url = f'https://api.weixin.qq.com/sns/userinfo?access_token={access_token}&openid={openid}&lang=zh_CN'
            res = requests.get(url)
            body = convert_encoding(res.text)
            data:dict = json.loads(body)
            self.logger.info('获取微信用户信息成功，user_info=%s', data)
            return data
        except Exception as e:
            self.logger.error('获取微信用户信息失败：%s，openid=%s', str(e), openid)
            return {}

    def __get_wx_jsapi_access_token(self, code):
        try:
            if not code: raise Exception('缺少 code')
            if self.token_info.get(code):
                if self.token_info[code]['expires_at'] <= time.time():
                    # 前次 access token 到期，刷新
                    return self.__refresh_wx_jsapi_access_token(code, self.token_info[code]['refresh_token'])
                else:
                    return self.token_info[code]['access_token']
            url = f"https://api.weixin.qq.com/sns/oauth2/access_token?appid={APP_PARAM['APPID']}&secret={APP_PARAM['APPSECRET']}&code={code}&grant_type=authorization_code"
            res = requests.get(url)
            data:dict = res.json()
            self.logger.info(data)
            data['expires_at'] = int(time.time()) + int(data['expires_in'])
            self.token_info[code] = data
            self.logger.info('获取网页授权 access token 成功，openid=%s，code=%s', data['openid'], code)
            return data['access_token'], data['openid']
        except Exception as e:
            self.logger.error('获取网页授权 access token 失败：%s，code=%s', str(e), code)
            return
    
    def __refresh_wx_jsapi_access_token(self, code, refresh_token):
        try:
            if not code: raise Exception('缺少 code')
            if not refresh_token: raise Exception('缺少 refresh_token')
            url = f"https://api.weixin.qq.com/sns/oauth2/refresh_token?appid={APP_PARAM['APPID']}&grant_type=refresh_token&refresh_token={refresh_token}"
            res = requests.get(url)
            data:dict = res.json()
            data['expires_at'] = int(time.time()) + int(data['expires_in'])
            for key in data.keys():
                self.token_info[code][key] = data[key]
            return data['access_token']
        except Exception as e:
            self.logger.error('刷新网页授权 access token 失败：%s，code=%s', str(e), code)
            return
    
    def __get_sign(self):
        """
        生成 SHA1 签名
        """
        self.param_template['jsapi_ticket'] = self.__get_ticket()
        string = '&'.join(['%s=%s' % (key.lower(), self.param_template[key]) for key in sorted(self.param_template)]).encode('utf-8')
        sign = hashlib.sha1(string).hexdigest()
        self.logger.info("生成 SHA1 签名成功\nURL=%s\nsign=%s", self.param_template['url'], sign)
        return sign

    def __get_ticket(self):
        """
        获取 jsapi_ticket
        """
        try:
            if jsapi_ticket_info['expire_time'] <= time.time():
                ticket = requests.get(self.url_getticket).json()['ticket']
                expire_time = self.__create_timestamp() + 7000  # max=7200
                jsapi_ticket_info['expire_time'] = expire_time
                jsapi_ticket_info['ticket'] = ticket
                self.logger.info("获取 jsapi_ticket 成功，有效期至：%d", expire_time)
            else:
                ticket = jsapi_ticket_info['ticket']
                expire_time = jsapi_ticket_info['expire_time']
                self.logger.info("获取 jsapi_ticket 成功（缓存），有效期至：%d", expire_time)
        except Exception as e:
            self.logger.error("获取 jsapi_ticket 失败：%s", str(e))
            ticket = ''
        return ticket

    def __create_nonce_str(self):
        """
        从a-zA-Z0-9生成指定数量的随机字符
        """
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))

    def __create_timestamp(self):
        """
        生成时间戳
        """
        return int(time.time())
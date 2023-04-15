from .qrcode_manager import QRCodeManager
from const import DIR_CERT_WXPAY, DIR_CONFIG, DIR_IMAGES_TEMPLATE, DIR_USERS
from logging import Logger
from os import environ, mkdir, path
from PIL import Image
from wechatpayv3 import WeChatPay, WeChatPayType
import inspect
import json
import time
import uuid
import web
import yaml

# 商户证书私钥
with open(path.abspath(path.join(DIR_CERT_WXPAY, 'key/apiclient_key.pem'))) as f:
    PRIVATE_KEY = f.read()

# 回调地址，也可以在调用接口的时候覆盖
NOTIFY_URL = environ['URL_SITE_BASE'] + '/pay/notify'

# 微信支付平台证书缓存目录，减少证书下载调用次数，首次使用确保此目录为空目录.
# 初始调试时可不设置，调试通过后再设置
CERT_DIR = path.abspath(path.join(DIR_CERT_WXPAY, 'client'))

# 接入模式:False=直连商户模式，True=服务商模式
PARTNER_MODE = False

# 代理设置，None或者{'https': 'http://10.10.1.10:1080'}，详细格式参见https://docs.python-requests.org/zh_CN/latest/user/advanced.html
PROXY = None

class PaymentManager:
    # API v3 密钥，详见 https://pay.weixin.qq.com/wiki/doc/apiv3/wechatpay/wechatpay3_2.shtml
    APIV3_KEY: str
    # APPID，应用ID或服务商模式下的 sp_appid
    APPID: str
    # 商户证书序列号
    CERT_SERIAL_NO: str
    # 微信支付商户号（直连模式）或服务商商户号（服务商模式，即 sp_mchid）
    MCHID: str
    qrcode_mgr = None
    pay_qrcode_template_file_path: str = path.join(DIR_IMAGES_TEMPLATE, 'pay-qrcode-template.jpg')
    pay_info: dict
    file_path_config: str
    file_path_pay_info: str
    levels: dict
    wxpay = None
    payment_success_callback = None
    workdir: str
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.file_path_config = path.abspath(path.join(DIR_CONFIG, 'wx-pay.yml'))
        self.file_path_pay_info = path.abspath(path.join(DIR_USERS, 'pay-info.yml'))
        self.levels = kwargs['levels']
        self.workdir = kwargs['workdir']
        self.read_config()
        self.read_pay_info()
        self.qrcode_mgr = QRCodeManager(logger=self.logger)
        self.wxpay = WeChatPay(
            wechatpay_type=WeChatPayType.JSAPI,
            mchid=self.MCHID,
            private_key=PRIVATE_KEY,
            cert_serial_no=self.CERT_SERIAL_NO,
            apiv3_key=self.APIV3_KEY,
            appid=self.APPID,
            notify_url=NOTIFY_URL,
            cert_dir=CERT_DIR,
            logger=self.logger,
            partner_mode=PARTNER_MODE,
            proxy=PROXY,
        )

    def create_out_trade_no():
        """
        生成订单号
        """
        return 'CH' + str(round(time.time()))

    def create_jsapi_pay(self, openid, description, price):
        """
        创建 JSAPI 支付订单
        """
        try:
            out_trade_no = self.create_out_trade_no()
            amount = int(price * 100)
            payer = { 'openid': openid }
            code, message = self.wxpay.pay(
                description=description,
                out_trade_no=out_trade_no,
                amount={ 'total': amount },
                pay_type=WeChatPayType.JSAPI,
                payer=payer,
            )
            res = json.loads(message)
            if code in range(200, 300):
                self.logger.info('订单已生成：%s/%s', description, out_trade_no)
                prepay_id = res.get('prepay_id')
                timestamp = str(round(time.time()))
                noncestr = str(uuid.uuid3(uuid.uuid4(), openid))
                package = 'prepay_id=' + prepay_id
                paysign = self.wxpay.sign([self.APPID, timestamp, noncestr, package])
                signtype = 'RSA'
                return {
                    'code': 0,
                    'result': {
                        'appId': self.APPID,
                        'timeStamp': timestamp,
                        'nonceStr': noncestr,
                        'package': 'prepay_id=%s' % prepay_id,
                        'signType': signtype,
                        'paySign': paysign,
                    },
                }
            else:
                return {
                    'code': -1,
                    'result': {
                        'reason': res.get('code'),
                    },
                }
        except Exception as e:
            return e

    def create_native_pay(self, description, price, to_file=True):
        """
        创建 Native 支付订单
        """
        try:
            out_trade_no = self.create_out_trade_no()
            amount = int(price * 100)
            code, message = self.wxpay.pay(
                description=description,
                out_trade_no=out_trade_no,
                amount={ 'total': amount },
                pay_type=WeChatPayType.NATIVE,
            )
            res = json.loads(message)
            if 'code_url' not in res: raise Exception(message)
            code_url = res['code_url']
            self.logger.info('订单已生成：%s', out_trade_no)
            # 生成支付二维码
            im_qrcode = self.qrcode_mgr.generate_qrcode(data=code_url, usage='打赏')
            im_pay = Image.open(self.pay_qrcode_template_file_path)
            im_pay.paste(im_qrcode, (223, 335), mask=None)
            if to_file:
                img_name = out_trade_no + '.jpg'
                image_path = path.abspath(path.join(self.workdir, img_name))
                if not path.exists(self.workdir): mkdir(self.workdir)
                im_pay.save(image_path)
                return image_path, out_trade_no
            else:
                return im_pay, out_trade_no
        except Exception as e:
            return e

    def notify_pay(self):
        """
        处理支付通知
        """
        headers = web.ctx.env
        new_headers = {}
        new_headers.update({'Wechatpay-Signature': headers.get('HTTP_WECHATPAY_SIGNATURE')})
        new_headers.update({'Wechatpay-Timestamp': headers.get('HTTP_WECHATPAY_TIMESTAMP')})
        new_headers.update({'Wechatpay-Nonce': headers.get('HTTP_WECHATPAY_NONCE')})
        new_headers.update({'Wechatpay-Serial': headers.get('HTTP_WECHATPAY_SERIAL')})
        result = self.wxpay.callback(new_headers, web.data())
        if result and result.get('event_type') == 'TRANSACTION.SUCCESS':
            res = result.get('resource')
            appid = res.get('appid')
            mchid = res.get('mchid')
            out_trade_no = res.get('out_trade_no')
            transaction_id = res.get('transaction_id')
            trade_type = res.get('trade_type')
            trade_state = res.get('trade_state')
            trade_state_desc = res.get('trade_state_desc')
            bank_type = res.get('bank_type')
            attach = res.get('attach')
            success_time = res.get('success_time')
            payer = res.get('payer')
            amount = res.get('amount').get('total')
            # 根据返回参数进行必要的业务处理，处理完后返回200或204
            self.logger.info('收到微信支付回调通知，用户：%s，订单号：%s，金额：¥%s，交易状态：%s',
                payer, out_trade_no, amount / 100, trade_state_desc,
            )
            if inspect.ismethod(self.payment_success_callback):
                if self.payment_success_callback(openid=payer.get('openid'), out_trade_no=out_trade_no, amount=amount):
                    return {'code': 'SUCCESS', 'message': '成功'}
                else:
                    return {'code': 'FAIL', 'message': '失败'}
            else:
                return {'code': 'SUCCESS', 'message': '成功'}
        else:
            message = result.get('event_type') if result else 'result 为空'
            self.logger.error('微信支付回调通知失败：%s', message)
            return {'code': 'FAIL', 'message': message}

    def set_payment_success_callback(self, func):
        """
        设置支付成功后调用的函数
        """
        self.payment_success_callback = func
        
    def read_config(self):
        try:
            if not path.isfile(self.file_path_config):
                self.logger.error('微信支付配置加载失败，找不到文件：%s', self.file_path_config)
                return False
            result:dict
            with open(self.file_path_config, 'r') as f:
                result = yaml.load(f, Loader=yaml.FullLoader)
            if not result: raise Exception('微信支付配置加载失败')
            self.APIV3_KEY = result['APIV3_KEY']
            self.APPID = result['APPID']
            self.CERT_SERIAL_NO = result['CERT_SERIAL_NO']
            self.MCHID = result['MCHID']
            self.logger.info('微信支付配置加载成功')
            return True
        except Exception as e:
            self.logger.error('微信支付配置加载失败：%s', str(e))
            return False
            
    def read_pay_info(self):
        """
        读取支付信息列表
        """
        try:
            self.pay_info = {}
            if not self.file_path_pay_info: raise Exception('找不到支付信息列表文件')
            if not path.isfile(self.file_path_pay_info):
                self.init_pay_info()
                return False
            result:dict
            with open(self.file_path_pay_info, 'r') as f:
                result = yaml.load(f, Loader=yaml.FullLoader)
            if not result: raise Exception('支付信息列表加载失败')
            self.pay_info = result
            self.logger.info('支付信息列表加载成功')
            return True
        except Exception as e:
            self.logger.error('支付信息列表加载失败：%s', str(e))
            return False

    def save_pay_info(self):
        """
        保存支付信息列表
        """
        try:
            with open(self.file_path_pay_info, mode='w', encoding='utf-8', errors='ignore') as f:
                yaml.dump(self.pay_info, f, allow_unicode=True)
            self.logger.info('支付信息列表加载成功')
            return True
        except Exception as e:
            self.logger.error('支付信息列表保存失败：%s', str(e))
            return False

    def init_pay_info(self):
        """
        初始化支付信息列表
        """
        stat_list = {}
        for level in self.levels:
            stat_list[level] = {
                'Count': 0,
                'EnableTime':  time.ctime(),
                'LastBuy': [],
            }
        self.pay_info = {
            'Statistics': stat_list,
            'PayList': {},
        }
        self.save_pay_info()

    def add_pay_info(self, **kwargs):
        """
        增加支付结果
        """
        stat_list = self.pay_info.get('Statistics')
        pay_list = self.pay_info.get('PayList', {})
        if not stat_list: raise Exception('支付信息列表已损坏，请修复')
        openid = kwargs['openid']
        headimgurl = kwargs['headimgurl']
        pay_level = kwargs['pay_level']
        before_level = kwargs['before_level']
        pay_time = kwargs['pay_time']
        out_trade_no = kwargs['out_trade_no']
        pay_list[openid] = {
            'PayLevel': pay_level,
            'BeforeLevel': before_level,
            'PayTime': pay_time,
            'OutTradeNo': out_trade_no,
        }
        stat_level = stat_list[pay_level]
        if not stat_level: raise Exception('支付信息列表已损坏，请修复后再执行操作')
        stat_level['Count'] += 1
        last_buy = stat_level['LastBuy']
        if len(last_buy) >= 5: last_buy.pop(0)
        last_buy.append({
            'User': openid,
            'HeadImgUrl': headimgurl,
            'PayTime': pay_time,
        })
        self.pay_info['PayList'] = pay_list
        self.save_pay_info()
        self.logger.info('用户 %s 的支付信息已记录', openid)

    def remove_pay_info(self, openid):
        """
        根据给定的 openid 删除支付结果
        """
        pay_list = self.pay_info.get('PayList', {})
        removed_pay_info = pay_list.get(openid)
        if not removed_pay_info: return False
        stat_list = self.pay_info.get('Statistics')
        if not stat_list: raise Exception('支付信息列表已损坏，请修复')
        stat_level = stat_list.get(removed_pay_info['pay_level'])
        if not stat_level: raise Exception('支付信息列表已损坏，请修复后再执行操作')
        pay_list.pop(openid)
        stat_level['Count'] -= 1
        self.pay_info['PayList'] = pay_list
        self.save_pay_info()
        self.logger.info('用户 %s 的支付信息已删除', openid)
        return True

    def refund_pay_info(self, openid, **kwargs):
        """
        根据给定的 openid 记录退款结果
        """
        pay_list = self.pay_info.get('PayList', {})
        refund_pay_info = pay_list.get(openid)
        if not refund_pay_info: return False
        stat_level = self.pay_info.get('Statistics').get(refund_pay_info['pay_level'])
        if not stat_level: raise Exception('支付信息列表已损坏，请修复后再执行操作')
        refund_time = kwargs['refund_time']
        refund_amount = kwargs['refund_amount']
        refund_memo = kwargs['refund_memo']
        refund_pay_info['Refund'] = {
            'Time': refund_time,
            'Amount': refund_amount,
            'Memo': refund_memo,
        }
        stat_level['Count'] -= 1
        self.pay_info['PayList'] = pay_list
        self.save_pay_info()
        self.logger.info('用户 %s 的支付退款信息已记录', openid)
        return True

    def get_pay_info(self, openid):
        """
        根据给定的 openid 获取支付结果
        """
        pay_info = self.pay_info.get('PayList', {}).get(openid)
        return pay_info

from .qrcode_manager import QRCodeManager
from configure import Config
from definition.cls import Singleton
from definition.const import DIR_CERT_WXPAY, DIR_IMAGES_TEMPLATE, DIR_USERS, URL_API
from logging import getLogger, Logger
from os import mkdir, path
from PIL import Image
from wechatpayv3 import WeChatPay, WeChatPayType
import inspect
import json
import time
import uuid
import web
import yaml

cfg = Config()

# 商户证书私钥
with open(path.abspath(path.join(DIR_CERT_WXPAY, 'key/apiclient_key.pem'))) as f:
    PRIVATE_KEY = f.read()

# 回调地址，也可以在调用接口的时候覆盖
NOTIFY_URL = path.join(URL_API, 'pay/notify')

# 微信支付平台证书缓存目录，减少证书下载调用次数，首次使用确保此目录为空目录.
# 初始调试时可不设置，调试通过后再设置
CERT_DIR = path.abspath(path.join(DIR_CERT_WXPAY, 'client'))

# 接入模式:False=直连商户模式，True=服务商模式
PARTNER_MODE = False

# 代理设置，None或者{'https': 'http://10.10.1.10:1080'}，详细格式参见https://docs.python-requests.org/zh_CN/latest/user/advanced.html
PROXY = None

class PaymentManager(metaclass=Singleton):
    # API v3 密钥，详见 https://pay.weixin.qq.com/wiki/doc/apiv3/wechatpay/wechatpay3_2.shtml
    APIV3_KEY: str
    # APPID，应用ID或服务商模式下的 sp_appid
    APPID: str
    # 商户证书序列号
    CERT_SERIAL_NO: str
    # 微信支付商户号（直连模式）或服务商商户号（服务商模式，即 sp_mchid）
    MCHID: str
    levels: dict
    pay_info_file_path: str
    pay_info: dict
    pay_qrcode_template_file_path: str
    payment_success_callback = None
    qrcode_mgr = None
    workdir: str
    wxpay = None
    wxpay_config: dict
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger(self.__class__.__name__)
        self.pay_qrcode_template_file_path = path.join(DIR_IMAGES_TEMPLATE, 'pay-qrcode-template.jpg')
        self.pay_info_file_path = path.abspath(path.join(DIR_USERS, 'pay-info.yaml'))
        self.levels = kwargs['levels']
        self.workdir = kwargs['workdir']
        self.load_config()
        self.load_pay_info()
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

    def create_out_trade_no(self):
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
                self.logger.error('生成订单 %s 时出错：%s', out_trade_no, res.get('code'))
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
            im_pay: Image.Image = Image.open(self.pay_qrcode_template_file_path)
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
        self.logger.info('收到微信支付回调通知：%s', web.data())
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
            pay_amount = res.get('amount').get('total')
            # 根据返回参数进行必要的业务处理，处理完后返回200或204
            self.logger.info('微信支付回调通知信息：用户：%s，订单号：%s，金额：¥%s，交易状态：%s',
                payer, out_trade_no, pay_amount / 100, trade_state_desc,
            )
            if inspect.ismethod(self.payment_success_callback):
                if self.payment_success_callback(openid=payer.get('openid'), out_trade_no=out_trade_no, pay_amount=pay_amount):
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
        
    def load_config(self):
        try:
            self.wxpay_config = cfg.data.wxpay
            self.APIV3_KEY = str(self.wxpay_config['APIV3_KEY'])
            self.APPID = str(self.wxpay_config['APPID'])
            self.CERT_SERIAL_NO = str(self.wxpay_config['CERT_SERIAL_NO'])
            self.MCHID = str(self.wxpay_config['MCHID'])
            self.logger.info('微信支付配置加载成功')
            return True
        except Exception as e:
            self.logger.error('微信支付配置加载失败：%s', str(e))
            return False
            
    def load_pay_info(self):
        """
        读取支付信息列表
        """
        try:
            self.pay_info = {}
            if not self.pay_info_file_path: raise Exception('找不到支付信息列表文件')
            if not path.isfile(self.pay_info_file_path):
                self.init_pay_info()
                return False
            result: dict
            with open(self.pay_info_file_path, 'r', encoding='utf-8', errors='ignore') as f:
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
            with open(self.pay_info_file_path, mode='w', encoding='utf-8', errors='ignore') as f:
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
        # 支付金额，单位为分
        pay_amount = int(kwargs['pay_amount'])
        pay_time = kwargs['pay_time']
        out_trade_no = kwargs['out_trade_no']
        pay_list[out_trade_no] = {
            'BeforeLevel': before_level,
            'PayAmount': pay_amount,
            'PayLevel': pay_level,
            'PayTime': pay_time,
            'OutTradeNo': out_trade_no,
            'UserId': openid,
        }
        if pay_level:
            stat_level = stat_list.get(pay_level)
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

    def remove_pay_info(self, out_trade_no):
        """
        根据给定的 out_trade_no 删除支付结果
        """
        pay_list = self.pay_info.get('PayList', {})
        removed_pay_info = pay_list.get(out_trade_no)
        if not removed_pay_info: return False
        stat_list = self.pay_info.get('Statistics')
        if not stat_list: raise Exception('支付信息列表已损坏，请修复')
        stat_level = stat_list.get(removed_pay_info['pay_level'])
        if not stat_level: raise Exception('支付信息列表已损坏，请修复后再执行操作')
        openid = removed_pay_info['UserId']
        pay_list.pop(out_trade_no)
        stat_level['Count'] -= 1
        self.pay_info['PayList'] = pay_list
        self.save_pay_info()
        self.logger.info('支付信息[用户 %s 交易单号 %s]已删除', openid, out_trade_no)
        return True

    def refund_pay_info(self, out_trade_no, **kwargs):
        """
        根据给定的 out_trade_no 记录退款结果
        """
        pay_list = self.pay_info.get('PayList', {})
        refund_pay_info = pay_list.get(out_trade_no)
        if not refund_pay_info: return False
        stat_level = self.pay_info.get('Statistics').get(refund_pay_info['pay_level'])
        if not stat_level: raise Exception('支付信息列表已损坏，请修复后再执行操作')
        openid = refund_pay_info['UserId']
        refund_time = kwargs['refund_time']
        # 退款金额，单位为分
        refund_amount = int(kwargs['refund_amount'])
        refund_memo = kwargs['refund_memo']
        refund_pay_info['Refund'] = {
            'Time': refund_time,
            'RefundAmount': refund_amount,
            'Memo': refund_memo,
        }
        stat_level['Count'] -= 1
        self.pay_info['PayList'] = pay_list
        self.save_pay_info()
        self.logger.info('支付信息[用户 %s 交易单号 %s]已添加退款记录', openid, out_trade_no)
        return True

    def get_pay_info_by_openid(self, openid):
        """
        根据给定的 openid 获取支付信息列表
        """
        pay_infos = [ info for info in self.pay_info.get('PayList', {}).values() if info['UserId'] == openid ]
        return pay_infos

    def get_pay_info_by_out_trade_no(self, out_trade_no):
        """
        根据给定的 out_trade_no 获取支付信息
        """
        pay_info = self.pay_info.get('PayList', {}).get(out_trade_no)
        return pay_info

    def get_paid_amount_by_openid(self, openid):
        """
        查询给定的 openid 已支付成功且无退回的金额（单位为分）
        """
        pay_amounts = [info['PayAmount'] for info in self.pay_info.get('PayList', {}).values() if info['UserId'] == openid ]
        return sum(pay_amounts)

import _thread
from logging import getLogger
from numpy import Infinity

from definition.const import DIR_IMAGES_QRCODE
from .article_manager import ArticleManager
from .autoreply_manager import AutoReplyManager
from .chatgroup_manager import ChatgroupManager
from .img2img_manager import Img2ImgManager
from .key_token_manager import KeyTokenManager
from .payment_manager import PaymentManager
from .poster_manager import PosterManager
from .user_manager import UserManager
from .voices_manager import VoicesManager
from .wx_access_token_manager import WxAccessTokenManager
from .wxjsapi_manager import WxJsApiManager

from monitor.user_monitor import UserMonitor

key_token_mgr = KeyTokenManager()
img2img_mgr = Img2ImgManager()
user_mgr = UserManager(
    vip_levels=[
        '白银',
        '黄金',
        '铂金',
    ],
    free_level='青铜',
    highest_level='铂金',
    vip_prices=[
        4.9,
        19.9,
        49.9,
    ],
    vip_rights=[
        '可享受无限期100次体验额度（额度用完后，观看广告可自动获得新的100次额度）',
        '可享受无限期500次体验额度（额度用完后，观看广告可自动获得新的500次额度）',
        '可享受无限次体验文字和图片生成服务，无需观看广告',
    ],
)
user_mon = UserMonitor(
    user_mgr=user_mgr,
)
_thread.start_new_thread(user_mon.run, ())
wx_access_token_mgr = WxAccessTokenManager()
wx_access_token_mgr.start(lambda access_token: (key_token_mgr.access_tokens.update({'WeChat': access_token}), key_token_mgr.save()))

payment_mgr = PaymentManager(
    workdir=DIR_IMAGES_QRCODE,
    levels=user_mgr.vip_levels,
)
poster_mgr = PosterManager()
autoreply_mgr = AutoReplyManager()
article_mgr = ArticleManager()
chatgroup_mgr = ChatgroupManager()
voices_mgr = VoicesManager()
wxjsapi_mgr = WxJsApiManager()
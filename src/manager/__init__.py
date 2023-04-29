import _thread

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

from configure import Config
from monitor.user_monitor import UserMonitor

cfg = Config()
key_token_mgr = KeyTokenManager()
img2img_mgr = Img2ImgManager()
user_mgr = UserManager(
    free_level=cfg.data.levels.get('FreeLevel'),
    top_level=cfg.data.levels.get('TopLevel'),
    vip_levels=[ level_name for level_name, level_info in cfg.data.levels.get('Definition').items() if level_info.get('Vip', False) ],
    vip_prices=[ level_info.get('Price') for level_info in cfg.data.levels.get('Definition').values() if level_info.get('Vip', False) ],
    vip_purchasable=[ level_info.get('Purchasable', True) for level_info in cfg.data.levels.get('Definition').values() if level_info.get('Vip', False) ],
    vip_rights=[ level_info.get('Rights') for level_info in cfg.data.levels.get('Definition').values() if level_info.get('Vip', False) ],
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
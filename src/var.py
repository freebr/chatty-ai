import _thread
from const import DIR_CONFIG, DIR_IMAGES_IMG2IMG
from logging import getLogger
from manager.img2img_manager import Img2ImgManager
from manager.key_token_manager import KeyTokenManager
from manager.user_manager import UserManager
from monitor.user_monitor import UserMonitor
from manager.wx_access_token_manager import WxAccessTokenManager
from numpy import Infinity
from service.bot_service import BotService

key_token_mgr = KeyTokenManager(
    logger=getLogger('KEYTOKENMGR'),
    workdir=DIR_CONFIG,
)
APP_PARAM = {
    name: key_token_mgr.configs.get('api_keys').get('App').get(name)
    for name in ['APPID', 'APPSECRET', 'APPTOKEN', 'ENCODING_AES_KEY']
}
bot = BotService(
    logger=getLogger('BOT'),
    access_tokens=key_token_mgr.configs.get('access_tokens').get('Services'),
    api_keys=key_token_mgr.configs.get('api_keys').get('Services'),
)
img2img_mgr = Img2ImgManager(
    logger=getLogger('IMG2IMGMGR'),
    api_keys=key_token_mgr.configs.get('api_keys').get('Img2Img'),
    workdir=DIR_IMAGES_IMG2IMG,
)
user_mgr = UserManager(
    logger=getLogger('USERMGR'),
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
    quota={
        '青铜': {
            'completion': 10,
            'image': 10,
        },
        '白银': {
            'completion': 100,
            'image': 100,
        },
        '黄金': {
            'completion': 500,
            'image': 500,
        },
        '铂金': {
            'completion': Infinity,
            'image': Infinity,
        },
    },
)
user_mon = UserMonitor(
    logger=getLogger('USERMON'),
    user_mgr=user_mgr,
)
_thread.start_new_thread(user_mon.run, ())
wx_access_token_mgr = WxAccessTokenManager(
    logger=getLogger('WXACCESSTOKENMGR'),
    APPID=APP_PARAM['APPID'],
    APPSECRET=APP_PARAM['APPSECRET'],
)
wx_access_token_mgr.start(lambda access_token: (key_token_mgr.configs.get('access_tokens').update({'WeChat': access_token}), key_token_mgr.save('access_tokens')))

# 开启 Websocket 服务器的数量
COUNT_WEBSOCKET_INSTANCE = 1
def setWebsocketInstanceCount(new_count:int):
    global COUNT_WEBSOCKET_INSTANCE
    if not 1 < new_count < 100: return
    COUNT_WEBSOCKET_INSTANCE = new_count

def getWebsocketInstanceCount():
    return COUNT_WEBSOCKET_INSTANCE
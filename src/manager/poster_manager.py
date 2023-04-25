import os
import time
from logging import getLogger, Logger
from PIL import Image, ImageDraw, ImageFont

from definition.cls import Singleton
from definition.const import DIR_IMAGES_TEMPLATE, DIR_IMAGES_POSTER
from manager.qrcode_manager import QRCodeManager

class PosterManager(metaclass=Singleton):
    logger: Logger = None
    qrcode_mgr: QRCodeManager
    def __init__(self, **kwargs):
        self.logger = getLogger('POSTERMGR')
        self.qrcode_mgr = QRCodeManager(logger=self.logger)

    def make_poster(self, openid, nickname, headimg_path):
        code_url = f'https://open.weixin.qq.com/connect/oauth2/authorize?appid=wx13629cb66f9315e5&redirect_uri=https%3A%2F%2Ffreebr.cn%2Foxf%2Fchat%2F&response_type=code&scope=snsapi_userinfo&state={openid}#wechat_redirect'
        app_logo_path = os.path.join(DIR_IMAGES_TEMPLATE, 'app-logo.png')
        poster_tmpl_path = os.path.join(DIR_IMAGES_TEMPLATE, 'poster.jpg')
        font_path = os.path.join(DIR_IMAGES_TEMPLATE, 'msyh.ttc')
        poster_name = str(round(time.time())) + '.jpg'
        poster_path = os.path.abspath(os.path.join(DIR_IMAGES_POSTER, poster_name))
        try:
            # 生成二维码
            qrcode_mgr = QRCodeManager(logger=self.logger)
            im_qrcode = qrcode_mgr.generate_qrcode(data=code_url, usage='查小特AI网页版', version=2, box_size=5, border=4, logo=app_logo_path)
            im_poster = Image.open(poster_tmpl_path)
            # 叠加二维码
            im_poster.paste(im_qrcode, (550, 1020), mask=None)
            # 叠加微信头像
            im_headimg_before = Image.open(headimg_path)
            delimeter = 125
            im_headimg_before.resize((delimeter, delimeter), Image.ANTIALIAS)
            # 最后生成圆的半径
            radius = int(delimeter / 2)
            im_headimg_after = Image.new('RGBA', (delimeter, delimeter), (255, 255, 255, 0))
            pim_before = im_headimg_before.load()
            pim_after = im_headimg_after.load()
            pim_poster = im_poster.load()
            origin_headimg = (82, 1145)
            for i in range(delimeter):
                for j in range(delimeter):
                    lx, ly = abs(i - radius), abs(j - radius)
                    l = (pow(lx, 2) + pow(ly, 2))**0.5
                    if l < radius-4:
                        pim_after[i, j] = pim_before[i, j]
                    else:
                        pim_after[i, j] = pim_poster[i + origin_headimg[0], j + origin_headimg[1]]
            im_poster.paste(im_headimg_after, origin_headimg, mask=None)
            # 叠加微信昵称
            draw = ImageDraw.Draw(im_poster)
            font = ImageFont.truetype(font_path, 34)
            text = nickname if len(nickname) <= 8 else (nickname[:8] + '…')
            draw.text((230, 1160), text, fill='#000', font=font, align='left')
            # 保存文件
            if not os.path.exists(DIR_IMAGES_POSTER): os.mkdir(DIR_IMAGES_POSTER)
            im_poster.save(poster_path)
            self.logger.info('生成海报成功，文件名：%s', poster_name)
            return poster_name, poster_path
        except Exception as e:
            self.logger.error('生成海报失败：%s', str(e))
            return None, None
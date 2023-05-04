from logging import getLogger, Logger
from os import path
from PIL import Image

import qrcode
from definition.cls import Singleton
from definition.const import DIR_IMAGES_TEMPLATE

class QRCodeManager(metaclass=Singleton):
    logo_file_path: str = path.join(DIR_IMAGES_TEMPLATE, 'qrcode-logo.jpg')
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        
    def generate_qrcode(self, data, usage='', version=7, box_size=8, border=0, logo=''):
        """
        根据给出的 data 生成二维码
        """
        try:
            qr = qrcode.QRCode(
                version=version,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=box_size,
                border=border,
            )
            # 添加数据
            qr.add_data(data)
            # 填充数据
            qr.make(fit=True)
            # 生成图片
            im = qr.make_image(fill_color='#000', back_color='#fff')
            # 添加logo
            icon = Image.open(self.logo_file_path if not logo else logo)
            # 获取图片的宽高
            img_w, img_h = im.size
            # 设置logo的大小
            factor = 4
            size_w = int(img_w / factor)
            size_h = int(img_h / factor)
            icon_w, icon_h = icon.size
            if icon_w > size_w: icon_w = size_w
            if icon_h > size_h: icon_h = size_h
            # 重新设置logo的尺寸
            icon = icon.resize((icon_w, icon_h), Image.ANTIALIAS)
            # 得到画图的x，y坐标，居中显示
            logo_x = int((img_w - icon_w) / 2)
            logo_y = int((img_h - icon_h) / 2)
            # 粘贴logo
            im.paste(icon, (logo_x, logo_y), mask=None)
            self.logger.info('【%s】二维码已生成，数据长度：%s', usage, len(data))
            return im
        except Exception as e:
            self.logger.error('【%s】二维码生成失败：%s', usage, e)
            return None

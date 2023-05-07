from logging import getLogger, Logger
from PIL import Image, ImageChops, ImageColor

class ImageHandler:
    words: list = []
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger(self.__class__.__name__)

    def convert_to_png(self, src_path, dest_path):
        """
        转换指定图片为 PNG 格式
        """
        im = Image.open(src_path).convert("RGB")
        im.save(dest_path, "png")
        self.logger.info('图片已转换为 PNG 格式：%s', dest_path)
        return True

    def crop_image(self, filepath):
        """
        读取给定图片文件，对空白边缘进行裁剪并按原文件名保存
        """
        try:
            # 裁剪空白
            img = Image.open(filepath)
            if img.mode == 'P': img = img.convert('RGB')
            bg = Image.new(img.mode, img.size, ImageColor.getrgb('white'))
            diff = ImageChops.difference(img, bg)
            diff = ImageChops.add(diff, diff, 2.0, -100)
            bbox = diff.getbbox()
            if bbox:
                edge_width = 5
                new_size = (bbox[2] - bbox[0] + 1 + edge_width * 2, bbox[3] - bbox[1] + 1 + edge_width * 2)
                corner = (edge_width, edge_width)
                img_new = Image.new(img.mode, new_size, ImageColor.getrgb('white'))
                img_crop = img.crop(bbox)
                img_new.paste(img_crop, corner)
            else:
                img_new = img
            img_new.save(filepath)
            return True, filepath
        except Exception as e:
            self.logger.error('裁剪图像失败：%s', str(e))
            return False, None
from configure import Config
from definition.cls import Singleton
from logging import getLogger, Logger
from random import random

cfg = Config()
class ArticleManager(metaclass=Singleton):
    article_media_ids: dict
    article_urls: dict
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = getLogger('ARTICLEMGR')
        self.load()
        
    def load(self):
        """
        加载推文信息字典
        """
        try:
            self.article_urls = cfg.data.articles.get('url', {})
            self.article_media_ids = cfg.data.articles.get('media_id', {})
            cfg.data.articles = {
                'url': self.article_urls,
                'media_id': self.article_media_ids,
            }
            self.logger.info('推文信息加载成功，URL 数量：%d，media id 数量：%d', len(self.article_urls), len(self.article_media_ids))
            return True
        except Exception as e:
            self.logger.error('推文信息加载失败：%s', str(e))
            return False

    def add_media_id(self, type: str, media_id: str):
        """
        添加指定类型的推文 media id
        """
        media_ids = self.article_media_ids.get(type, [])
        if media_id in media_ids: return True
        media_ids.append(media_id)
        self.article_media_ids[type] = media_ids
        cfg.save()
        return True

    def remove_media_id(self, type: str, media_id: str):
        """
        删除指定类型的推文 media id
        """
        media_ids = self.article_media_ids.get(type, [])
        if media_id in media_ids: return True
        media_ids.remove(media_id)
        self.article_media_ids[type] = media_ids
        cfg.save()
        return True

    def get_media_id(self, type: str):
        """
        返回指定类型的推文 media id
        """
        return self.article_media_ids.get(type)

    def add_url(self, type: str, url: str):
        """
        添加指定类型的推文 URL
        """
        urls = self.article_urls.get(type, [])
        if url in urls: return False
        urls.append(url)
        self.article_urls[type] = urls
        cfg.save()
        return True

    def remove_url(self, type: str, url: str):
        """
        删除指定类型的推文 URL
        """
        urls = self.article_urls.get(type, [])
        if not url in urls: return False
        urls.remove(url)
        self.article_urls[type] = urls
        cfg.save()
        return True

    def shuffle_get_url(self, type: str):
        """
        随机抽取一篇指定类型的推文 URL 并返回
        """
        urls = self.article_urls.get(type, [])
        index = int(random() * len(urls))
        return urls[index]
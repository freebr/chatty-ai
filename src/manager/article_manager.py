from definition.const import DIR_CONFIG
from os import path
from random import random
from logging import Logger
import yaml

class ArticleManager:
    file_path: str = path.join(DIR_CONFIG, 'article-urls.yml')
    article_urls: list = []
    ad_urls: list = []
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.read()
        
    def read(self):
        """
        加载文章 URL 列表
        """
        try:
            if not path.isfile(self.file_path):
                self.logger.error('文章 URL 列表加载失败，找不到文件：%s', self.file_path)
                return False
            result:dict
            with open(self.file_path, 'r') as f:
                result = yaml.load(f, Loader=yaml.FullLoader)
            if not result: raise Exception('文章 URL 列表加载失败')
            self.article_urls = result
            self.ad_urls = self.article_urls.get('ads')
            if not self.ad_urls: self.article_urls['ads'] = self.ad_urls = []
            self.logger.info('文章 URL 列表加载成功，广告文章数量：%d', len(self.ad_urls))
            return True
        except Exception as e:
            self.logger.error('文章 URL 列表加载失败：%s', str(e))
            return False

    def save(self):
        """
        保存文章 URL 列表
        """
        with open(self.file_path, mode='w', encoding='utf-8', errors='ignore') as f:
            yaml.dump(self.article_urls, f)

    def add_ad_url(self, url=''):
        """
        添加广告文章 URL
        """
        if url in self.ad_urls: return True
        self.ad_urls.append(url)
        self.save()
        return True

    def remove_ad_url(self, url=''):
        """
        删除广告文章 URL
        """
        if url not in self.ad_urls: return False
        self.ad_urls.remove(url)
        self.save()
        return True

    def shuffle_get_ad_url(self):
        """
        随机抽取一篇广告文章 URL 并返回
        """
        index = int(random() * len(self.ad_urls))
        return self.ad_urls[index]
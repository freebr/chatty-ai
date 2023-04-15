from const import DIR_CONFIG
from os import path
from random import random
from logging import Logger
import yaml

class ArticleManager:
    file_path: str = path.join(DIR_CONFIG, 'article-urls.yml')
    article_urls: list = []
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.read()
        
    def read(self):
        try:
            if not path.isfile(self.file_path):
                self.logger.error('文章 URL 列表加载失败，找不到文件：%s', self.file_path)
                return False
            result:dict
            with open(self.file_path, 'r') as f:
                result = yaml.load(f, Loader=yaml.FullLoader)
            if not result: raise Exception('文章 URL 列表加载失败')
            ads = result['ads']
            self.article_urls = []
            for url in ads:
                self.article_urls.append(url)
            self.logger.info('文章 URL 列表加载成功，数量：%d', len(self.article_urls))
            return True
        except Exception as e:
            self.logger.error('文章 URL 列表加载失败：%s', str(e))
            return False

    def save(self):
        with open(self.file_path, mode='w', encoding='utf-8', errors='ignore')  as f:
            f.write('\n'.join(self.article_urls))

    def add_article_url(self, url=''):
        if url in self.article_urls: return True
        self.article_urls.append(url)
        self.save()
        return True

    def remove_article_url(self, url=''):
        if url not in self.article_urls: return False
        self.article_urls.remove(url)
        self.save()
        return True

    def shuffle_get_url(self):
        """
        随机抽取一篇文章 URL 并返回
        """
        index = int(random() * len(self.article_urls))
        return self.article_urls[index]
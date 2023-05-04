"""
搜索引擎工具
"""
from bs4 import BeautifulSoup
from logging import getLogger, Logger
import requests.api as requests
import web

class SearchEngine:
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger(self.__class__.__name__)
        
    def get_all_answers(self, question):
        """
        通过爬取搜索引擎结果，获取对问题的答案列表
        """
        question = question.strip()
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.39',
        }
        url = f'https://cn.bing.com/?q={web.urlquote(question)}'
        res = requests.get(url, headers=headers).text
        soup = BeautifulSoup(res, 'lxml')
        results = soup.select('main .b_ans.b_top')
        if len(results) != 0:
            # 将置顶搜索结果内容作为答案
            answer = '[' + self.format_url(soup.select('main .b_ans.b_top h2 a')[0].attrs.get('href')) + ']' + results[0].text
            return [answer]
        results = soup.select('main .b_algo p')
        if len(results) == 0: return []
        # 将第一页搜索结果内容作为答案
        answers = [
            # 信息来源
            '[' + self.format_url(soup.select('main .b_algo h2 a')[i].attrs.get('href')) + ']'
            # 信息内容
            + soup.select('main .b_algo p')[i].text[0:50]
            for i in range(len(results))
        ]
        return answers

    def format_url(self, url: str):
        """
        格式化 URL
        """
        if not url.startswith('https://') and not url.startswith('http://'): url = 'http://' + url
        return url
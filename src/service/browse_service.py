import requests.api as requests
import requests.exceptions
from bs4 import BeautifulSoup
from logging import getLogger, Logger
from urllib.parse import urlparse, urljoin

from configure import Config
from definition.cls import Singleton

cfg = Config()
class BrowseService(metaclass=Singleton):
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger("BROWSESERVICE")
        self.semantic_parse = kwargs['semantic_parse']

    def __real_query(self, url: str, question: str, get_links: bool):
        """
        浏览指定网页并针对执行问题生成摘要和 URL 列表
        url: 网页 URL
        question: 问题
        get_links: 是否提取链接
        """
        try:
            summary = self.get_text_summary(url, question)
            if get_links:
                links = self.get_hyperlinks(url)
                # Limit links to 5
                if type(links) == list and len(links) > 5:
                    links = links[:5]
                result = f'网页内容摘要:{summary}\n\n链接:{links}'
            else:
                result = f'网页内容摘要:{summary}'
            return result
        except Exception as e:
            self.logger.error('浏览网页信息失败：%s', str(e))
            return

    def invoke(self, args):
        """
        调用服务并返回信息
        """
        result = self.__real_query(args['url'], args['question'], args['get_links'])
        return result

    def get_hyperlinks(self, url):
        """Return the results of a google search"""
        link_list = self.scrape_links(url)
        return link_list
        
    def get_text_summary(self, url, question):
        """Return the results of a google search"""
        text = self.scrape_text(url)
        summary = self.summarize_text(text, question)
        return """ Result : """ + summary

    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    # Function to sanitize the URL
    def sanitize_url(self, url):
        return urljoin(url, urlparse(url).path)

    # Define and check for local file address prefixes
    def check_local_file_access(self, url):
        local_prefixes = ['file:///', 'file://localhost', 'http://localhost', 'https://localhost']
        return any(url.startswith(prefix) for prefix in local_prefixes)

    def get_response(self, url, headers={'Content-Type': 'text/html; charset=utf-8', 'UserAgent': cfg.data.features['UserAgent']}, timeout=10):
        try:
            # Restrict access to local files
            if self.check_local_file_access(url):
                raise ValueError('Access to local files is restricted')

            # Most basic check if the URL is valid:
            if not url.startswith('http://') and not url.startswith('https://'):
                raise ValueError('Invalid URL format')

            sanitized_url = self.sanitize_url(url)

            response = requests.get(sanitized_url, headers=headers, timeout=timeout)

            # Check if the response contains an HTTP error
            if response.status_code >= 400:
                return None, "Error: HTTP " + str(response.status_code) + " error"

            return response, None
        except ValueError as ve:
            # Handle invalid URL format
            return None, "Error: " + str(ve)

        except requests.exceptions.RequestException as re:
            # Handle exceptions related to the HTTP request (e.g., connection errors, timeouts, etc.)
            return None, "Error: " + str(re)

    def scrape_text(self, url):
        """Scrape text from a webpage"""
        response, error_message = self.get_response(url)
        if error_message:
            return error_message

        soup = BeautifulSoup(response.text.encode('iso-8859-1').decode('utf-8'), 'lxml')

        for script in soup(['script', 'style']):
            script.extract()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    def extract_hyperlinks(self, soup):
        """Extract hyperlinks from a BeautifulSoup object"""
        hyperlinks = []
        for link in soup.find_all('a', href=True):
            hyperlinks.append((link.text, link['href']))
        return hyperlinks

    def format_hyperlinks(self, hyperlinks):
        """Format hyperlinks into a list of strings"""
        formatted_links = []
        for link_text, link_url in hyperlinks:
            formatted_links.append(f"{link_text} ({link_url})")
        return formatted_links

    def scrape_links(self, url):
        """Scrape links from a webpage"""
        response, error_message = self.get_response(url)
        if error_message:
            return error_message

        soup = BeautifulSoup(response.text, 'lxml')

        for script in soup(['script', 'style']):
            script.extract()

        hyperlinks = self.extract_hyperlinks(soup)

        return self.format_hyperlinks(hyperlinks)

    def split_text(self, text, max_length=8192):
        """Split text into chunks of a maximum length"""
        paragraphs = text.split("\n")
        current_length = 0
        current_chunk = []

        for paragraph in paragraphs:
            if current_length + len(paragraph) + 1 <= max_length:
                current_chunk.append(paragraph)
                current_length += len(paragraph) + 1
            else:
                yield "\n".join(current_chunk)
                current_chunk = [paragraph]
                current_length = len(paragraph) + 1

        if current_chunk:
            yield "\n".join(current_chunk)

    def create_prompt(self, chunk, question):
        """Create a message for the user to summarize a chunk of text"""
        return f"\"\"\"{chunk}\"\"\" Using the above text, please answer the following question: \"{question}\" -- if the question cannot be answered using the text, please summarize the text."

    def summarize_text(self, text, question):
        """Summarize text using the LLM model"""
        if not text:
            return "Error: No text to summarize"

        text_length = len(text)
        self.logger.info('文本长度：%d', text_length)

        summaries = []
        chunks = list(self.split_text(text))

        # 对每段文本块进行总结
        for i, chunk in enumerate(chunks):
            self.logger.info('正在总结第 %d/%d 个文本块', i + 1, len(chunks))
            prompt = self.create_prompt(chunk, question)
            summary = self.semantic_parse(content=prompt)
            summaries.append(summary)

        self.logger.info(f'已完成 %d 个文本块的总结', len(chunks))

        # 对分段摘要汇总后再次总结摘要
        combined_summary = "\n".join(summaries)
        prompt = self.create_prompt(combined_summary, question)

        final_summary = self.semantic_parse(content=prompt)

        return final_summary
from definition.const import DIR_DATA
from logging import getLogger, Logger
from os import listdir, path

class MessageHandler:
    file_dir: str = path.join(DIR_DATA, 'sensitive-words')
    words: list = []
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.read_sensitive_words()
        
    def read_sensitive_words(self):
        if not path.isdir(self.file_dir):
            self.logger.error('敏感词词典加载失败，找不到路径：%s', self.file_dir)
            return False
        files = listdir(self.file_dir)
        self.words.clear()
        for i in range(len(files)):
            file_path = path.join(self.file_dir, files[i])
            if not (path.isfile(file_path) and file_path.endswith('.txt')): continue
            with open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
                line = f.readline()
                while line:
                    self.words.append(line.strip())
                    line = f.readline()
        self.logger.info('敏感词词典加载成功，数量：%d', len(self.words))
        return True

    def extract_message(self, text='', offset=0, min_len=10, stop_chars='\n', code_mode=False):
        """
        从文本中提取第一个片段（句子、段落）
        如遇到代码则不切分
        """
        if len(text) == 0: return ('', offset, code_mode)
        index = text.find('```')
        if index != -1:
            if code_mode:
                index_r = text.rfind('\n```')
                if index_r != -1:
                    index_r += 4
                    return (text[index:index_r], index_r + offset, False)
                else:
                    return ('', offset, True)
            else:
                if index == 0: return ('', offset, True)
                ret = self.extract_message(text[:index], offset, min_len, stop_chars, False)
                if not ret[0]: ret = (text[:index].strip(), index + offset, True)
                return ret
        index = -1
        while index + 1 < min_len:
            new_index = text.find(stop_chars[0], index + 1)
            for char in stop_chars:
                if new_index == -1:
                    new_index = text.find(char, index + 1)
                else:
                    break
            if new_index == -1: return ('', offset, code_mode)
            index = new_index
        if text[index] in '\r\n':
            # 不输出换行符，跳过
            return (text[:index], index + offset + 1, code_mode)
        return (text[:index + 1], index + offset + 1, code_mode)

    def filter_sensitive(self, text=''):
        """
        过滤敏感词
        """
        for word in self.words:
            text = text.replace(word, '*' * len(word))
        return text
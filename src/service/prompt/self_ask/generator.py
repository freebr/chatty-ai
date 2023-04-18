"""
self-ask 框架提示增强模块
"""
from ..utils.search_engine import SearchEngineAgent
from logging import Logger, getLogger
from time import strftime
import datetime
import openai
import re
import traceback

RE_FINAL_ANSWER = re.compile(r'"The final answer": "(.*)"', re.I)
RE_SEARCH_QUESTION = re.compile(r'"Search": "(.*)"', re.I)
SELF_ASK_PROMPT_LEVEL0 = f"""\
1.Do not answer the question you do not need to search, just output in JSON {{"Search": "no"}}.\
2.For daily news, time-related events and statistical data, you should always search to find out answer, just output in JSON {{"Search": "<keyword about what you want to search>"}}.\
3.Do not search for the same keyword each time.\
"""
SELF_ASK_PROMPT_LEVELN = f"""\
1.If you finally find out answer, output in JSON {{"The final answer": "<url>: <final answer>"}}.\
2.If you are not sure about answer yet, you can search more to find answer, just output in JSON {{"Search": "<keyword about what you want to search>"}}. Do not give any other comments.\
3.Do not search for the same keyword each time.\
"""

MAX_LEVEL_SEARCH = 1
class SelfAskPromptGenerator:
    api_key: str
    search_agent: SearchEngineAgent
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.api_key = kwargs['api_key']
        self.search_agent = SearchEngineAgent(logger=getLogger('SEARCHENGINEAGENT'))

    def invoke(self, input:list, level=0):
        """
        self-ask 单层推理流程
        """
        try:
            # 作出判断推理
            now_time = (datetime.datetime.now() + datetime.timedelta(hours=8)).timetuple()
            messages = []
            messages += input
            if level == 0:
                messages[-1] = {'role': 'user', 'content': f"现在是{strftime('%Y年%m月%d日 %H:%M:%S', now_time)},请问:{messages[-1]['content']}"}
                append_message = [{'role': 'system', 'content': SELF_ASK_PROMPT_LEVEL0}]
            else:
                append_message = [{'role': 'system', 'content': SELF_ASK_PROMPT_LEVELN}]
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=messages + append_message,
                request_timeout=20,
                api_key=self.api_key,
                max_tokens=1000,
                temperature=0,
            )
            text = response['choices'][0]['message']['content'].strip()
            answer, search = self.decide(text)
            # 判断是否需要使用工具
            if search == 'no':
                # 无需搜索
                self.logger.info('无需在线搜索增强提示')
                return
            if search:
                if level == MAX_LEVEL_SEARCH: return
                self.logger.info('在线搜索：%s', search)
                messages.append({'role': 'assistant', 'content': search})
                # 使用搜索引擎获得对 search 的回答
                search_answer = self.search_agent.get_all_answers(search)
                if len(search_answer) > 1:
                    answers = [f'Result {n+1}:' + search_answer[n] for n in range(len(search_answer))]
                    messages.append({'role': 'assistant', 'content': ''.join(answers)})
                else:
                    answer = 'Result:' + search_answer[0]
                    messages.append({'role': 'assistant', 'content': answer})
                # 将输入和回答打包传递到下层
                return self.invoke(messages, level+1)
            if answer:
                answer = '1.按以下模式回答: "根据我的搜索, <search result>, 信息来源: <url>."; 2.搜索结果:' + answer
                self.logger.info("增强系统提示：%s", answer)
                return answer
        except Exception as e:
            self.logger.error('Invoke Error: %s', str(e))
            traceback.print_exc(limit=5)
        # 没有提取到 final answer 和 search question
        return

    def decide(self, text):
        """
        根据 GPT 生成的文本，确定答案和 GPT 对是否需要使用工具回答问题的判断
        工具包括：搜索引擎
        """
        answer = ''
        search = ''
        match = re.search(RE_FINAL_ANSWER, text)
        if match:
            # 获得最终答案
            answer = match[1].strip()
            return answer, ''
        match = re.search(RE_SEARCH_QUESTION, text)
        if match:
            # 获得需搜索内容
            search = match[1].strip()
            return '', search
        self.logger.error('没有提取到 final answer 和 search question')
        return '', ''
import datetime
import web
import json
from .token_counter import count_string_tokens
from definition.const import MODEL_TEXT_COMPLETION
from typing import List, Dict

def convert_encoding(text = ''):
    """
    将指定文本从 ISO-8859-1 转换为 UTF-8 编码
    """
    return str(text).encode('iso-8859-1').decode('utf-8')

def get_query_string():
    input = web.input()
    arr = []
    for key in input:
        value = web.urlquote(input.get(key))
        if len(value) == 0:
            arr.append(key)
        else:
            arr.append(f'{key}={value}')
    return '&'.join(arr)

def success_json(**kwargs):
    ret = {
        'code': 0,
        'result': 'ok',
    }
    if kwargs != {}: ret['detail'] = kwargs
    return json.dumps(ret, ensure_ascii=False)
    
def fail_json(**kwargs):
    ret = {
        'code': 1,
        'result': 'fail',
    }
    if kwargs != {}: ret['detail'] = kwargs
    return json.dumps(ret, ensure_ascii=False)

def make_message(role, content):
    """
    返回一条消息记录
    """
    return {'role': role, 'content': content, '__token': count_string_tokens(content, MODEL_TEXT_COMPLETION)}

def format_messages(messages: List[Dict[str, str]]):
    """
    为 OpenAI 接口格式化消息记录
    """
    return [{'role': message['role'], 'content': message['content'] } for message in messages]

def now():
    return datetime.datetime.now().ctime()
import datetime
import web
import json
from .token_counter import count_message_tokens
from definition.const import MODEL_CHAT
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
    if not content: return
    return {'role': role, 'content': content, '__token': count_message_tokens([{'role': role, 'content': content}], MODEL_CHAT)}

def make_wx_msg_link(display_text, message=None):
    if not message: message = display_text
    return f"""<a href="weixin://bizmsgmenu?msgmenucontent={message}&msgmenuid=0">{display_text}</a>"""
    
def format_messages(messages: List[Dict[str, str]]):
    """
    为 OpenAI 接口格式化消息记录
    """
    return [{'role': message['role'], 'content': message['content'] } for message in messages]

def now():
    return datetime.datetime.now().ctime()

def get_feature_command_string(command: str):
    if not command: return
    return 'Commands.' + command

def get_headers():
    return {
        'Content-Type': 'application/json; charset=utf-8'
    }
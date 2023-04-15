import datetime
import web
import json

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

def now():
    return (datetime.datetime.now() + datetime.timedelta(hours=8)).ctime()
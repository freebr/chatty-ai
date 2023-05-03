import json
import re

def parse_json(text):
    errors = []
    results = []
    text = text.replace('，', ',').replace('：', ':').replace('“', '"').replace('”', '"')
    snippets = text.split('\n')
    for snippet in snippets:
        try:
            if not snippet.strip(): continue
            # 提取 JSON
            match = re.search(r'\{(.*)\}', snippet, re.S)
            if match:
                json_object = match[0]
                result = json.loads(json_object)
                if not result.get('command'):
                    result = {'command': result}
                results.append(result)
                continue
            match = re.search(r'```(.*)```', snippet, re.S)
            if match:
                json_object = '{' + match[0] + '}'
                result = json.loads(json_object)
                if not result.get('command'):
                    result = {'command': result}
                results.append(result)
                continue
            snippet = '{' + snippet + '}'
            match = re.search(r'\{(.*)\}', snippet, re.S)
            if match:
                json_object = match[0]
                result = json.loads(json_object)
                if not result.get('command'):
                    result = {'command': result}
                results.append(result)
        except Exception as e:
            # 试图修复错误
            message = str(e)
            if 'Expecting property name enclosed in double quotes' in message:
                char_pos = int(re.search(r'char\s(\d+)', message)[1])
                snippet = snippet[:char_pos] + re.sub(r'(\w+):', lambda match: f'"{match[1]}":', snippet[char_pos:])
                temp_result = parse_json(snippet)
                if type(temp_result) != list:
                    errors.append(str(temp_result))
                    continue
                results.append(temp_result[0])
            else:
                errors.append(str(e))
                continue
    if len(results) == 0: return 'failed: %s' % ','.join(errors)
    return results
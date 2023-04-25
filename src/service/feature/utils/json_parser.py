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
            snippet = re.sub(r'(\w+)(:)', lambda match: f'"{match[1]}"{match[2]}', snippet)
            # 提取 JSON
            match = re.search(r'\{(.*)\}', snippet, re.S)
            if match:
                json_object = match[0]
                response = json.loads(json_object)
                if not response.get('command'):
                    response = {'command': response}
                results.append(response)
                continue
            match = re.search(r'```(.*)```', snippet, re.S)
            if match:
                json_object = '{' + match[0] + '}'
                response = json.loads(json_object)
                results.append(response)
                continue
            snippet = '{' + snippet + '}'
            match = re.search(r'\{(.*)\}', snippet, re.S)
            if match:
                json_object = match[0]
                response = json.loads(json_object)
                results.append(response)
        except Exception as e:
            errors.append(str(e))
            continue
    if len(results) == 0: return 'failed: %s' % ','.join(errors)
    return results
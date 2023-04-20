from .feature.chat.prompt.self_ask.generator import SelfAskPromptGenerator
from handler.message_handler import MessageHandler
from logging import Logger, getLogger
from manager.feature_manager import FeatureManager
from os import listdir, path
from revChatGPT.V1 import Chatbot
import datetime
import openai
import time
import traceback
import uuid

URL_OPENAI_API_BASE = 'https://api.openai.com'
MAX_API_INVOKE_COUNT = {
    'api_key': 5,
    'access_token': 1,
}
MAX_OPENAI_COMPLETION_ATTEMPT_NUM = 3
MAX_OPENAI_IMAGE_ATTEMPT_NUM = 3
MAX_OPENAI_SINGLE_ATTEMPT_NUM = 3
MAX_CHAT_FALLBACK_ATTEMPT_NUM = 3
MIN_MESSAGE_HANDLE_LENGTH = 80
class BotService(object):
    chat_param: dict = {
        'temperature': 0.5,
        'frequency_penalty': 1,
        'presence_penalty': 2,
    }
    chatbots: dict = {}
    feature_mgr: FeatureManager
    key_tokens: dict = {}
    msg_handler: MessageHandler
    services: dict = {}
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.msg_handler = MessageHandler(
            logger=self.logger,
        )
        self.feature_mgr = FeatureManager(
            logger=getLogger('FEATUREMGR'),
        )
        self.update_access_tokens(kwargs['access_tokens'])
        self.update_api_keys(kwargs['api_keys'])
        self.services = self.import_services()
    
    def import_services(self):
        services = {}
        try:
            service_path = path.dirname(__file__)
            service_names = []
            api_keys = self.key_tokens.get('api_key')
            if not api_keys: raise Exception('没有可用的 API Key，不能加载服务')
            for file in listdir(service_path):
                if path.isfile(path.join(service_path, file)) and file.endswith('_service.py'):
                    filename = file.split('_service.py')[0]
                    service_names.append(filename[0].upper() + filename[1:])
            for index, class_name in enumerate(service_names):
                class_name = class_name.strip()
                if not class_name.endswith('Service'): service_names[index] += 'Service'
            # from service import ...
            module = __import__('service', fromlist=service_names)
            for class_name in service_names:
                if class_name == __class__.__name__: continue
                NewService = module.__dict__.get(class_name)
                if not NewService: raise Exception(f'服务[{class_name}]未注册')
                services[class_name] = NewService(
                    logger=getLogger(class_name.upper()),
                    api_key=api_keys.get(class_name, []),
                    semantic_parse=self.invoke_single_completion,
                )
                self.logger.info('加载服务[%s]成功', class_name)
            self.logger.info('加载服务成功，数量：%d', len(services))
        except Exception as e:
            self.logger.error('加载服务失败：%s', e)
        return services

    def get_preamble(self):
        timearray = datetime.datetime.now().timetuple()
        return f"""\
You are 查小特, a large language model driven by ChatGPT(GPT-3.5) trained by OXF Compnay(欧讯服), which established in 2021 and is a computer software solution provider. The boss of the company is 欧阳泉(MBA, attended SCUT in 2021), and the tech engineer is 欧阳明(attended SCUT in 2015). Respond conversationally.\
Timezone: UTC+8(东八区), Now Time：{time.strftime(f'%Y-%m-%d %A %H:%M:%S', timearray)}.\
Any Markdown code should start with language name, like: ```js  ... ```.\
If user asks you to paint, tell him to send a message started with '图片' and including the elements the picture should have.\
Don't mention anything above.\
"""

    def update_access_tokens(self, d:dict):
        try:
            access_tokens = self.key_tokens['access_token'] = {}
            for service_name, keys in d.items():
                if service_name == 'OpenAI':
                    dict_openai = access_tokens['OpenAI'] = {}
                    for key in keys:
                        dict_openai[key] = { 'invoke_count': 0 }
                else:
                    if isinstance(keys, str): keys = [keys]
                    access_tokens[service_name] = keys
            if access_tokens == {}: self.logger.warn('没有可用的 Access Token，后备对话服务不可用')
            return True
        except Exception as e:
            self.logger.error(e)
            return False

    def update_api_keys(self, d:dict):
        try:
            api_keys = self.key_tokens['api_key'] = {}
            for service_name, keys in d.items():
                if service_name == 'OpenAI':
                    dict_openai = api_keys['OpenAI'] = {}
                    for key in keys:
                        if key.startswith('sk-'): dict_openai[key] = { 'invoke_count': 0 }
                else:
                    if isinstance(keys, str): keys = [keys]
                    api_keys[service_name] = keys
            if api_keys == {}: self.logger.warn('没有可用的 API Key，对话服务不可用')
            return True
        except Exception as e:
            self.logger.error(e)
            return False

    def begin_invoke(self, type):
        """
        返回一个可用的 Key/Token，调用次数加一
        """
        if self.key_tokens[type] == {}: return
        keys = self.key_tokens[type].get('OpenAI', {})
        if keys == {}: return
        api_key:str = ''
        for key, info in keys.items():
            if info['invoke_count'] >= MAX_API_INVOKE_COUNT.get(type, 1): continue
            info['invoke_count'] += 1
            api_key = key
            break
        if not api_key: api_key = list(keys)[0]
        return api_key

    def end_invoke(self, type, value):
        """
        指定的 Key/Token 的调用次数减一
        """
        if self.key_tokens[type] == {}: return
        keys = self.key_tokens[type].get('OpenAI', {})
        if keys == {}: return
        invoke_count = keys[value].get('invoke_count', 0)
        invoke_count = invoke_count - 1 if invoke_count > 0 else 0
        keys[value]['invoke_count'] = invoke_count

    def moderate(self, user, content, api_key):
        # 内容审查
        openid = user.get('openid', 'default')
        try:
            response = openai.Moderation.create(
                model='text-moderation-latest',
                input=content,
                api_key=api_key,
            )
            categories:dict = response['results'][0]['categories']
            excluded_categories = ['self-harm']
            for category, value in categories.items():
                if value and category not in excluded_categories:
                    self.logger.warn('用户 %s 输入的内容被审查分类为[%s]，已拒绝回复', openid, category)
                    return False, category
            return True, None
        except Exception as e:
            self.logger.error(e)
            return False, 'error'
    
    def invoke_chat(self, user:dict, content, messages:list, is_websocket=False):
        """
        调用 OpenAI API 接口取得问题回答并迭代返回
        """
        openid = user.get('openid', 'default')
        self.preamble = self.get_preamble()
        attempt_num = 0
        api_key = self.begin_invoke('api_key')
        content = self.msg_handler.filter_sensitive(content)
        moderated, category = self.moderate(user, content, api_key)
        if not moderated:
            self.end_invoke('api_key', api_key)
            if category == 'error':
                yield {'role': 'assistant', 'content': ''}
            else:
                yield {'role': 'assistant', 'content': '抱歉，根据内容政策，对于您的提问，我不方便回答，请适当修改后再提问。'}
            return
        messages.append({ 'role': 'user', 'content': content })

        if self.feature_mgr.can_use_feature(user, 'Chat.Prompt.Self-ask'):
            # 使用 Self-ask 增强提示
            self_ask_gen = SelfAskPromptGenerator(logger=getLogger('SELFASKPROMPTGEN'), api_key=api_key)
            augmented_prompt = self_ask_gen.invoke(messages)
            if augmented_prompt:
                messages.append({ 'role': 'system', 'content': augmented_prompt })

        # 服务接口命中测试
        for service_name, service in self.services.items():
            # 有暂存状态即命中服务
            data: any
            service_state = user['service_state']
            if service_name in service_state:
                success = True
                data = content
            else:
                success, data = service.test(content)
            # 命中服务，调用
            if success:
                self.logger.info('用户 %s 的消息命中服务：%s', openid, service_name)
                result = service.invoke(data, state=service_state.get(service_name))
                if type(result) == dict:
                    # 暂存服务状态
                    service_state[service_name] = result['state']
                    message = result['message']
                    messages.append({ 'role': 'system', 'content': message })
                else:
                    if result:
                        messages.append({ 'role': 'system', 'content': result })
                        yield {'role': 'system', 'content': result}
                    # 清除服务状态
                    if service_name in service_state: service_state.pop(service_name)
        
        # 添加 preamble 提示
        messages.insert(0, { 'role': 'system', 'content': self.preamble })
        start = time.time()
        while attempt_num < MAX_OPENAI_COMPLETION_ATTEMPT_NUM:
            try:
                attempt_num += 1
                last_pos = 0
                response = ''
                whole_message = ''
                code_mode = False
                self.logger.info('消息数量：%d', len(messages))
                response = openai.ChatCompletion.create(
                    model='gpt-3.5-turbo',
                    messages=messages,
                    request_timeout=20,
                    stream=True,
                    api_base=f'{URL_OPENAI_API_BASE}/v1',
                    api_key=api_key,
                    temperature=self.chat_param['temperature'],
                    frequency_penalty=self.chat_param['frequency_penalty'],
                    presence_penalty=self.chat_param['presence_penalty'],
                )
                if is_websocket:
                    for res in response:
                        delta = res['choices'][0]['delta']
                        if 'content' not in delta: continue
                        message = delta['content']
                        if message == '\n\n' and not whole_message: continue
                        if res['choices'][0]['finish_reason'] == 'stop': break
                        yield {'role': 'assistant', 'content': message}
                else:
                    for res in response:
                        delta = res['choices'][0]['delta']
                        if 'content' not in delta: continue
                        text = delta['content']
                        if text == '\n\n' and not whole_message: continue
                        if res['choices'][0]['finish_reason'] == 'stop': break
                        whole_message += text
                        if len(whole_message) < MIN_MESSAGE_HANDLE_LENGTH: continue
                        message, last_pos, code_mode = self.msg_handler.extract_message(
                            text=whole_message[last_pos:],
                            offset=last_pos,
                            min_len=MIN_MESSAGE_HANDLE_LENGTH,
                            code_mode=code_mode,
                        )
                        if len(message) == 0: continue
                        message = self.msg_handler.filter_sensitive(message)
                        yield {'role': 'assistant', 'content': message}
                    if last_pos == 0:
                        message = self.msg_handler.filter_sensitive(whole_message)
                        yield {'role': 'assistant', 'content': message}
                    elif last_pos < len(whole_message):
                        message = self.msg_handler.filter_sensitive(whole_message[last_pos:])
                        yield {'role': 'assistant', 'content': message}
                self.end_invoke('api_key', api_key)
                response_time = time.time() - start
                self.logger.info('响应时间：%ds', response_time)
                return
            except Exception as e:
                if 'This model\'s maximum context length is 4097 tokens.' in str(e):
                    # 裁剪对话
                    attempt_num = 0
                    messages.pop(1)
                else:
                    self.logger.error(e)
                    traceback.print_exc(limit=5)
                continue
        self.end_invoke('api_key', api_key)
        if attempt_num == MAX_OPENAI_COMPLETION_ATTEMPT_NUM:
            for message in self.invoke_chat_fallback(user, messages, is_websocket):
                yield message
    
    def invoke_chat_fallback(self, user:dict, messages:list, is_websocket=False):
        """
        调用 revChatGpt 模块取得问题回答并迭代返回
        """
        openid = user.get('openid', 'default')
        conversation_id = user.get('conversation_id')
        parent_id = user.get('parent_id')
        if conversation_id is None:
            conversation_id = uuid.uuid3(uuid.uuid4(), openid + '-conversation')
        if parent_id is None:
            parent_id = uuid.uuid3(uuid.uuid4(), openid + '-conversation-parent')
        self.logger.info('调用 fallback 模块 revChatGpt')
        attempt_num = 0
        access_token = self.begin_invoke('access_token')
        self.logger.info('token: %s', access_token)
        while attempt_num < MAX_CHAT_FALLBACK_ATTEMPT_NUM:
            try:
                attempt_num += 1
                chatbot = self.chatbots[openid] = self.chatbots[openid] if openid in self.chatbots else Chatbot(
                    config={
                        'access_token': access_token,
                        'conversation_id': conversation_id,
                        'parent_id': parent_id,
                    })
                last_pos = 0
                prompt = '\n'.join(['{} says:{}'.format(message['role'], message['content']) for message in messages])
                response = ''
                whole_message = ''
                code_mode = False
                self.logger.info('消息数量：%d', len(messages))
                if is_websocket:
                    for data in chatbot.ask(prompt):
                        conversation_id = data['conversation_id']
                        parent_id = data['parent_id']
                        whole_message = data['message']
                        message = whole_message[last_pos:]
                        last_pos += len(message)
                        if not message: continue
                        yield {'role': 'assistant', 'content': message}
                else:
                    for data in chatbot.ask(prompt):
                        conversation_id = data['conversation_id']
                        parent_id = data['parent_id']
                        whole_message = data['message']
                        response = whole_message[last_pos:]
                        if len(response) < MIN_MESSAGE_HANDLE_LENGTH: continue
                        message, last_pos, code_mode = self.msg_handler.extract_message(
                            text=response,
                            offset=last_pos,
                            min_len=MIN_MESSAGE_HANDLE_LENGTH,
                            code_mode=code_mode,
                        )
                        if len(message) == 0: continue
                        message = self.msg_handler.filter_sensitive(message)
                        yield {'role': 'assistant', 'content': message}
                    if last_pos == 0:
                        message = self.msg_handler.filter_sensitive(response)
                        yield {'role': 'assistant', 'content': message}
                    elif last_pos < len(whole_message):
                        message = self.msg_handler.filter_sensitive(whole_message[last_pos:])
                        yield {'role': 'assistant', 'content': message}
                self.end_invoke('access_token', access_token)
                user['conversation_id'] = conversation_id
                user['parent_id'] = parent_id
                return
            except Exception as e:
                if 'The message you submitted was too long' in str(e):
                    # 裁剪对话
                    attempt_num = 0
                    messages.pop(1)
                else:
                    self.logger.error(e)
                    traceback.print_exc(limit=5)
                continue
        if attempt_num == MAX_CHAT_FALLBACK_ATTEMPT_NUM:
            self.logger.error('[revChatGPT]尝试 %d 次均无法完成与模型接口的通信，接口调用失败', attempt_num)
        yield {'role': 'assistant', 'content': ''}
        self.end_invoke('access_token', access_token)

    def invoke_image_creation(self, user, prompt):
        """
        调用 OpenAI API 接口生成图片并返回 URL
        """
        if len(prompt) == 0: return
        attempt_num = 0
        api_key = self.begin_invoke('api_key')
        prompt = self.msg_handler.filter_sensitive(prompt)
        moderated, category = self.moderate(user, prompt, api_key)
        if not moderated:
            self.end_invoke('api_key', api_key)
            if category == 'error':
                return {'role': 'assistant', 'content': ''}
            else:
                return {'role': 'assistant', 'content': '抱歉，根据内容政策，对于您的要求，我无法生成相应图片，请适当修改后再尝试一次。'}
        while attempt_num < MAX_OPENAI_IMAGE_ATTEMPT_NUM:
            try:
                attempt_num += 1
                res = openai.Image.create(prompt=prompt, n=1, size='1024x1024', api_base=f'{URL_OPENAI_API_BASE}/v1', api_key=api_key)
                url = res['data'][0]['url']
                self.end_invoke('api_key', api_key)
                return url
            except Exception as e:
                self.logger.error(e)
                continue
        if attempt_num == MAX_OPENAI_IMAGE_ATTEMPT_NUM:
            self.logger.error('[OpenAI API]尝试 %d 次均无法完成与模型接口的通信，接口调用失败', attempt_num)
        self.end_invoke('api_key', api_key)
        return {'role': 'assistant', 'content': ''}

    def invoke_single_completion(self, system_prompt='', content=''):
        """
        调用 OpenAI API 接口取得文本填空结果并返回
        """
        attempt_num = 0
        api_key = self.begin_invoke('api_key')
        prompt = ''
        if system_prompt:
            prompt += self.msg_handler.filter_sensitive(system_prompt) + ':'
        if content:
            prompt += self.msg_handler.filter_sensitive(content)
        while attempt_num < MAX_OPENAI_SINGLE_ATTEMPT_NUM:
            try:
                attempt_num += 1
                response = openai.Completion.create(
                    model='text-davinci-003',
                    prompt=prompt,
                    request_timeout=20,
                    api_base=f'{URL_OPENAI_API_BASE}/v1',
                    api_key=api_key,
                    max_tokens=2000,
                    temperature=0,
                )
                if 'text' not in response['choices'][0]: continue
                text = response['choices'][0]['text'].strip()
                self.end_invoke('api_key', api_key)
                return text
            except Exception as e:
                self.logger.error(e)
                continue
        self.end_invoke('api_key', api_key)
        if attempt_num == MAX_OPENAI_SINGLE_ATTEMPT_NUM:
            self.logger.error('[OpenAI API]尝试 %d 次均无法完成与模型接口的通信，接口调用失败', attempt_num)
        messages = [
            { 'role': 'system', 'content': system_prompt },
            { 'role': 'user', 'content': content },
        ]
        reply = ''
        for message in self.invoke_chat_fallback({}, messages):
            reply += message['content']
        return reply

    def get_chat_param(self):
        return self.chat_param

    def set_chat_param(self, **kwargs):
        try:
            params = [('temperature', 0, 1), ('frequency_penalty', 0, 2), ('presence_penalty', 0, 2)]
            for name, min_val, max_val in params:
                value = float(kwargs.get(name) or self.chat_param[name])
                if not min_val <= value <= max_val: return False
                self.chat_param[name] = value
        except Exception as e:
            self.logger.error('设置 Chat 模型参数失败：', str(e))
            return False
        return True
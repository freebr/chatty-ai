import _thread
import json
import re
import socket
import web
import websockets
from asyncio import get_event_loop, new_event_loop, set_event_loop
from logging import getLogger, Logger, getLogger
from os import path
from ssl import SSLContext, PROTOCOL_TLS_SERVER
from time import time
from websockets_routes import Router

from definition.const import \
    CREDIT_TYPENAME_DICT,\
    DIR_IMAGES_UPLOAD, URL_IMG2IMG_EXPORT,\
    MAX_UPLOAD_IMAGES, RESPONSE_EXCEED_TOKEN_LIMIT, SYSTEM_PROMPT_IMG2IMG,\
    TTS_ENGINE
from definition.var import getWebsocketInstanceCount
from helper.formatter import fail_json, make_message, success_json
from manager import img2img_mgr, user_mgr, voices_mgr
from service.base import bot

TIME_WAIT = 5
MIN_PACKET_LENGTH = 1
voices_info, recommended_voices = voices_mgr.get_voices_info(engine=TTS_ENGINE)
router = Router()
class WebsocketController:
    servers: list
    addr: str
    start_port: int
    ports: list[int]
    secure: bool
    ssl_enabled: bool
    ssl_context: SSLContext
    workdir: str
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger('WEBSOCKETCTLR')
        self.addr = kwargs.get('addr') or 'localhost'
        self.ports = []
        self.servers = []
        self.start_port = kwargs.get('start_port') or 8000
        self.secure = kwargs.get('secure') or False
        self.workdir = kwargs.get('workdir')
        if self.workdir:
            self.workdir = path.abspath(self.workdir)
            self.ssl_context = SSLContext(PROTOCOL_TLS_SERVER)
            file_cert = path.join(self.workdir, 'fullchain.pem')
            file_key = path.join(self.workdir, 'privkey.pem')
            self.ssl_enabled = True
            if not path.isfile(file_cert):
                self.logger.error('找不到证书文件"%s"，将无法启用WSS服务器！', file_cert)
                self.ssl_enabled = False
            if not path.isfile(file_key):
                self.logger.error('找不到私钥文件"%s"，将无法启用WSS服务器！', file_key)
                self.ssl_enabled = False
            if self.ssl_enabled: self.ssl_context.load_cert_chain(file_cert, file_key)
    
    async def send(self, ws, msg):
        await ws.send(msg)

    async def send_as_role(self, ws, result, role, **kwargs):
        if result == 'success':
            await self.send(ws, success_json(message={'role': role, **kwargs}))
        else:
            await self.send(ws, fail_json(message={'role': role, **kwargs}))
    
    def make_route(self, logger: Logger):
        @router.route('/chatty-ai/invoke')
        async def route_handler(ws, req_path):
            async for message in ws:
                try:
                    data: dict = json.loads(message)
                    opr = data.get('opr')
                    openid = data.get('openid')
                    if not openid:
                        await self.send(ws, fail_json(message='未提供用户名，禁止操作'))
                    logger.info('请求路径：%s', req_path)
                    match opr:
                        # 登录
                        case 'login':
                            user = user_mgr.register_user(openid)
                            user_mgr.set_ws(openid, ws)
                            await self.send(ws, success_json(login_time=user['login_time']))
                        # 文本生成/文生图提示/图生图提示
                        case 'msg.text':
                            content = data['content'].strip()
                            if content == '结束':
                                self.logger.info('用户 %s 进入文字对话模式', openid)
                                reply = '【系统提示】'
                                voice_name = user_mgr.get_voice_name(openid=openid)
                                if voice_name or user_mgr.get_img2img_mode(openid):
                                    reply += '现在是文字对话模式'
                                    if voice_name:
                                        user_mgr.set_voice_name(openid=openid, role=None)
                                    user_mgr.set_img2img_mode(openid, False)
                                    user_mgr.set_pending(openid, False)
                                    img2img_mgr.unregister_user(openid)
                                else:
                                    reply += '记忆已清除'
                                    user_mgr.clear_conversation(openid)
                                await self.send_as_role(ws, result='success', role='system', content=reply)
                                continue
                            if user_mgr.get_img2img_mode(openid):
                                # 按图生图风格处理
                                if content == '图生图提示举例':
                                    reply = img2img_mgr.get_prompt_examples()
                                    await self.send_as_role(ws, result='success', role='system', content='\n'.join(reply))
                                    continue
                                try:
                                    # 通过语义理解获取用户需要的风格和给出的提示
                                    system_prompt=SYSTEM_PROMPT_IMG2IMG
                                    result = bot.invoke_single_completion(system_prompt=system_prompt, content=content)
                                    self.logger.info(result)
                                    # 提取 JSON
                                    match = re.search(r'\{(.*)\}', result, re.S)
                                    # 未提取到 JSON 结构，放弃提取
                                    if not match: continue
                                    info = json.loads(match[0])
                                    # style = img2img_mgr.find_style(content)
                                    # if not style:
                                    #     reply = ['【系统提示】非常抱歉，暂不支持该风格，请重新选择！']
                                    #     reply += img2img_mgr.get_style_list(type='web')
                                    #     reply += ['想要获得提示灵感，<a href=\'#\' data-message=\'图生图提示举例\'>点击这里</a>']
                                    #     reply += ['要返回对话模式，发送<a href=\'#\' data-message=\'结束\'>结束</a>即可']
                                    #     await self.send_as_role(ws, result='success', role='system', content='\n'.join(reply))
                                    #     continue
                                    self.logger.info('用户 %s 输入提示：%s', openid, content)
                                    style = info.get('style', 'MJ风格')
                                    info['prompt'] = info.get('prompt', '').replace(style, '')
                                    info['negative_prompts'] = info.get('negative_prompts', '').replace(style, '')
                                    img2img_mgr.add_user_image_info(openid, style=style, prompt=info['prompt'], negative_prompts=info['negative_prompts'])
                                    await self.process_img2img(ws, openid, prompt=content)
                                except Exception as e:
                                    self.logger.error('处理用户 %s 的图生图指令失败：%s', openid, str(e))
                                    reply = 'error-raised'
                                    await self.send_as_role(ws, result='fail', role='system', content=reply)
                                continue
                            # 处理文本/语音消息
                            self.logger.info('用户 %s 发送消息，长度：%d', openid, len(content))
                            credit_typename = 'completion'
                            match credit_typename:
                                case 'completion':
                                    await self.process_chat(ws, openid, content)
                        # 进入图生图模式
                        case 'msg.image':
                            filename = data['filename']
                            self.logger.info('用户 %s 发送图片消息', openid)
                            await self.process_img2img_request(ws, openid, filename=filename)
                        case _:
                            await self.send(ws, fail_json(message='无效操作'))
                except Exception as e:
                    logger.error(e)
                    return e
        return route_handler
    
    def get_idle_port_after(self, start_port):
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex((self.addr, start_port)) != 0:
                    return start_port
            start_port += 1

    def run(self, server_no, port):
        logger = getLogger(f'WEBSOCKETSERVER[#{server_no}]')
        set_event_loop(new_event_loop())
        coro_serve = websockets.serve(
            lambda ws, path: self.make_route(logger)(ws, path),
            host=self.addr,
            port=port,
            logger=logger,
            ssl=self.ssl_context if self.ssl_enabled else None,
        )
        while True:
            try:
                logger.info('Websocket 服务器[#%d] 已启动，监听 %s://%s:%d', server_no, 'wss' if self.ssl_enabled else 'ws', self.addr, port)
                server = get_event_loop().run_until_complete(coro_serve)
                self.servers.append(server)
                get_event_loop().run_forever()
                logger.warn("Websocket 服务器[#%d] 意外终止，正在重启...", server_no)
            except Exception as e:
                logger.error('启动服务器[#%d]失败：%s', server_no, str(e))
                logger.error('等待 %d 秒重试...', TIME_WAIT)
                start_time = time()
                while(time() - start_time < TIME_WAIT): pass
    
    def emit(self):
        try:
            self.ports.clear()
            port = self.start_port
            for i in range(getWebsocketInstanceCount()):
                port = self.get_idle_port_after(port)
                self.ports.append(port)
                _thread.start_new_thread(self.run, (i + 1, port))
                port += 1
        except Exception as e:
            self.logger.error('创建服务器线程[#%d]失败：%s', i + 1, str(e))
    
    async def process_chat(self, ws, openid, prompt):
        """
        处理文本消息
        """
        # 判断是否有剩余可用次数
        if not await self.check_remaining_credit(ws, openid, 'completion'): return
        # 判断是否在等待回答
        if user_mgr.get_pending(openid):
            reply = 'wait-finish'
            await self.send_as_role(ws, result='fail', role='system', content=reply)
            return
        user_message = make_message('user', prompt)
        token_prompt = user_message['__token']
        self.logger.info('用户 %s 消息 token=%d', openid, token_prompt)
        # if token_prompt > MAX_TOKEN_CONTEXT:
        #     # 超出 token 数限制
        #     reply = RESPONSE_EXCEED_TOKEN_LIMIT % (token_prompt, MAX_TOKEN_CONTEXT)
        #     self.send_message(openid, reply, send_as_text=True)
        #     return
        user_mgr.set_pending(openid, True)
        assistant_reply = ''
        try:
            voice_name = user_mgr.get_voice_name(openid)
            if voice_name and voices_info[voice_name][-2] == 'en':
                # 若选择的语音角色说英语，则给出用英语回答的提示
                prompt += '\nPlease answer in English.'
            packet = ''
            for message in bot.invoke_chat(user_mgr.users[openid], prompt, True):
                # 系统消息，只记录不发送
                reply = message['content']
                if message['role'] == 'system':
                    if type(reply) == tuple and reply[0] == 'exceed-token-limit':
                        # 超出 token 数限制
                        raise Exception(RESPONSE_EXCEED_TOKEN_LIMIT % (reply[1], reply[2]))
                    # 系统消息，只记录不发送
                    user_mgr.add_message(openid, message)
                    continue
                if not reply: raise ConnectionError()
                reply = reply.strip('\n')
                packet += reply
                if len(packet) >= MIN_PACKET_LENGTH:
                    await self.send_as_role(ws, result='success', role='assistant', content=packet)
                    packet = ''
                assistant_reply += reply
            if packet:
                await self.send_as_role(ws, result='success', role='assistant', content=packet)
                packet = ''
            # 记录对话内容
            user_mgr.add_message(openid, make_message('assistant', assistant_reply))
            user_mgr.reduce_service_credit(openid, 'completion')
            reply = '<EOF>'
            await self.send_as_role(ws, result='success', role='system', content=reply)
            # 检查剩余可用次数
            await self.check_remaining_credit(ws, openid, 'completion')
        except Exception as e:
            self.logger.error(e)
            if type(e) == ConnectionError:
                reply = 'error-raised'
                await self.send_as_role(ws, result='fail', role='system', content=reply)
            if assistant_reply: user_mgr.add_message(openid, user_message, make_message('assistant', assistant_reply))
        user_mgr.set_pending(openid, False)

    async def process_img2img_request(self, ws, openid, **kwargs):
        self.logger.info('用户 %s 进入图生图模式', openid)
        reply = ['【系统提示】', '现在是图生图模式，请选择您想要转换成的画风（一次只能上传一张图片转换哦）：']
        reply += img2img_mgr.get_style_list(type='web')
        reply += ['想要获得提示灵感，<a href=\'#\' data-message=\'图生图提示举例\'>点击这里</a>']
        reply += ['要返回对话模式，发送<a href=\'#\' data-message=\'结束\'>结束</a>即可']
        filename = kwargs.get('filename')
        prompt = kwargs.get('prompt')
        style = kwargs.get('style')
        if filename:
            img_path = path.abspath(path.join(DIR_IMAGES_UPLOAD, filename))
            info = img2img_mgr.get_user_image_info(openid)
            if info and len(info['img_path']) >= MAX_UPLOAD_IMAGES:
                img2img_mgr.unregister_user(openid)
                reply.insert(1, '已切换新上传的原图！')
        await self.send_as_role(ws, result='success', role='system', content='\n'.join(reply))
        img2img_mgr.add_user_image_info(openid, img_path=img_path, prompt=prompt, style=style)
        user_mgr.set_img2img_mode(openid, True)
        await self.process_img2img(ws, openid)

    async def process_img2img(self, ws, openid, prompt=''):
        """
        处理图生图指令
        """
        try:
            self.logger.info('用户 %s 触发图生图指令', openid)
            if not await self.check_remaining_credit(ws, openid, 'image'): return
            if not img2img_mgr.check_img2img_valid(openid): return
            if user_mgr.get_pending(openid):
                reply = 'wait-finish'
                await self.send_as_role(ws, result='fail', role='system', content=reply)
                return
            user_mgr.set_pending(openid, True)
            results = img2img_mgr.img2img(openid)
            for dest_name, dest_path in results:
                img_url = path.join(URL_IMG2IMG_EXPORT, dest_name)
                self.logger.info('图像 url：%s', img_url)
                await self.send_as_role(ws, result='success', role='assistant', type='image', url=img_url)
                user_mgr.reduce_service_credit(openid, 'image')
        except Exception as e:
            self.logger.error(e)
            reply = 'error-raised'
            await self.send_as_role(ws, result='fail', role='system', content=reply)
        user_mgr.set_pending(openid, False)
        if await self.check_remaining_credit(ws, openid, 'image'):
            style = img2img_mgr.get_user_image_info(openid)['style']
            reply = f'【系统提示】AI 已为您将图片转变为【{style}】的效果。如果想再画一张，请<a href=\'#\' data-message=\'{web.urlquote(prompt)}\'>点击这里</a>。<a href=\'#\' data-message=\'结束\'>返回对话模式</a>'
            await self.send_as_role(ws, result='success', role='system', content=reply)
    
    async def check_remaining_credit(self, ws, openid, credit_typename, wait_before_remind=True):
        # 判断是否有剩余可用次数，如果用完则发出提示
        if user_mgr.get_remaining_service_credit(openid, credit_typename) > 0: return True
        reply = self.get_credit_used_up_reply(openid, credit_typename)
        await self.send(ws, success_json(message={"role": "system", "content": reply}))
        return False

    def get_credit_used_up_reply(self, openid, type='completion'):
            total_credit = user_mgr.get_total_service_credit(openid, type)
            grant_credit = int(total_credit / 2)
            return f"""\
❗【系统提示】您的 {total_credit} 次{CREDIT_TYPENAME_DICT[type]}使用额度已用完~
ℹ️如果您觉得AI对您有帮助，还请点击下方分享按钮转发给朋友，对方点击进入后即分享成功，每成功一次可再奖励 {grant_credit} 次额度哦~感谢支持！\
"""
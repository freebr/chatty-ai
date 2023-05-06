import _thread
import hashlib
import json
import os
import re
import requests.api as requests
import shutil
import time
import web
import xmltodict
from asyncio import new_event_loop, set_event_loop, get_event_loop
from crypt.WXBizMsgCrypt import WXBizMsgCrypt
from logging import getLogger, Logger

from configure import Config
from definition.const import \
    DEBUG_MODE,\
    MAX_DAY_SHARE_COUNT, MAX_UPLOAD_IMAGES, SHARE_GRANT_CREDIT_SCALE, SIGNUP_GRANT_CREDIT_SCALE,\
    CREDIT_TYPENAME_DICT, COMMAND_COMPLETION, COMMAND_IMAGINE, COMMAND_VARIATION,\
    DIR_CLASH, DIR_STATIC, DIR_TTS,\
    DIR_IMAGES_AI_DRAW, DIR_IMAGES_AVATAR, DIR_IMAGES_IMG2IMG, DIR_IMAGES_MARKDOWN, DIR_IMAGES_POSTER, DIR_IMAGES_QRCODE, DIR_IMAGES_UPLOAD,\
    REGEXP_MARKDOWN_IMAGE, REGEXP_TEXT_SORRY, SYSTEM_PROMPT_IMAGINE, SYSTEM_PROMPT_IMG2IMG, TTS_ENGINE,\
    URL_API, URL_CLASH_SERVER, URL_DEFAULT_USER, URL_DISCORD, URL_POSTER_EXPORT, URL_WEIXIN_BASE, WAIT_TIMEOUT
from handler import code_handler, img_handler, msg_handler
from helper.formatter import convert_encoding, fail_json, get_feature_command_string, get_headers, get_query_string, make_message, make_wx_msg_link, success_json
from helper.wx_menu import get_voice_menu, get_wx_menu
from manager import article_mgr, autoreply_mgr, chatgroup_mgr, key_token_mgr, img2img_mgr, payment_mgr, poster_mgr, user_mgr, voices_mgr, wxjsapi_mgr
from numpy import Infinity
from service.base import bot

APP_PARAM = key_token_mgr.get_app_param()
voices_info, recommended_voices = voices_mgr.get_voices_info(engine=TTS_ENGINE)
cfg = Config()
class APIController:
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger(self.__class__.__name__)
        payment_mgr.set_payment_success_callback(self.payment_success_callback)
        set_event_loop(new_event_loop())
    
    def index(self):
        web.header('Content-Type', 'text/html; charset=utf-8')
        filepath = os.path.join(DIR_STATIC, 'index.html')
        if not os.path.isfile(filepath): return web.NotFound('未找到主页文件')
        with open(filepath, 'r', encoding='utf-8') as f:
            data = f.read()
        return data
    
    def init_menu(self):
        """
        初始化菜单
        """
        media_id = article_mgr.get_media_id('upgrade')
        # 创建菜单
        url = self.wx_api_url('menu/create')
        ret = requests.post(
            url,
            data=json.dumps(get_wx_menu(
                article_id_upgrade=media_id,
                voice_menu=get_voice_menu(voices_info, recommended_voices)),
            ensure_ascii=False).encode('utf-8'),
            headers=get_headers(),
        ).json()
        return success_json(detail=ret)

    def get_rid_info(self, rid):
        """
        获取指定 rid 的信息
        """
        url = self.wx_api_url('openapi/rid/get')
        data = {
            'rid': rid,
        }
        ret = requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers=get_headers(),
        ).json()
        return json.dumps({ 'result': 'ok', 'detail': ret }, ensure_ascii=False)

    def test_connection(self, url):
        """
        测试指定网址是否连接成功
        """
        try:
            res = requests.get(url)
            return success_json(detail=res.text)
        except Exception as e:
            return fail_json(error=e.__str__())

    def list_wx_articles(self, offset=0, to_dict=True):
        """
        从微信服务器获取推文数组信息并返回
        """
        data = {
            'offset': offset,
            'count': 20,
        }
        data = requests.post(
            url=self.wx_api_url('freepublish/batchget'),
            data=json.dumps(data),
            headers=get_headers(),
        )
        ret = json.loads(convert_encoding(data.text))
        if to_dict: return ret
        return json.dumps(
            ret,
            indent=4,
            sort_keys=True,
            ensure_ascii=False,
        )

    def list_medias(self, type='image', offset=0, to_dict=True):
        """
        列出永久素材
        """
        data = {
            'type': type,
            'offset': offset,
            'count': 20,
        }
        data = requests.post(
            url=self.wx_api_url('material/batchget_material'),
            data=json.dumps(data),
            headers=get_headers(),
        )
        ret = convert_encoding(data.text)
        if to_dict: return json.loads(ret)
        return json.dumps(
            ret,
            indent=4,
            sort_keys=True,
            ensure_ascii=False,
        )

    def add_article_media_id(self):
        """
        添加推文 media id
        """
        type = web.input().get('type')
        if not type: return fail_json(message='请输入推文类型')
        media_id = web.input().get('media_id')
        if not media_id: return fail_json(message='请输入有效的推文 media id')
        return fail_json() if not article_mgr.add_media_id(type, media_id) else success_json()

    def remove_article_media_id(self):
        """
        删除推文 media id
        """
        type = web.input().get('type')
        if not type: return fail_json(message='请输入推文类型')
        media_id = web.input().get('media_id')
        if not media_id: return fail_json(message='请输入有效的推文 media id')
        return fail_json() if not article_mgr.remove_media_id(type, media_id) else success_json()

    def add_article_url(self):
        """
        添加推文 URL
        """
        type = web.input().get('type')
        if not type: return fail_json(message='请输入推文类型')
        url = web.input().get('url')
        if not url: return fail_json(message='请输入有效的推文 URL')
        return fail_json() if not article_mgr.add_url(type, url) else success_json()

    def remove_article_url(self):
        """
        删除推文 URL
        """
        type = web.input().get('type')
        if not type: return fail_json(message='请输入推文类型')
        url = web.input().get('url')
        if not url: return fail_json(message='请输入有效的推文 URL')
        return fail_json() if not article_mgr.remove_url(type, url) else success_json()

    def update_articles(self):
        """
        更新推文信息字典
        """
        try:
            cfg.load()
            article_mgr.load()
        except Exception as e:
            self.logger.error(e)
            return fail_json(message=e)
        return success_json()

    def update_features(self):
        """
        更新特性配置
        """
        try:
            cfg.load()
            user_mgr.reload_features()
        except Exception as e:
            self.logger.error(e)
            return fail_json(message=e)
        return success_json()

    def process_message(self, data):
        """
        解析消息
        """
        openid = data.get('FromUserName')
        message_type = data.get('MsgType')
        msg_data_id = data.get('MsgDataId') if 'MsgDataId' in data else None
        match message_type:
            case 'event':
                event_type = data.get('Event')
                self.process_event(openid, event_type, data.get('EventKey'))
            case 'image':
                img_url = data.get('PicUrl')
                self.process_img2img_request(openid, img_url=img_url)
            case 'text' | 'voice':
                content: str = data.get('Content') if message_type == 'text' else data.get('Recognition')
                content = content.strip()
                if content == '结束':
                    self.logger.info('用户 %s 进入文字对话模式', openid)
                    voice_name = user_mgr.get_voice_name(openid=openid)
                    if voice_name or user_mgr.get_img2img_mode(openid) or user_mgr.get_ai_draw_mode(openid):
                        reply = autoreply_mgr.get('ReturnToChatMode')
                        if voice_name:
                            user_mgr.set_voice_name(openid=openid, role=None)
                        user_mgr.set_img2img_mode(openid, False)
                        user_mgr.set_ai_draw_mode(openid, False)
                        user_mgr.set_pending(openid, False)
                        img2img_mgr.unregister_user(openid)
                    else:
                        reply = autoreply_mgr.get('MemoryCleared')
                        user_mgr.clear_conversation(openid)
                    self.send_message(openid, reply, send_as_text=True)
                    return
                if user_mgr.get_img2img_mode(openid):
                    # 按图生图风格处理
                    if content == '图生图提示举例':
                        reply = img2img_mgr.get_prompt_examples()
                        self.send_message(openid, reply, send_as_text=True)
                        return
                    try:
                        # 通过语义理解获取用户需要的风格和给出的提示
                        result = bot.invoke_single_completion(system_prompt=SYSTEM_PROMPT_IMG2IMG, content=content + '\nOutput:')
                        self.logger.info(result)
                        # 提取 JSON
                        match = re.search(r'\{(.*)\}', result, re.S)
                        # 未提取到 JSON 结构，放弃提取
                        if not match: return
                        info = json.loads(match[0])
                        self.logger.info('用户 %s 输入图生图要求：%s', openid, content)
                        # 生成模式
                        mode = info.get('mode', '').strip().lower()
                        info['mode'] = mode
                        # 风格
                        style = info.get('style', '').strip()
                        if style != 'MJ风格':
                            style = style.replace('风格', '')
                        # 提示
                        prompt = info.get('prompt', '').replace(style, '').strip()
                        # 负向提示
                        negative_prompts = info.get('negative_prompts', '').replace(style, '').strip()
                        img2img_mgr.add_user_image_info(openid, controlnet_task=mode, style=style, prompt=prompt, negative_prompts=negative_prompts)
                        self.process_img2img(openid, input=content)
                    except Exception as e:
                        self.logger.error('处理用户 %s 的图生图指令失败：%s', openid, str(e))
                        self.send_message(openid, autoreply_mgr.get('ErrorRaised'), send_as_text=True)
                    return
                if user_mgr.get_ai_draw_mode(openid):
                    # AI 作画模式
                    try:
                        self.process_ai_draw(openid, input=content)
                    except Exception as e:
                        self.logger.error('处理用户 %s 的 AI 作画指令失败：%s', openid, str(e))
                        self.send_message(openid, autoreply_mgr.get('ErrorRaised'), send_as_text=True)
                    return
                if content == '【打赏作者】':
                    self.process_donate_request(openid)
                    self.logger.info('用户 %s 点击链接“打赏作者”', openid)
                    return
                # 处理文本/语音消息
                self.logger.info('用户 %s 发送消息，长度：%s', openid, len(content))
                reply = None
                if msg_data_id:
                    self.logger.info('用户 %s 消息 msg_data_id：%s', openid, msg_data_id)
                    if user_mgr.get_see_ad(openid):
                        # 今日已阅读广告，不能再领取额度
                        reply = autoreply_mgr.get('CreditGrantedFailed')
                        self.send_message(openid, reply, send_as_text=True)
                        return
                    granted_credit = False
                    for credit_type in CREDIT_TYPENAME_DICT.keys():
                        remaining_credit = user_mgr.get_remaining_feature_credit(openid, get_feature_command_string(credit_type))
                        if remaining_credit <= 0:
                            user_mgr.reset_feature_credit(openid, get_feature_command_string(credit_type))
                            granted_credit = True
                    if granted_credit:
                        self.logger.info('%s 获得体验额度', openid)
                        reply = autoreply_mgr.get('CreditGrantedSuccess')
                        self.send_message(openid, reply, send_as_text=True)
                    elif content.startswith('已阅'):
                        reply = autoreply_mgr.get('AdRead')
                        self.send_message(openid, reply, send_as_text=True)
                    user_mgr.set_see_ad(openid, True)
                    return
                credit_typename = COMMAND_COMPLETION
                match credit_typename:
                    case COMMAND_COMPLETION:
                        self.process_chat(openid, content)
        return

    def process_event(self, openid, event_type, event_key=None):
        """
        处理关注、取关和菜单事件
        """
        match event_type:
            case 'subscribe' | 'SCAN':
                self.logger.info('用户 %s 关注公众号', openid)
                reply = autoreply_mgr.get('Subscribe')
                self.send_message(openid, reply, send_as_text=True)
                media_id = article_mgr.get_media_id('usage')
                self.push_article_by_id(openid, media_id)
                reply = autoreply_mgr.get('Welcome')
                self.send_message(openid, reply, send_as_text=True)
                return
            case 'unsubscribe':
                user_mgr.clear_conversation(openid)
                return
        key: str = event_key
        match key:
            case 'show-pay-qrcode':
                self.logger.info('用户 %s 点击菜单“打赏我们”', openid)
                self.process_donate_request(openid)
            case 'show-group-chat-qrcode':
                self.logger.info('用户 %s 点击菜单“讨论交流”', openid)
                self.send_image(openid, chatgroup_mgr.shuffle_get_qrcode())
            case 'show-level':
                self.logger.info('用户 %s 点击菜单“我的等级”', openid)
                level = user_mgr.get_vip_level(openid)
                if level == user_mgr.top_level:
                    reply = autoreply_mgr.get('LevelDescriptionTopLevel') % (level, user_mgr.vip_rights[level])
                else:
                    credit_desc = []
                    for credit_type, credit_typename in CREDIT_TYPENAME_DICT.items():
                        total_credit = user_mgr.get_total_feature_credit(openid, get_feature_command_string(credit_type))
                        remaining_credit = user_mgr.get_remaining_feature_credit(openid, get_feature_command_string(credit_type))
                        credit_desc.append(autoreply_mgr.get('LevelDescriptionCredit') % (credit_typename, total_credit, remaining_credit))
                    if level == user_mgr.free_level:
                        reply_end = autoreply_mgr.get('LevelDescriptionEndingFreeLevel')
                    else:
                        reply_end = autoreply_mgr.get('LevelDescriptionEndingVipLevel')
                    reply = autoreply_mgr.get('LevelDescriptionNormal') % (level, '\n'.join(credit_desc), reply_end)
                self.send_message(openid, reply, send_as_text=True)
            case 'ai-draw':
                self.logger.info('用户 %s 点击菜单“AI 绘画”', openid)
                if user_mgr.get_ai_draw_mode(openid):
                    self.send_message(openid, autoreply_mgr.get('AIDrawExit'), send_as_text=True)
                    user_mgr.set_ai_draw_mode(openid, False)
                else:
                    self.process_ai_draw_mode_request(openid)
            case _:
                if not key.startswith('voice:'): return
                self.process_voice_mode_request(openid, key)

    def process_chat(self, openid, prompt):
        """
        处理文本消息
        """
        # 判断是否有剩余额度
        if not self.check_remaining_credit(openid, COMMAND_COMPLETION): return
        # 判断是否在等待回答
        reply = ''
        if user_mgr.get_pending(openid):
            reply = autoreply_mgr.get('ChatPending')
        else:
            user_message = make_message('user', prompt)
            token_prompt = user_message['__token']
            self.logger.info('用户 %s 消息 token=%d', openid, token_prompt)
            # if token_prompt > MAX_TOKEN_CONTEXT:
            #     # 超出 token 数限制
            #     reply = autoreply_mgr.get('ExceedTokenLimit') % (token_prompt, MAX_TOKEN_CONTEXT)
            #     self.send_message(openid, reply, send_as_text=True)
            #     return
            user_mgr.set_pending(openid, True)
            assistant_reply = ''
            try:
                # 生成回答
                reply_result = {'is_respond': False}
                _thread.start_new_thread(self.warmly_tip,
                    (openid, WAIT_TIMEOUT, reply_result, autoreply_mgr.get('ChatWarmlyTip'))
                )
                last_sent_time = 0
                voice_name = user_mgr.get_voice_name(openid)
                if voice_name and voices_info[voice_name][-2] == 'en':
                    # 若选择的语音角色说英语，则给出用英语回答的提示
                    prompt += '\nPlease answer in English.'
                for message in bot.invoke_chat(user_mgr.users[openid], prompt):
                    reply = message['content']
                    if message['role'] == 'system':
                        if type(reply) == tuple and reply[0] == 'exceed-token-limit':
                            # 超出 token 数限制
                            raise Exception(autoreply_mgr.get('ExceedTokenLimit') % (reply[1], reply[2]))
                        # 系统消息，只记录不发送
                        user_mgr.add_message(openid, message)
                        continue
                    if not reply: raise ConnectionError()
                    reply_result['is_respond'] = True
                    self.set_typing(openid, True)
                    reply = reply.strip('\n')
                    # 保证发出下一消息前有足够时间间隔，避免微信拒绝响应
                    if last_sent_time != 0 and time.time() - last_sent_time < 2: time.sleep(1)
                    last_sent_time = time.time()
                    if re.match(r'```\s*image', reply):
                        # 获取图片
                        img_url = re.search(REGEXP_MARKDOWN_IMAGE, reply)[1]
                        img_name, src_path = self.fetch_image(openid, img_url, DIR_IMAGES_MARKDOWN)
                        success, dest_path = img_handler.crop_image(src_path)
                        if success:
                            # 发送图片
                            media_id = self.upload_wx_image(openid, img_name, dest_path)
                            if media_id: self.send_image(openid, media_id)
                            assistant_reply += reply
                    else:
                        self.send_message(openid, reply)
                        if reply.startswith('```'):
                            # 对代码片段进行处理
                            self.process_snippet(openid, reply)
                        if not re.search(REGEXP_TEXT_SORRY, reply, re.I):
                            assistant_reply += reply
                # 记录对话内容
                user_mgr.add_message(openid, user_message, make_message('assistant', assistant_reply))
                user_mgr.reduce_feature_credit(openid, get_feature_command_string(COMMAND_COMPLETION))
                self.set_typing(openid, False)
                reply = None
            except Exception as e:
                self.logger.error(e)
                if type(e) == ConnectionError: reply = autoreply_mgr.get('ErrorRaised')
                reply_result['is_respond'] = True
                if assistant_reply: user_mgr.add_message(openid, user_message, make_message('assistant', assistant_reply))
            user_mgr.set_pending(openid, False)
            self.set_typing(openid, False)
        if reply:
            self.send_message(openid, reply, send_as_text=True)

    def process_snippet(self, openid, snippet):
        """
        处理代码片段，生成代码调试链接并推送
        """
        success, data = code_handler.process_snippet(snippet)
        if not success: return False
        success, key = user_mgr.append_code_list(openid, data)
        if not success: return False
        title = '点我调试代码吧'
        description = '叮！您要的代码已生成，请点击这里调试~'
        url = self.debug_api_url(openid, key)
        self.push_link(openid, title, description, url, article_mgr.get_cover_url('snippet'))
        return True
        
    def process_img2img_request(self, openid, **kwargs):
        self.logger.info('用户 %s 进入图生图模式', openid)
        img_url = kwargs.get('img_url')
        src_path = None
        if img_url:
            # 下载图片
            src_name, src_path = self.fetch_image(openid, img_url, DIR_IMAGES_UPLOAD)
            info = img2img_mgr.get_user_image_info(openid)
            if info and len(info['img_path']) >= MAX_UPLOAD_IMAGES:
                img2img_mgr.clear_user_images(openid)
                reply = autoreply_mgr.get('Img2ImgNewPictureUploaded')
                self.send_message(openid, reply, send_as_text=True)
        reply = img2img_mgr.get_guide() % (
            '\n'.join(['❇️' + task for task in img2img_mgr.get_controlnet_task_list()]),
            '\n'.join(img2img_mgr.get_style_list()),
            '',
            make_wx_msg_link('点击这里', '图生图提示举例'),
            make_wx_msg_link('结束'),
        )
        self.send_message(openid, reply, send_as_text=True)
        reply = img2img_mgr.get_guide_examples()
        self.send_message(openid, reply, send_as_text=True)
        img2img_mgr.add_user_image_info(openid, img_path=src_path)
        user_mgr.set_img2img_mode(openid, True)

    def process_img2img(self, openid: str, input: str):
        """
        处理图生图指令
        """
        try:
            self.logger.info('用户 %s 触发图生图指令', openid)
            if not self.check_remaining_credit(openid, COMMAND_IMAGINE): return
            if not img2img_mgr.check_img2img_valid(openid):
                info = img2img_mgr.get_user_image_info(openid)
                reply = autoreply_mgr.get('Img2ImgStatus') % (info.get('controlnet_task') or '<请指定>', info.get('style') or '<请指定>', info.get('prompt') or '<未指定>', info.get('negative_prompts') or '<未指定>')
                self.send_message(openid, reply, send_as_text=True)
                return
            if user_mgr.get_pending(openid):
                reply = autoreply_mgr.get('Img2ImgPending')
                self.send_message(openid, reply, send_as_text=True)
                return
            user_mgr.set_pending(openid, True)
            media_id = None
            reply_result = {'is_respond': False}
            _thread.start_new_thread(self.warmly_tip,
                (openid, WAIT_TIMEOUT, reply_result, autoreply_mgr.get('Img2ImgWarmlyTip'))
            )
            results = img2img_mgr.img2img(openid)
            for dest_name, dest_path in results:
                reply_result['is_respond'] = True
                media_id = self.upload_wx_image(openid, dest_name, dest_path)
                if media_id:
                    self.send_image(openid, media_id)
                    user_mgr.reduce_feature_credit(openid, get_feature_command_string(COMMAND_IMAGINE))
        except Exception as e:
            self.logger.error(e)
            self.send_message(openid, autoreply_mgr.get('ErrorRaised'), send_as_text=True)
            reply_result['is_respond'] = True
        user_mgr.set_pending(openid, False)
        if self.check_remaining_credit(openid, COMMAND_IMAGINE):
            info = img2img_mgr.get_user_image_info(openid)
            reply = autoreply_mgr.get('Img2ImgSuccess') % (
                info.get('controlnet_task'),
                info.get('style'),
                info.get('prompt') or '<未指定>',
                info.get('negative_prompts') or '<未指定>',
                make_wx_msg_link('点击这里', web.urlquote(input)),
                make_wx_msg_link('返回对话模式', '结束'))
            self.send_message(openid, reply, send_as_text=True)
    
    def process_ai_draw(self, openid: str, input: str):
        """
        处理 AI 作画指令
        """
        if input == '退出垫图':
            self.send_message(openid, autoreply_mgr.get('AIDrawVariationExit'), send_as_text=True)
            return True
        # 判断是否在等待回答
        if user_mgr.get_pending(openid):
            self.send_message(openid, autoreply_mgr.get('AIDrawPending'), send_as_text=True)
            return False
        image_positions = ['左上', '右上', '左下', '右下']
        if input.startswith(':'):
            # 指令
            command = input[1:].split(':')
            match command[0]:
                case 'U' | 'VU':
                    # U|VU:task_key:image_no
                    if len(command) != 3:
                        self.send_message(openid, autoreply_mgr.get('AIDrawCommandArgInvalid'), send_as_text=True)
                        return False
                    task_key = command[1]
                    image_no = command[2]
                    if image_no not in ['1', '2', '3', '4']:
                        self.send_message(openid, autoreply_mgr.get('AIDrawCommandArgInvalid'), send_as_text=True)
                        return False
                    image_no = int(image_no)
                    user_mgr.set_pending(openid, True)
                    # 发起请求
                    url = f'{URL_DISCORD}/command'
                    data = {
                        'command': 'upscale',
                        'user_id': openid,
                        'task_name': 'imagine' if command[0] == 'U' else 'variation',
                        'task_key': task_key,
                        'image_no': image_no,
                    }
                    res = requests.post(
                        url,
                        data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                        headers=get_headers(),
                    )
                    if res.status_code != 200:
                        self.send_message(openid, autoreply_mgr.get('ErrorRaised'), send_as_text=True)
                        user_mgr.set_pending(openid, False)
                        return False
                    result = res.json()
                    if result['code'] != 0:
                        self.logger.error('调用 Discord 接口时发生错误：%s', result)
                        self.send_message(openid, autoreply_mgr.get('ErrorRaised'), send_as_text=True)
                        user_mgr.set_pending(openid, False)
                        return False
                    task_key = result['detail']['task_key']
                    img_url = result['detail']['url']
                    # 下载图片
                    img_name, src_path = self.fetch_image(openid, img_url, DIR_IMAGES_AI_DRAW)
                    # 发送图片
                    media_id = self.upload_wx_image(openid, img_name, src_path)
                    if not media_id:
                        self.logger.error('上传图片失败')
                        self.send_message(openid, autoreply_mgr.get('ErrorRaised'), send_as_text=True)
                        user_mgr.set_pending(openid, False)
                        return False
                    self.send_image(openid, media_id)
                    # 发送提示消息
                    link_variation = make_wx_msg_link('这张', f':V:{task_key}:0')
                    reply = autoreply_mgr.get('AIDrawUpscaleSuccess') % link_variation
                    self.send_message(openid, reply, send_as_text=True)
                    user_mgr.set_pending(openid, False)
                    return True
                case 'V':
                    # V:task_key:image_no
                    if len(command) != 3:
                        self.send_message(openid, autoreply_mgr.get('AIDrawCommandArgInvalid'), send_as_text=True)
                        return False
                    task_key = command[1]
                    image_no = command[2]
                    if image_no not in ['0', '1', '2', '3', '4']:
                        self.send_message(openid, autoreply_mgr.get('AIDrawCommandArgInvalid'), send_as_text=True)
                        return False
                    image_no = int(image_no)
                    user_mgr.set_ai_draw_variation(openid, {
                        'task_key': task_key,
                        'image_no': image_no
                    })
                    reply = autoreply_mgr.get('AIDrawVariationEnter') % image_positions[image_no]
                    self.send_message(openid, reply, send_as_text=True)
                    return True
                case _:
                    self.send_message(openid, autoreply_mgr.get('AIDrawCommandArgInvalid'), send_as_text=True)
                    return False
        # 处理 imagine 或 variation 指令
        tempstr = input.lower()
        variation_info = user_mgr.get_ai_draw_variation(openid)
        if variation_info:
            command = COMMAND_VARIATION
        else:
            if 'http://' in tempstr or 'https://' in tempstr:
                # 输入包含 URL，判断为垫图绘画
                command = COMMAND_VARIATION
            else:
                command = COMMAND_IMAGINE
        # 判断是否有剩余额度
        if not self.check_remaining_credit(openid, command): return False
        user_mgr.set_pending(openid, True)
        # 内容审查
        moderated, category = bot.moderate(user_mgr.users[openid], input)
        if not moderated:
            self.send_message(openid, autoreply_mgr.get('AIDrawModerationFailed'), send_as_text=True)
            user_mgr.set_pending(openid, False)
            return False
        self.logger.info('用户 %s 输入作画描述：%s', openid, input)
        if input.startswith('@'):
            # 自由式
            prompt = input[1:]
        else:
            # 翻译提示词
            prompt = bot.invoke_single_completion(system_prompt=SYSTEM_PROMPT_IMAGINE, content=input + '\nOutput:')
            self.logger.info('用户 %s 的作画描述转换为提示词：%s', openid, prompt)
        # 发起请求
        url = f'{URL_DISCORD}/command'
        if variation_info:
            data = {
                'command': 'variation',
                'user_id': openid,
                'task_name': 'upscale' if variation_info['image_no'] == 0 else 'imagine',
                'task_key': variation_info['task_key'],
                'image_no': variation_info['image_no'],
                'prompt': prompt,
            }
        else:
            data = {
                'command': 'imagine',
                'user_id': openid,
                'prompt': prompt,
            }
        res = requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers=get_headers(),
        )
        if res.status_code != 200:
            self.send_message(openid, autoreply_mgr.get('ErrorRaised'), send_as_text=True)
            user_mgr.set_pending(openid, False)
            return False
        result = res.json()
        if result['code'] != 0:
            self.logger.error('调用 Discord 接口时发生错误：%s', result)
            self.send_message(openid, autoreply_mgr.get('ErrorRaised'), send_as_text=True)
            user_mgr.set_pending(openid, False)
            return False
        task_key = result['detail']['task_key']
        img_url = result['detail']['url']
        # 下载图片
        img_name, src_path = self.fetch_image(openid, img_url, DIR_IMAGES_AI_DRAW)
        # 发送图片
        media_id = self.upload_wx_image(openid, img_name, src_path)
        if not media_id:
            self.logger.error('上传图片失败')
            self.send_message(openid, autoreply_mgr.get('ErrorRaised'), send_as_text=True)
            user_mgr.set_pending(openid, False)
            return False
        self.send_image(openid, media_id)
        # 发送提示消息
        links_upscale = [
            make_wx_msg_link(display_text, f':U:{task_key}:{index + 1}')
            for index, display_text in enumerate(image_positions)
        ]
        links_variation = [
            make_wx_msg_link(display_text, f':U:{task_key}:{index + 1}')
            for index, display_text in enumerate(image_positions)
        ]
        if variation_info:
            reply = autoreply_mgr.get('AIDrawVariationSuccess') % (
                '|'.join(links_upscale),
                '|'.join(links_variation),
                make_wx_msg_link('退出垫图')
            )
        else:
            reply = autoreply_mgr.get('AIDrawImagineSuccess') % (
                '|'.join(links_upscale),
                '|'.join(links_variation)
            )
        self.send_message(openid, reply, send_as_text=True)
        user_mgr.reduce_feature_credit(openid, get_feature_command_string(command))
        self.check_remaining_credit(openid, command)
        user_mgr.set_pending(openid, False)
        return True

    def process_donate_request(self, openid):
        self.send_image(openid, media_id=self.get_pay_qrcode(openid))

    def process_voice_mode_request(self, openid, voice_key):
        """
        处理进入语音模式指令
        """
        old_name = user_mgr.get_voice_name(openid=openid)
        new_name = voice_key[6:]
        if old_name == new_name:
            user_mgr.set_voice_name(openid=openid, role=None)
            reply = autoreply_mgr.get('ReturnToChatMode')
        else:
            self.logger.info('用户 %s 进入语音对话模式，角色：【%s】', openid, new_name)
            user_mgr.set_voice_name(openid=openid, role=new_name)
            if old_name:
                reply = autoreply_mgr.get('VoiceChanged') % new_name
            else:
                reply = autoreply_mgr.get('VoiceGuide') % new_name
        self.send_message(openid, reply, send_as_text=True)

    def process_ai_draw_mode_request(self, openid):
        self.logger.info('用户 %s 进入 AI 作画模式', openid)
        user_mgr.set_ai_draw_mode(openid, True)
        reply = autoreply_mgr.get('AIDrawGuide') % (
            user_mgr.get_vip_level(openid),
            user_mgr.get_total_feature_credit(openid, get_feature_command_string(COMMAND_IMAGINE)),
            user_mgr.get_remaining_feature_credit(openid, get_feature_command_string(COMMAND_IMAGINE)),
            user_mgr.get_total_feature_credit(openid, get_feature_command_string(COMMAND_VARIATION)),
            user_mgr.get_remaining_feature_credit(openid, get_feature_command_string(COMMAND_VARIATION)),
            make_wx_msg_link('结束')
        )
        self.send_message(openid, reply, send_as_text=True)

    def check_remaining_credit(self, openid, credit_type, wait_before_remind=True):
        # 判断是否有剩余额度，如果用完则发出提示
        if user_mgr.get_remaining_feature_credit(openid, get_feature_command_string(credit_type)) > 0: return True
        reply = self.get_credit_used_up_reply(openid, credit_type)
        if wait_before_remind: time.sleep(5)
        self.send_message(openid, reply, send_as_text=True)
        article_url = article_mgr.shuffle_get_url('ad')
        self.push_article_by_url(openid, article_url)
        return False

    def get_credit_used_up_reply(self, openid, credit_type):
        total_credit = user_mgr.get_total_feature_credit(openid, get_feature_command_string(credit_type))
        return autoreply_mgr.get('NoCreditWechat') % (total_credit, CREDIT_TYPENAME_DICT[credit_type])

    def payment_success_callback(self, openid, out_trade_no, pay_amount):
        self.logger.info('用户 %s 订单 %s 支付金额 %s 元', openid, out_trade_no, pay_amount / 100)
        paid_amount = payment_mgr.get_paid_amount_by_openid(openid)
        if paid_amount: self.logger.info('用户 %s 先前已支付金额 %s 元', openid, paid_amount / 100)
        total_amount = paid_amount + pay_amount
        self.logger.info('用户 %s 合计支付金额 %s 元', openid, total_amount / 100)
        level_upgrade, rights = user_mgr.get_level_rights_by_amount(total_amount / 100)
        # 检查此订单之前是否已处理
        pay_info = payment_mgr.get_pay_info_by_out_trade_no(out_trade_no)
        if pay_info and pay_info['OutTradeNo'] == out_trade_no:
            self.logger.info('先前记录支付信息：%s', pay_info)
            self.logger.warn('收到订单 %s 支付通知，但此订单已处理', out_trade_no)
            return True
        wx_user_info: dict = user_mgr.get_wx_user_info(openid)
        if not wx_user_info:
            headimgurl = URL_DEFAULT_USER
        else:
            headimgurl = wx_user_info.get('headimgurl', URL_DEFAULT_USER)
        # 记录支付信息
        payment_mgr.add_pay_info(openid=openid,
            before_level=user_mgr.get_vip_level(openid),
            headimgurl=headimgurl,
            out_trade_no=out_trade_no,
            pay_amount=pay_amount, pay_level=level_upgrade, pay_time=time.ctime(),
        )
        if (not level_upgrade) or level_upgrade == user_mgr.get_vip_level(openid):
            message = autoreply_mgr.get('DonateSuccess')
        else:
            # 升级用户等级
            success = user_mgr.add_vip(openid, level_upgrade)
            if success:
                self.logger.info('用户 %s 等级升级为【%s】', openid, level_upgrade)
                message = autoreply_mgr.get('UpgradeVipLevel') % (level_upgrade, rights)
            else:
                self.logger.error('用户 %s 等级未能升级为【%s】，该等级不存在', openid, level_upgrade)
                message = autoreply_mgr.get('UpgradeFailed')
        ws = user_mgr.get_ws(openid)
        if ws:
            try:
                # 通过 Websocket 发送支付/升级成功消息，H5页面接收
                reply = success_json(message={'role': 'system', 'content': message})
                get_event_loop().run_until_complete(ws.send(reply))
            except Exception as e:
                self.logger.warn('用户 %s 已断开 WebSocket 连接，通过微信服务器发送支付/升级成功消息', openid)
                self.send_message(openid, message, send_as_text=True)
        else:
            # 通过微信服务器发送支付/升级成功消息，公众号界面接收
            self.send_message(openid, message, send_as_text=True)
        return True
    
    def set_remaining_feature_credit(self, openid, credit_type):
        """
        设置指定用户、指定类型的可用次数
        """
        if len(openid) == 0: openid = '*'
        credit_value = get_query_string()
        return fail_json() if not user_mgr.set_remaining_feature_credit(openid, get_feature_command_string(credit_type), credit_value) else success_json()

    def dump_user_info(self):
        """
        转储用户信息
        """
        openid = web.input().get('openid')
        if not openid: return fail_json()
        ret: bool
        if openid == '*':
            ret = user_mgr.dump_all_users()
        else:
            ret = user_mgr.dump_user(openid=openid)
        return success_json() if ret else fail_json()

    def get_login_user_list(self):
        """
        返回全部已登录用户信息
        """
        return success_json(users=user_mgr.get_login_user_list())

    def get_user_info(self, openid=''):
        """
        返回用户信息
        """
        self.cross_origin()
        login_time = user_mgr.get_login_time(openid)
        level = user_mgr.get_vip_level(openid)
        if level == -1: return fail_json(message='用户不存在')
        total_credit = {}
        remaining_credit = {}
        for credit_type in CREDIT_TYPENAME_DICT:
            total_credit[credit_type] = user_mgr.get_total_feature_credit(openid, get_feature_command_string(credit_type))
            if total_credit[credit_type] == Infinity: total_credit[credit_type] = 'infinity'
            remaining_credit[credit_type] = user_mgr.get_remaining_feature_credit(openid, get_feature_command_string(credit_type))
            if remaining_credit[credit_type] == Infinity: remaining_credit[credit_type] = 'infinity'
        return success_json(
            openid=openid,
            login_time=login_time,
            level=level,
            total_credit=total_credit,
            remaining_credit=remaining_credit,
        )

    def get_vip_level(self, openid=''):
        """
        返回用户 VIP 等级
        """
        level = user_mgr.get_vip_level(openid)
        if level == -1: return fail_json(message='用户不存在')
        return success_json(
            openid=openid,
            level=level,
        )

    def add_vip(self, openid='', level='白银'):
        """
        增加 VIP 用户
        """
        return fail_json() if not user_mgr.add_vip(openid, level) else success_json()

    def remove_vip(self, openid=''):
        """
        删除 VIP 用户
        """
        return fail_json() if not user_mgr.remove_vip(openid) else success_json()

    def signup(self, openid):
        """
        设置指定用户的签到状态，如第一次签到则赠送额度
        """
        signup = user_mgr.get_signup(openid)
        if signup:
            return fail_json(message='您今日已签到')
        user_mgr.set_signup(openid, True)
        for credit_type in CREDIT_TYPENAME_DICT:
            total_credit = user_mgr.get_total_feature_credit(openid, get_feature_command_string(credit_type))
            grant_credit = int(total_credit * SIGNUP_GRANT_CREDIT_SCALE)
            user_mgr.grant_credit(openid, credit_type, grant_credit)
        self.logger.info('用户 %s 签到成功', openid)
        return success_json()

    def clash_get_config(self):
        """
        获取 Clash 正在使用的配置文件
        """
        try:
            secret = key_token_mgr.api_keys.get('Clash')[0]
            res = requests.get(
                    self.clash_api_url('configs'),
                    headers={
                        'Authorization': f'Bearer {secret}',
                    }
                )
        except Exception as e:
            self.logger.error('获取 Clash 配置失败：', str(e))
            return fail_json(detail=str(e))
        if res.status_code != 200:
            self.logger.error('获取 Clash 配置失败')
            return fail_json(detail=res.json())
        return success_json(detail=res.json())

    def clash_set_config(self):
        """
        设置 Clash 使用的配置文件
        """
        name = web.input().get('name', 'fastlink')
        data = {
            'path': os.path.join(DIR_CLASH, 'config-' + name + '.yaml'),
        }
        res = requests.put(
                self.clash_api_url('configs', 'force=true'),
                data=json.dumps(data, ensure_ascii=False),
                headers={
                    'Authorization': f'Bearer {key_token_mgr.configs.get("api_keys").get("Clash")}',
                },
                proxies={
                    'http': '',
                },
            )
        self.logger.info(os.path.join(DIR_CLASH, 'config-' + name + '.yaml'))
        if res.status_code != 204:
            self.logger.error('Clash 配置更改为 %s 失败', name)
            return fail_json(status_code=res.status_code, detail=res.text)
        match name:
            case 'fastlink':
                os.environ['ALL_PROXY'] = 'socks5h://127.0.0.1:7891'
            case _:
                os.environ['ALL_PROXY'] = 'http://127.0.0.1:8888'
        self.logger.info('Clash 配置已更改为：%s', name)
        return success_json(detail=res.text)

    def clear_pending(self, openid):
        """
        清除指定用户的等待状态，没有指定则清除全部用户的等待状态
        """
        if len(openid) == 0: openid = '*'
        user_mgr.set_pending(openid, False)
        return success_json()

    def clear_conversation(self, openid):
        """
        清空指定对话，没有指定则清空所有对话
        """
        if len(openid) == 0: openid = '*'
        user_mgr.clear_conversation(openid)
        return success_json()

    def clear_image_files(self, type):
        """
        清空指定类型的生成图片文件
        """
        try:
            match type:
                case 'avatar': dir_path = DIR_IMAGES_AVATAR
                case 'img2img': dir_path = DIR_IMAGES_IMG2IMG
                case 'markdown': dir_path = DIR_IMAGES_MARKDOWN
                case 'poster': dir_path = DIR_IMAGES_POSTER
                case 'qrcode': dir_path = DIR_IMAGES_QRCODE
                case 'upload': dir_path = DIR_IMAGES_UPLOAD
                case _: raise Exception('未指定 type')
            shutil.rmtree(dir_path)
            os.mkdir(dir_path)
            self.logger.info('类型[%s]的图片文件存放目录 %s 已清空', type, dir_path)
        except Exception as e:
            self.logger.error(e)
            return fail_json(message=e)
        return success_json()

    def clear_voice_files(self):
        """
        清空生成和转换的语音文件
        """
        try:
            shutil.rmtree(DIR_TTS)
            os.mkdir(DIR_TTS)
            self.logger.info('语音文件存放目录 %s 已清空', DIR_TTS)
        except Exception as e:
            self.logger.error(e)
            return fail_json(message=e)
        return success_json()

    def clear_voice_files(self):
        """
        清空生成和转换的语音文件
        """
        try:
            shutil.rmtree(DIR_TTS)
            os.mkdir(DIR_TTS)
            self.logger.info('语音文件存放目录 %s 已清空', DIR_TTS)
        except Exception as e:
            self.logger.error(e)
            return fail_json(message=e)
        return success_json()

    def reset_user(self, openid):
        return success_json() if user_mgr.reset_user(openid,
            reset_conversation=True,
            reset_credits=True,
            reset_daily_data=True,
            reset_invited_users=True,
            reset_login_time=True,
            reset_pending=True,
            reset_ws=True,
            reset_wx_user_info=True,
        ) else fail_json()
        
    def update_autoreply(self):
        """
        更新自动回复消息内容
        """
        try:
            cfg.load()
            autoreply_mgr.load()
        except Exception as e:
            self.logger.error(e)
            return fail_json(message=e)
        return success_json()
        
    def reload_config(self):
        """
        重新加载配置
        """
        try:
            cfg.load()
        except Exception as e:
            self.logger.error(e)
            return fail_json(message=e)
        return success_json()

    def show_debug_code(self):
        openid = web.input().get('openid')
        key = web.input().get('key')
        if not key: return autoreply_mgr.get('SnippetNotExisted')
        self.logger.info('收到中转至代码调试工具请求：username=%s, key=%s', openid, key)
        data = user_mgr.get_code_list_item(openid, key)
        if not data: return autoreply_mgr.get('SnippetNotExisted')
        web.header('Content-Type', 'text/html; charset=utf-8')
        return code_handler.get_debug_html(data)
        
    def get_donate_price(self):
        """
        返回当前设置的打赏金额
        """
        return success_json(price=cfg.data.prices.get('Donation'))

    def set_donate_price(self):
        """
        设置打赏金额
        """
        price = web.input().get('price')
        if not price:
            return fail_json(message='请输入付款金额（单位：元，可精确到两位小数）！')
        elif not re.match('\\d+(.\\d(\\d)?)?', price):
            return fail_json(message='请输入有效的付款金额（单位：元，可精确到两位小数）！')
        cfg.data.prices['Donation'] = float(price)
        cfg.save()
        return success_json()

    def update_bot_access_token(self):
        """
        设置 OpenAI access token
        """
        if not bot.update_access_tokens(d=key_token_mgr.access_tokens.get('Services')):
            self.logger.error('更新 OpenAI access token 列表失败')
            return fail_json()
        self.logger.info('更新 OpenAI access token 列表成功')
        return success_json()

    def update_wx_access_token(self):
        """
        更新微信 access token
        """
        try:
            access_token = web.input().get('access-token')
            dict_tokens = key_token_mgr.access_tokens
            dict_tokens['WeChat'] = access_token
            key_token_mgr.save()
            self.logger.info('更新微信 access token 成功，value=%s', access_token)
            return success_json()
        except Exception as e:
            message = '更新微信 access token 失败：%s' % str(e)
            self.logger.error(message)
            return fail_json(message=message)

    def update_bot_api_key_list(self):
        """
        更新 OpenAI API key 列表
        """
        if not bot.update_api_keys(d=key_token_mgr.api_keys.get('Services')):
            self.logger.error('更新 OpenAI API key 列表失败')
            return fail_json()
        self.logger.info('更新 OpenAI API key 列表成功')
        bot.services = bot.import_services()
        return success_json()

    def update_sensitive_words(self):
        """
        更新敏感词词典
        """
        if not msg_handler.read_sensitive_words():
            self.logger.error('更新敏感词词典失败')
            return fail_json()
        self.logger.info('更新敏感词词典成功')
        return success_json()

    def send_message(self, openid, message, send_as_text=False):
        """
        回复文本或语音消息到指定用户
        """
        if not message: return
        if DEBUG_MODE:
            self.logger.debug('发送消息：%s', message)
            return
        try:
            voice_name = user_mgr.get_voice_name(openid)
            if voice_name and not send_as_text:
                success, output_filepath = voices_mgr.run_tts(message, voice_name=voice_name)
                if not success: raise Exception('调用合成语音接口失败')
                output_filename = os.path.basename(output_filepath)
                # 上传语音
                url = self.wx_api_url('media/upload', 'type=voice')
                upload_data = {
                    'media': (output_filename, open(output_filepath, 'rb'), 'application/octet-stream')
                }
                res = requests.post(
                    url,
                    files=upload_data,
                ).json()
                if 'media_id' in res:
                    media_id = res['media_id']
                else:
                    raise Exception(json.dumps(res, ensure_ascii=False))
                data = {
                    'touser': openid,
                    'msgtype': 'voice',
                    'voice': {
                        'media_id': media_id,
                    },
                }
            else:
                data = {
                    'touser': openid,
                    'msgtype': 'text',
                    'text': {
                        'content': message,
                    },
                }
            url = self.wx_api_url('message/custom/send')
            res = requests.post(
                url,
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                headers=get_headers(),
            ).json()
            self.logger.info('微信回复：%s', res)
        except Exception as e:
            message = '回复文本或语音消息到用户 {} 失败：{}'.format(openid, str(e))
            self.logger.error(message)

    def send_image(self, openid, media_id):
        """
        回复图片消息到指定用户
        """
        if DEBUG_MODE:
            self.logger.debug('发送图片消息，media_id=%s', media_id)
            return
        self.logger.info('发送图像，media_id=%s', media_id)
        try:
            url = self.wx_api_url('message/custom/send')
            data = {
                'touser': openid,
                'msgtype': 'image',
                'image': {
                    'media_id': media_id,
                },
            }
            return requests.post(
                url,
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                headers=get_headers(),
            )
        except Exception as e:
            message = '回复图片消息到用户 {} 失败：{}'.format(openid, str(e))
            self.logger.error(message)

    def upload_wx_image(self, openid, img_name, image_path):
        """
        上传指定图片作为临时素材
        """
        try:
            url = self.wx_api_url('media/upload', 'type=image')
            with open(image_path, 'rb') as f:
                upload_data = {
                    'media': (img_name, f, 'image/jpg')
                }
                res = requests.post(
                    url,
                    files=upload_data,
                ).json()
            if 'media_id' in res:
                media_id = res['media_id']
                self.logger.info('用户 %s 上传图片素材成功：%s', openid, image_path)
                return media_id
            else:
                raise Exception(json.dumps(res, ensure_ascii=False))
        except Exception as e:
            message = '用户 {} 上传图片素材失败：{}'.format(openid, str(e))
            self.logger.error(message)
            raise Exception(message)

    def fetch_image(self, openid, img_url, dest_dir):
        """
        从指定 URL 下载图片并保存，返回文件名称和路径
        """
        try:
            res = requests.get(img_url, stream=True)
            img_name = str(round(time.time())) + '.jpg'
            img_path = os.path.abspath(os.path.join(dest_dir, img_name))
            if not os.path.exists(dest_dir): os.mkdir(dest_dir)
            with open(img_path, 'wb') as f:
                for chunk in res.iter_content(chunk_size=32):
                    f.write(chunk)
            self.logger.info('用户 %s 下载图片成功，目标路径：%s', openid, img_path)
            return (img_name, img_path)
        except Exception as e:
            message = '用户 {} 下载图片失败：{}'.format(openid, str(e))
            self.logger.error(message)
            raise Exception(message)
    
    def set_typing(self, openid, typing):
        """
        设置对指定用户的输入状态
        """
        if DEBUG_MODE: return
        url = self.wx_api_url('message/custom/typing')
        data = {
            'touser': openid,
            'command': 'Typing' if typing else 'CancelTyping',
        }
        return requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers=get_headers(),
        )

    def get_pay_qrcode(self, openid):
        # media_id = 'LcVB-VNdn-QGqqjWJ6Eeu7FXDSqzFcSv8Yk7A48czcaXJFQsEnqA8A0xRw0bCJtY'
        # return media_id
        try:
            pay_qrcode_path, out_trade_no = payment_mgr.create_native_pay(
                description='打赏·查小特AI',
                price=cfg.data.prices.get('Donation'),
                to_file=True,
            )
            if out_trade_no:
                # 上传付款码图片
                media_id =self.upload_wx_image(openid, os.path.basename(pay_qrcode_path), pay_qrcode_path)
                self.send_message(openid, autoreply_mgr.get('DonateTip'), send_as_text=True)
                if media_id:
                    self.logger.info('付款码 media_id：%s', media_id)
                    return media_id
        except Exception as e:
            self.logger.error('付款码 media id 获取失败：%s', e)
            return None

    def push_article_by_id(self, openid, article_id):
        """
        推送指定 id 的图文消息到指定用户
        """
        url = self.wx_api_url('message/custom/send')
        data = {
            'touser': openid,
            'msgtype': 'mpnewsarticle',
            'mpnewsarticle':
            {
                'article_id': article_id,
            }
        }
        return requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers=get_headers(),
        )

    def push_article_by_url(self, openid, article_url):
        """
        推送指定 url 的图文消息（小型）到指定用户
        """
        url = self.wx_api_url('message/custom/send')
        data = {
            'touser': openid,
            'msgtype': 'news',
            'news': {
                'articles': [
                    {
                        'title': '推文',
                        'description': """为了更好提供服务，还请点下这则推文→进去滑到最底端（不用看正文！)→发消息→回复'已阅'，您就能帮助我们获得收益，使我们得以持续运营下去！再次感谢您的支持与厚爱❤""",
                        'url': article_url,
                        'picurl': article_mgr.get_cover_url('ad'),
                    }
                ]
            }
        }
        return requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers=get_headers(),
        )

    def push_link(self, openid, title, description, link_url, cover_url):
        """
        推送指定 url 的链接到指定用户
        """
        url = self.wx_api_url('message/custom/send')
        data = {
            'touser': openid,
            'msgtype': 'news',
            'news': {
                'articles': [
                    {
                        'title': title,
                        'description': description,
                        'url': link_url,
                        'picurl': cover_url,
                    }
                ]
            }
        }
        return requests.post(
            url,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers=get_headers(),
        )

    def validate_wechat_token(self):
        """
        验证微信发送的 token 请求
        """
        try:
            data = web.input()
            if len(data) == 0:
                return 'Error: no data provided!'
            signature = data.signature
            timestamp = data.timestamp
            nonce = data.nonce
            echostr = data.echostr
            
            list = [APP_PARAM['APPTOKEN'], timestamp, nonce]
            list.sort()
            sha1 = hashlib.sha1()
            sha1.update(list[0].encode('utf-8'))
            sha1.update(list[1].encode('utf-8'))
            sha1.update(list[2].encode('utf-8'))
            hashcode = sha1.hexdigest()  # 获取加密串

            # 验证
            if hashcode == signature:
                self.logger.info('Token 验证成功')
                return echostr
            else:
                return ''
        except Exception as e:
            return e

    def warmly_tip(self, openid, timeout, reply_result, tip=''):
        """
        等待给定时间（秒）后，若模型未返回输出，则发送耐心等待的提示给用户
        """
        time.sleep(timeout)
        if reply_result['is_respond']: return
        return self.send_message(openid, tip, send_as_text=True)

    def wx_api_url(self, name, querystring=''):
        """
        根据指定的 name 返回对应的微信 API 接口 URL
        """
        if querystring: querystring = '&' + querystring
        access_token = key_token_mgr.access_tokens.get('WeChat')
        return f'{URL_WEIXIN_BASE}/{name}?access_token={access_token}{querystring}'

    def clash_api_url(self, name, querystring=''):
        """
        根据指定的 name 返回对应的 Clash API 接口 URL
        """
        if querystring: querystring = '?' + querystring
        return f'{URL_CLASH_SERVER}/{name}{querystring}'

    def debug_api_url(self, openid, key):
        """
        根据指定的 openid 和 key 返回对应的代码调试工具中转 URL
        """
        return f'{URL_API}/debug-code?openid={openid}&key={key}'

    def get_chat_param(self):
        return success_json(param=bot.get_chat_param())

    def set_chat_param(self):
        temperature = web.input().get('temperature')
        frequency_penalty = web.input().get('frequency_penalty')
        presence_penalty = web.input().get('presence_penalty')
        if not bot.set_chat_param(temperature=temperature, frequency_penalty=frequency_penalty, presence_penalty=presence_penalty):
            return fail_json()
        return success_json()

    def get_wx_jsapi_param(self):
        try:
            url = web.input().get('url')
            if not url: raise Exception('缺少 url')
            self.cross_origin()
            wxjsapi_mgr.update_access_token(key_token_mgr.access_tokens.get('WeChat'))
            param = wxjsapi_mgr.get_sign_param(url=url)
            param['appId'] = APP_PARAM['APPID']
            return success_json(**param)
        except Exception as e:
            return fail_json(message=str(e))

    def get_wx_user_info(self):
        try:
            code = web.input().get('code')
            state = web.input().get('state')
            user_info = wxjsapi_mgr.get_wx_user_info(code)
            if not code: raise Exception('缺少 code')
            openid_login = user_info['openid']
            user_mgr.set_wx_user_info(openid_login, user_info)
            if state:
                # 分享链接，赠送额度
                openid_invitor = state
                nickname_login = user_info['nickname']
                if openid_invitor != '0' and openid_invitor != openid_login:
                    day_share_count = user_mgr.get_day_share_count(openid_invitor)
                    granted = False
                    grant_credit = 0
                    reason = ''
                    if day_share_count >= MAX_DAY_SHARE_COUNT:
                        # 达到本日最大分享次数，不再赠送额度
                        reason = 'max-day-share-count'
                    elif user_mgr.is_invited_user(openid_invitor, openid_login):
                        reason = 'user-invited'
                    else:
                        user_mgr.set_day_share_count(openid_invitor, day_share_count + 1)
                        user_mgr.add_invited_user(openid_invitor, openid_login)
                        for credit_type in CREDIT_TYPENAME_DICT:
                            total_credit = user_mgr.get_total_feature_credit(openid_invitor, get_feature_command_string(credit_type))
                            grant_credit = int(total_credit * SHARE_GRANT_CREDIT_SCALE)
                            granted = user_mgr.grant_credit(openid_invitor, credit_type, grant_credit)
                    if granted:
                        result = success_json(message={'role': 'system', 'content': 'grant-credit', 'count': grant_credit, 'nickname_invitee': nickname_login})
                    else:
                        result = fail_json(message={'role': 'system', 'content': 'grant-credit', 'reason': reason, 'nickname_invitee': nickname_login})
                    try:
                        ws = user_mgr.get_ws(openid_invitor)
                        if ws: get_event_loop().run_until_complete(ws.send(result))
                    except Exception as e:
                        self.logger.error('赠送额度失败：%s', str(e))
            self.cross_origin()
            return success_json(**user_info)
        except Exception as e:
            return fail_json(message=str(e))

    def get_pay_info(self):
        """
        返回支付信息列表
        """
        pay_info = payment_mgr.pay_info
        return success_json(**pay_info)

    def get_pay_stats(self):
        """
        返回支付记录统计信息
        """
        pay_stats = payment_mgr.pay_info.get('Statistics')
        self.cross_origin()
        return success_json(**pay_stats)

    def make_poster(self):
        """
        生成分享海报
        """
        openid: str = web.input().get('openid', '').strip()
        nickname: str = web.input().get('nickname', '').strip()
        headimgurl: str = web.input().get('headimgurl', '').strip()
        headimg_name, headimg_path = self.fetch_image(openid, headimgurl, DIR_IMAGES_AVATAR)
        poster_name, poster_path = poster_mgr.make_poster(openid=openid, nickname=nickname, headimg_path=headimg_path)
        if not poster_name: return fail_json()
        poster_url = URL_POSTER_EXPORT + poster_name
        self.cross_origin()
        return success_json(url=poster_url)

    def upload_file(self):
        """
        上传文件（仅限图片）
        """
        try:
            self.cross_origin()
            openid: str = web.input().get('openid', '').strip()
            if not openid: raise Exception('缺少 openid')
            body = web.input(file={})
            filetype = body.file.filename.split('.', 1)[-1]
            filename = str(round(time.time())) + '.' + filetype
            filepath = os.path.abspath(os.path.join(DIR_IMAGES_UPLOAD, filename))
            if not os.path.exists(DIR_IMAGES_UPLOAD): os.mkdir(DIR_IMAGES_UPLOAD)
            with open(filepath, 'wb') as f: f.write(body.file.file.read())
            self.logger.info('用户 %s 上传文件成功，文件名：%s', openid, filename)
            return success_json(filename=filename)
        except Exception as e:
            self.logger.error('用户 %s 上传文件失败：%s', openid, str(e))
            return fail_json(message=str(e))

    def cross_origin(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Access-Control-Allow-Headers', 'X-Requested-With,Content-Type')
        web.header('Access-Control-Allow-Methods', 'GET, POST, PUT')

    def POST(self, api_name: str):
        web.header('Content-Type', 'application/json; charset=utf-8')
        if not api_name: api_name = '/'
        seq = api_name[1:].split('/')
        match seq:
            case ['pay', 'create']:
                self.cross_origin()
                input = web.input()
                openid = input.get('openid')
                level = input.get('level')
                description = f'查小特AI服务-{level}会员'
                price = user_mgr.vip_prices.get(level)
                if not level:
                    return fail_json(message='请输入要升级的等级！')
                elif not price:
                    return fail_json(message='等级名称无效！')
                result = payment_mgr.create_jsapi_pay(
                    openid=openid,
                    description=description,
                    price=price,
                )
                if type(result) != dict: return fail_json(message=str(result))
                return success_json(**result)
            case ['pay', 'notify']:
                self.cross_origin()
                return payment_mgr.notify_pay()
            case _:
                raw_data = web.data().decode('utf-8')
                if '<Encrypt>' in raw_data:
                    input = web.input()
                    timestamp = input.get('timestamp')
                    nonce = input.get('nonce')
                    msg_sign = input.get('msg_signature')
                    decryptor = WXBizMsgCrypt(APP_PARAM['APPTOKEN'], APP_PARAM['ENCODING_AES_KEY'], APP_PARAM['APPID'])
                    ret, decrypt_xml = decryptor.DecryptMsg(raw_data, msg_sign, timestamp, nonce)
                    # 将XML格式转换为字典
                    data = xmltodict.parse(decrypt_xml)
                else:
                    data = xmltodict.parse(raw_data)
                # 调用消息处理函数
                _thread.start_new_thread(self.process_message, (data.get('xml'),))
                return 'success'

    def GET(self, api_name: str):
        web.header('Content-Type', 'application/json; charset=utf-8')
        if not api_name: api_name = '/'
        seq = api_name[1:].split('/')
        match seq:
            case ['access-token', 'update']:
                return self.update_bot_access_token()
            case ['access-token', 'wx', 'update']:
                return self.update_wx_access_token()
            case ['api-key', 'update']:
                return self.update_bot_api_key_list()
            case ['article', 'media-id', 'add']:
                return self.add_article_media_id()
            case ['article', 'media-id', 'remove']:
                return self.remove_article_media_id()
            case ['article', 'update']:
                return self.update_articles()
            case ['article', 'url', 'add']:
                return self.add_article_url()
            case ['article', 'url', 'remove']:
                return self.remove_article_url()
            case ['article', 'wx']:
                offset = web.input().get('offset', 0)
                return self.list_wx_articles(offset=offset)
            case ['autoreply', 'update']:
                return self.update_autoreply()
            case ['config', 'reload']:
                return self.reload_config()
            case ['debug-code']:
                return self.show_debug_code()
            case ['donate', 'price']:
                return self.get_donate_price()
            case ['donate', 'price', 'set']:
                return self.set_donate_price()
            case ['feature', 'update']:
                return self.update_features()
            case ['image', type, 'clear']:
                return self.clear_image_files(type=type)
            case ['init']:
                return self.init_menu()
            case ['invoke']:
                return self.validate_wechat_token()
            case ['media', 'list']:
                type = web.input().get('type', 'image')
                offset = web.input().get('offset', 0)
                return self.list_medias(type=type, offset=offset)
            case ['pay', 'info']:
                return self.get_pay_info()
            case ['pay', 'stats']:
                return self.get_pay_stats()
            case ['poster']:
                return self.make_poster()
            case ['rid', rid]:
                return self.get_rid_info(rid)
            case ['sensitive-word', 'update']:
                return self.update_sensitive_words()
            case ['chat-param']:
                return self.get_chat_param()
            case ['chat-param', 'set']:
                return self.set_chat_param()
            case ['test']:
                url = web.input().get('url', 'https://api.openai.com')
                return self.test_connection(url)
            case ['user', 'dump']:
                return self.dump_user_info()
            case ['user', 'list']:
                return self.get_login_user_list()
            case ['user', openid]:
                return self.get_user_info(openid=openid)
            case ['user', openid, 'credit', credit_type, 'set']:
                return self.set_remaining_feature_credit(openid=openid, credit_type=credit_type)
            case ['user', openid, 'conversation', 'clear']:
                return self.clear_conversation(openid=openid)
            case ['user', openid, 'pending', 'clear']:
                return self.clear_pending(openid=openid)
            case ['user', openid, 'reset']:
                return self.reset_user(openid=openid)
            case ['user', openid, 'signup']:
                return self.signup(openid=openid)
            case ['vip', openid]:
                return self.get_vip_level(openid=openid)
            case ['vip', openid, level, 'add']:
                return self.add_vip(openid=openid, level=level)
            case ['vip', openid, 'remove']:
                return self.remove_vip(openid=openid)
            case ['cl', 'config']:
                return self.clash_get_config()
            case ['cl', 'config', 'set']:
                return self.clash_set_config()
            case ['voice', 'clear']:
                return self.clear_voice_files()
            case ['wx', 'jsapi', 'param']:
                return self.get_wx_jsapi_param()
            case ['wx', 'jsapi', 'user_info']:
                return self.get_wx_user_info()
            case _:
                return self.index()
    
    def PUT(self, api_name: str):
        web.header('Content-Type', 'application/json; charset=utf-8')
        if not api_name: api_name = '/'
        seq = api_name[1:].split('/')
        match seq:
            case ['file']:
                return self.upload_file()
    
    def OPTIONS(self, api_name: str):
        web.header('Content-Type', 'application/json; charset=utf-8')
        if not api_name: api_name = '/'
        seq = api_name[1:].split('/')
        match seq:
            case ['file']:
                self.cross_origin()
                web.ctx.status = '204 OK'
            case ['pay', 'create']:
                self.cross_origin()
                web.ctx.status = '204 OK'
        return
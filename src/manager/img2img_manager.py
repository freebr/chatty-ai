import json
import requests.api as requests
import web
from base64 import b64decode
from logging import getLogger, Logger
from os import path, mkdir
from time import time

from configure import Config
from definition.cls import Singleton
from definition.const import DIR_IMAGES_IMG2IMG
from manager.key_token_manager import KeyTokenManager

URL_API_BASE = 'https://flagopen.baai.ac.cn/flagStudio'
DISPLAY_STYLE_COUNT_WECHAT = 30
cfg = Config()
key_token_mgr = KeyTokenManager()
class Img2ImgManager(metaclass=Singleton):
    api_keys: list
    workdir: str
    users: dict
    style_dict: dict
    logger: Logger
    DEFAULT_PARAMS = {
        'controlnet_task': 'canny-from-image',
        'style': None,
        'prompt': None,
        'negative_prompts': None,
        'step': 100,
        'width': 768,
        'height': 768,
    }
    def __init__(self, **kwargs):
        self.logger = getLogger(self.__class__.__name__)
        self.api_keys = key_token_mgr.api_keys.get('Img2Img')
        self.style_dict = { key: {'used_count': 0} for key in STYLE_LIST }
        self.users = {}
        self.workdir = DIR_IMAGES_IMG2IMG
    
    def register_user(self, name):
        """
        添加用户图片信息
        """
        self.users[name] = {
            'img_path': [],
            'last_upload_image': None,
            'last_export_image': None,
        }
        for key, value in self.DEFAULT_PARAMS.items():
            self.users[name][key] = value
        
    def unregister_user(self, name):
        """
        清除指定用户上传的图片信息
        """
        if name not in self.users: return True
        self.users.pop(name)
        return True
    
    def add_user_image_info(self, name, **kwargs):
        """
        记录指定用户上传的图片信息
        """
        if name not in self.users: self.register_user(name)
        img_path = kwargs.get('img_path')
        if img_path: self.users[name]['img_path'].append(img_path)
        for key in ['controlnet_task', 'negative_prompts', 'prompt', 'style']:
            value = kwargs.get(key) or ''
            if value: self.users[name][key] = value
        return True

    def get_user_image_info(self, name):
        """
        返回指定用户上传的图片信息
        """
        if name not in self.users: return
        return self.users[name]

    def clear_user_images(self, name):
        """
        清除指定用户上传的图片信息
        """
        if name not in self.users: self.register_user(name)
        self.users[name]['img_path'].clear()
        for key in ['controlnet_task', 'negative_prompts', 'prompt', 'style']:
            self.users[name][key] = None
        return True

    def check_img2img_valid(self, name):
        """
        返回指定用户上传的图片信息是否有效
        """
        src_path = self.users[name].get('img_path')
        if not src_path: return False
        style = self.users[name].get('style')
        if not style: return False
        controlnet_task = self.users[name].get('controlnet_task')
        if not controlnet_task: return False
        return True

    def img2img(self, username, params={}):
        """
        将指定的图片上传到 FlagStudio 并进行图生图处理
        """
        if username not in self.users: return
        img_paths = self.users[username].get('img_path')
        if not img_paths: return
        user = self.users[username]
        results = []
        try:
            # 1.获取调用接口的 token
            token = self.get_token()
            for src_path in img_paths:
                # 2.获取上传图片的地址
                url = self.api_url('v1/getUploadLink')
                headers = {
                    'Accept': 'application/json',
                    'token': token,
                }
                res = requests.get(
                    url,
                    headers=headers,
                ).json()
                if 'data' not in res: raise Exception(json.dumps(res, ensure_ascii=False))
                upload_info = { key: res['data'][key] for key in ['filename', 'url', 'headers'] }
                # 3.上传图片
                with open(src_path, 'rb') as f: upload_data = f.read()
                res = requests.put(
                    url=upload_info['url'],
                    headers=upload_info['headers'],
                    data=upload_data,
                )
                # 4.图生图
                param_data = {
                    'filename': upload_info.get('filename'),
                }
                for key, default_value in self.DEFAULT_PARAMS.items():
                    param_data[key] = params.get(key, user.get(key, default_value))
                if not param_data['controlnet_task'].endswith('-from-image'):
                    param_data['controlnet_task'] += '-from-image'
                url = self.api_url('v1/img2img')
                res = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(param_data, ensure_ascii=False).encode('utf-8'),
                ).json()
                if res['code'] != 200: raise Exception(json.dumps(res, ensure_ascii=False))
                img_data = b64decode(res['data'])
                img_name = str(round(time())) + '.jpg'
                dest_path = path.abspath(path.join(self.workdir, img_name))
                if not path.exists(self.workdir): mkdir(self.workdir)
                with open(dest_path, 'wb') as f: f.write(img_data)
                self.logger.info('用户 %s 执行图生图任务成功，目标路径：%s', username, dest_path)
                user['last_upload_image'] = src_path
                user['last_export_image'] = dest_path
                style_item = self.style_dict.get(param_data['style'])
                if style_item: style_item['used_count'] += 1
                results.append((img_name, dest_path))
            return results
        except Exception as e:
            message = '用户 {} 执行图生图任务失败：{}'.format(username, str(e))
            self.logger.error(message)
            raise Exception(message)

    def get_token(self):
        """
        获取调用接口的 token
        """
        url = self.api_url('auth/getToken')
        res = requests.get(url).json()
        if 'data' not in res or 'token' not in res.get('data'):
            message = '获取 Token 失败'
            self.logger.error(message)
            raise Exception(message)
        return res.get('data').get('token')
    
    def api_url(self, name, querystring=''):
        """
        根据指定的 name 返回对应的 API 接口 URL
        """
        if querystring: querystring = '&' + querystring
        return f'{URL_API_BASE}/{name}?apikey={self.api_keys[0]}{querystring}'

    def get_controlnet_task_list(self, type='wechat'):
        """
        获取预处理器列表字符串
        """
        counter = 0
        ret = []
        line = ''
        for name, desc in CONTROLNET_TASK_LIST.items():
            counter += 1
            if type == 'wechat':
                line = desc
            elif type == 'web':
                line = f'<a href=\'#\' data-message=\'@append-prompt:预处理器[{web.urlquote(name)}]\'>{desc}</a>'
            ret.append(line)
        return ret

    def get_style_list(self, type='wechat'):
        """
        获取风格列表字符串
        """
        counter = 0
        ret = []
        line = ''
        for style, info in self.style_dict.items():
            # show_text = '{} {}人次使用'.format(style, info['used_count'])
            counter += 1
            if type == 'wechat':
                line += style
            elif type == 'web':
                line += f'<a href=\'#\' data-message=\'@append-prompt:风格[{web.urlquote(style)}]\'>{style}</a>'
            if counter % 3 == 0:
                ret.append(line)
                line = ''
            else:
                line += ' / '
            if counter == DISPLAY_STYLE_COUNT_WECHAT and type == 'wechat': break
        return ret

    def get_guide(self):
        return cfg.data.autoreplies['Img2ImgGuide']

    def get_guide_examples(self):
        return cfg.data.autoreplies['Img2ImgGuideExample']

    def get_prompt_examples(self):
        return cfg.data.autoreplies['Img2ImgExample']

    def find_style(self, message: str):
        for key in STYLE_LIST:
            if key in message: return key
        return

    def is_style_supported(self, style: str):
        """
        返回是否支持生成指定风格
        """
        return style.strip() in STYLE_LIST

STYLE_LIST = [
    'MJ风格',
    '国画',
    '写实主义',
    '虚幻引擎',
    '黑白插画',
    '暗黑',
    '涂鸦',
    '漫画场景',
    '素描',
    'CG渲染',
    '动漫',
    '剪纸',
    '毕加索',
    '米开朗基罗',
    '新海诚',
    '版绘',
    '水彩画',
    '儿童画',
    '低聚',
    '工业霓虹',
    '电影艺术',
    '史诗大片',
    '特写',
    '油画',
    '卡通画',
    '浮世绘',
    '赛博朋克',
    '吉卜力',
    '哑光',
    '现代中式',
    '相机',
    '霓虹游戏',
    '蒸汽波',
    '宝可梦',
    '火影忍者',
    '圣诞老人',
    '个人特效',
    '通用漫画',
    'Momoko',
    '齐白石',
    '张大千',
    '丰子恺',
    '梵高',
    '塞尚',
    '莫奈',
    '马克·夏加尔',
    '丢勒',
    '高更',
    '爱德华·蒙克',
    '托马斯·科尔',
    '安迪·霍尔',
    '倪传婧',
    '村上隆',
    '黄光剑',
    '吴冠中',
    '林风眠',
    '木内达朗',
    '萨雷尔',
    '杜拉克',
    '比利宾',
    '布拉德利',
    '普罗旺森',
    '莫比乌斯',
    '格里斯利',
    '比普',
    '卡尔·西松',
    '玛丽·布莱尔',
    '埃里克·卡尔',
    '扎哈·哈迪德',
    '包豪斯',
    '英格尔斯',
    'RHADS',
    '阿泰·盖兰',
    '俊西',
    '坎皮恩',
    '德尚鲍尔',
    '库沙特',
    '雷诺阿',
]

CONTROLNET_TASK_LIST = {
    'canny': 'canny：能很好识别出图像内各对象的边缘轮廓（如线稿），适合原画设计师',
    'depth': 'depth：可使出图保持与原图一致的纵深关系',
    'hed': 'hed：更好保留柔和边缘细节，适合重新着色和风格化',
    'mlsd': 'mlsd：适合出建筑设计效果图',
    'normal': 'normal：光影处理效果好，适合CG、游戏美术设计',
    'pose': 'pose：适合人物形象转换',
    'scribble': 'scribble：可由简笔画生成效果图',
    'seg': 'seg：可由一系列色块生成效果图',
}
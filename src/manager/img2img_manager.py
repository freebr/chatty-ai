import json
import requests.api as requests
import web
from base64 import b64decode
from logging import getLogger, Logger
from os import path, mkdir
from time import time

from definition.cls import Singleton
from definition.const import DIR_IMAGES_IMG2IMG
from manager.key_token_manager import KeyTokenManager

URL_API_BASE = 'https://flagopen.baai.ac.cn/flagStudio'
key_token_mgr = KeyTokenManager()
class Img2ImgManager(metaclass=Singleton):
    api_keys: list
    workdir: str
    users: dict
    style_dict: dict
    logger: Logger = None
    DEFAULT_PARAMS = {
        'style': None,
        'prompt': None,
        'negative_prompts': None,
        'step': 100,
        'width': 768,
        'height': 768,
    }
    def __init__(self, **kwargs):
        self.logger = getLogger('IMG2IMGMGR')
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
        for key in ['prompt', 'style']:
            value = kwargs.get(key)
            self.users[name][key] = value
        return True

    def get_user_image_info(self, name):
        """
        返回指定用户上传的图片信息
        """
        if name not in self.users: return
        return self.users[name]

    def clear_user_images(self, name):
        """
        记录指定用户上传的图片地址
        """
        if name not in self.users: self.register_user(name)
        self.users[name]['img_path'].clear()
        return True

    def check_img2img_valid(self, name):
        """
        返回指定用户上传的图片信息是否有效
        """
        src_path = self.users[name].get('img_path')
        if not src_path: return False
        style = self.users[name].get('style')
        if not style: return False
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
                line += f'<a href=\'weixin://bizmsgmenu?msgmenucontent={web.urlquote(style)}&msgmenuid=0\'>{style}</a>'
            elif type == 'web':
                line += f'<a href=\'#\' data-message=\'{web.urlquote(style)}\'>{style}</a>'
            if counter % 3 == 0:
                ret.append(line)
                line = ''
            else:
                line += ' / '
        return ret

    def get_prompt_examples(self):
        ret = [
            '例如：',
            '当您想要升级某些元素（背景、眼睛或衣服）的质感时，可添加以下提示词：'
            'extremely detailed /* 某些元素 */',
            'beautiful detailed /* 某种元素 */',
            '基本吟唱魔法：best quality, ultra-detailed, masterpiece, finely detail, highres, 8k wallpaper',
            '人物吟唱魔法：beautiful detailed eyes, highly detailed skin, extremely delicate and beautiful girls',
            '主体远近：full body shot(全身) / cowboy shot(半身) / close-up shot(接近)',
            '光线指定：cinematic lighting(电影光) / dynamic lighting(动感光)',
            '视角指定：dynamic angle / from above / from below / wide shot / Aerial View',
            '视线指定：looking at viewer / looking at another / looking away / looking back / looking up',
            '服装指定：china dress / sailor dress / school uniform / sailor senshi uniform',
            '身体指定：blush(脸红)/ wet sweat(大汗) / flying sweatdrops(飞汗)',
            '姿势指定：hands on own face / hands on feet / hands on breast / kneeling / hand between legs / hair flip / skirt flip',
            '使提示词更强：用 () 括起元素',
            '使提示词更弱：用 [] 括起元素',
            '元素后加一个数值表示强调倍数，数值越大该元素越强化，如：春天(1.5)/笑脸(1.9)/星空(2.5)',
        ]
        return ret

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
    '低聚',
    '工业霓虹',
    '电影艺术',
    '史诗大片',
    # '特写',
    # '儿童画',
    # '油画',
    # '水彩画',
    # '卡通画',
    # '浮世绘',
    # '赛博朋克',
    # '吉卜力',
    # '哑光',
    # '现代中式',
    # '相机',
    # '霓虹游戏',
    # '蒸汽波',
    # '宝可梦',
    # '火影忍者',
    # '圣诞老人',
    # '个人特效',
    # '通用漫画',
    # 'Momoko',
    # '齐白石',
    # '张大千',
    # '丰子恺',
    # '梵高',
    # '塞尚',
    # '莫奈',
    # '马克·夏加尔',
    # '丢勒',
    # '高更',
    # '爱德华·蒙克',
    # '托马斯·科尔',
    # '安迪·霍尔',
    # '倪传婧',
    # '村上隆',
    # '黄光剑',
    # '吴冠中',
    # '林风眠',
    # '木内达朗',
    # '萨雷尔',
    # '杜拉克',
    # '比利宾',
    # '布拉德利',
    # '普罗旺森',
    # '莫比乌斯',
    # '格里斯利',
    # '比普',
    # '卡尔·西松',
    # '玛丽·布莱尔',
    # '埃里克·卡尔',
    # '扎哈·哈迪德',
    # '包豪斯',
    # '英格尔斯',
    # 'RHADS',
    # '阿泰·盖兰',
    # '俊西',
    # '坎皮恩',
    # '德尚鲍尔',
    # '库沙特',
    # '雷诺阿',
]
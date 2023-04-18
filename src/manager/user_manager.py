from const import DIR_USERS, CREDIT_TYPENAME_DICT
from helper.formatter import now
from logging import Logger
from os import path
import json
import redis
import time
import uuid

KEY_USER_OPENID = 'USERS'
KEY_USER_INFO = 'USER:%s'
EXCLUDED_DUMP_KEYS = ['ws']
class UserManager:
    cache: redis.StrictRedis
    default_credit:dict
    default_credit_vip:dict
    # VIP 等级
    vip_levels:list
    # VIP 价格
    vip_prices:dict
    # VIP 权益描述
    vip_rights:dict
    # VIP 用户 ID
    vip_dict:dict
    # 普通用户称谓
    free_level:str
    # 最高 VIP 用户称谓
    highest_level:str
    vip_file_path = path.join(DIR_USERS, 'vip-list.json')
    logger: Logger = None

    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.cache = kwargs['cache']
        self.users = {}
        self.vip_levels = kwargs['vip_levels']
        self.vip_prices = {}
        self.vip_rights = {}
        for index, level in enumerate(self.vip_levels):
            self.vip_prices[level] = kwargs['vip_prices'][index]
            self.vip_rights[level] = kwargs['vip_rights'][index]
        self.free_level = kwargs['free_level']
        self.highest_level = kwargs['highest_level']
        self.vip_dict = {level: [] for level in self.vip_levels}
        self.default_credit = {}
        self.default_credit_vip = {level: {} for level in self.vip_levels}
        for type in CREDIT_TYPENAME_DICT:
            self.default_credit[type] = kwargs['credit'][self.free_level][type]
            for level in self.vip_levels:
                self.default_credit_vip[level][type] = kwargs['credit'][level][type]
        self.read_vip_list()
        self.load_all_users()

    def register_user(self, openid):
        """
        添加用户对话信息
        """
        openid = openid.strip()
        if openid == '': return
        if openid in self.users:
            self.users[openid]['login_time'] = now()
            return self.users[openid]
        self.users[openid] = {
            'openid': openid,
            'login_time': now(),
            'records': [],
            'conversation_id': None,
            'parent_id': None,
            'pending': False,
            'img2img_mode': False,
            'voice_role': None,
            'total_credit': {},
            'remaining_credit': {},
            'service_state': {},
            'code_list': {},
            'daily_data': self.get_initial_daily_data(),
            'invited_users': [],
            'wx_user_info': {},
            'ws': None,
        }
        for type in CREDIT_TYPENAME_DICT:
            level = self.get_vip_level(openid)
            self.set_total_credit(openid, type, self.default_credit[type] if level == self.free_level else self.default_credit_vip[level][type])
            self.reset_remaining_credit(openid, type)
        self.dump_user(openid)
        return self.users[openid]

    def reset_user(self, openid):
        """
        重置指定用户的全部信息
        """
        user: dict = self.users[openid]
        ws = user.get('ws')
        user.update({
            'login_time': None,
            'conversation_id': None,
            'parent_id': None,
            'pending': False,
            'img2img_mode': False,
            'records': '',
            'service_state': '',
            'code_list': '',
            'daily_data': self.get_initial_daily_data(),
            'invited_users': '',
            'wx_user_info': '',
            'ws': None,
        })
        if ws: ws.close(reason='reset')
        user['ws'] = None
        for type in CREDIT_TYPENAME_DICT:
            level = self.get_vip_level(openid)
            self.set_total_credit(openid, type, self.default_credit[type] if level == self.free_level else self.default_credit_vip[level][type])
            self.reset_remaining_credit(openid, type)
        self.dump_user(openid)
        return True

    def get_initial_daily_data(self):
        """
        返回初始的每日数据字典
        """
        return {
            'day_share_count': 0,
            'signup': False,
        }

    def reset_daily_data(self, openid):
        """
        重置指定用户的每日数据
        """
        user = self.users[openid]
        user['daily_data'] = self.get_initial_daily_data()
        self.dump_user(openid)
        return True

    def reset_all_daily_data(self):
        """
        重置全部用户的每日数据
        """
        for openid in self.users:
            if not self.reset_daily_data(openid): return False
        return True

    def get_last_conversations(self, openid, count=5):
        """
        以 list 形式返回指定用户之前指定次数的对话
        """
        if openid not in self.users: return []
        if count < 1: return []
        ret = []
        for record in self.users[openid]['records'][-count:]:
            ret.append({ 'role': 'user', 'content': record['input'] })
            ret.append({ 'role': 'assistant', 'content': record['output'] })
        return ret

    def record_conversation(self, openid, input, output):
        """
        记录指定用户的对话
        """
        if openid not in self.users: self.register_user(openid)
        self.users[openid]['records'].append({
            'input': input,
            'output': output,
        })
        self.dump_user(openid)

    def clear_conversation(self, openid):
        """
        清空指定或所有对话
        """
        if len(self.users) == 0: return True
        if openid == '*':
            for openid in self.users: self.reset_user(openid)
            self.logger.info('全部用户对话已清空')
        else:
            user = self.users.get(openid)
            if not user: return True
            self.reset_user(openid)
            self.logger.info('用户 %s 的对话已清空', openid)
        return True

    def get_pending(self, openid):
        """
        获取指定用户的等待状态
        """
        if openid not in self.users: return False
        return self.users[openid]['pending']

    def set_pending(self, openid, pending):
        """
        设置指定用户的等待状态
        """
        if openid == '*':
            for user in self.users.values():
                user['pending'] = pending
        else:
            if openid not in self.users: self.register_user(openid)
            self.users[openid]['pending'] = pending
        self.dump_user(openid)

    def get_img2img_mode(self, openid):
        """
        获取指定用户的图生图模式
        """
        if openid not in self.users: return False
        return self.users[openid]['img2img_mode']

    def set_img2img_mode(self, openid, value):
        """
        设置指定用户的图生图模式
        """
        if openid not in self.users: self.register_user(openid)
        self.users[openid]['img2img_mode'] = value
        self.dump_user(openid)

    def get_voice_name(self, openid):
        """
        获取指定用户的语音对话角色名
        """
        if openid not in self.users: return
        return self.users[openid]['voice_role']

    def set_voice_name(self, openid, role):
        """
        设置指定用户的语音对话角色名
        """
        if openid not in self.users: self.register_user(openid)
        self.users[openid]['voice_role'] = role
        self.dump_user(openid)

    def reduce_remaining_credit(self, openid, type):
        """
        使指定用户的指定类型的可用次数减一
        """
        if openid not in self.users: return False
        if type not in CREDIT_TYPENAME_DICT: return False
        if self.users[openid]['remaining_credit'][type] <= 0: return False
        self.users[openid]['remaining_credit'][type] -= 1
        self.dump_user(openid)
        return True

    def get_remaining_credit(self, openid, type):
        """
        获取指定用户的指定类型的剩余可用次数
        """
        if openid not in self.users:
            level = self.get_vip_level(openid)
            if level == self.free_level:
                return self.default_credit[type]
            return self.default_credit_vip[level][type]
        if type not in CREDIT_TYPENAME_DICT: return 0
        return self.users[openid]['remaining_credit'][type]

    def set_remaining_credit(self, openid, type, value=0):
        """
        设置指定用户的指定类型的剩余可用次数
        """
        if openid not in self.users: return False
        if type not in CREDIT_TYPENAME_DICT: return False
        self.users[openid]['remaining_credit'][type] = value
        self.dump_user(openid)
        return True

    def reset_remaining_credit(self, openid, type):
        """
        重置指定用户的指定类型的剩余可用次数为默认次数
        """
        if openid not in self.users: return False
        if type not in CREDIT_TYPENAME_DICT: return False
        level = self.get_vip_level(openid)
        self.users[openid]['remaining_credit'][type] = self.default_credit[type] if level == self.free_level else self.default_credit_vip[level][type]
        self.dump_user(openid)
        return True

    def get_total_credit(self, openid, type):
        """
        获取指定用户的指定类型的总可用次数
        """
        if openid not in self.users:
            level = self.get_vip_level(openid)
            return self.default_credit[type] if level == self.free_level else self.default_credit_vip[level][type]
        if type not in CREDIT_TYPENAME_DICT: return 0
        return self.users[openid]['total_credit'][type]

    def set_total_credit(self, openid, type, value=0):
        """
        设置指定用户的指定类型的总可用次数
        """
        if openid not in self.users: return False
        if type not in CREDIT_TYPENAME_DICT: return False
        self.users[openid]['total_credit'][type] = value
        self.dump_user(openid)
        return True

    def get_wx_user_info(self, openid):
        """
        获取指定用户的微信用户信息
        """
        if openid not in self.users: return
        return self.users[openid]['wx_user_info']

    def set_wx_user_info(self, openid, value):
        """
        设置指定用户的微信用户信息
        """
        if openid not in self.users: self.register_user(openid)
        self.users[openid]['wx_user_info'] = value
        self.dump_user(openid)

    def get_ws(self, openid):
        """
        获取指定用户的 Websocket 实例
        """
        if openid not in self.users: return
        return self.users[openid]['ws']

    def set_ws(self, openid, ws):
        """
        设置指定用户的 Websocket 实例
        """
        if openid not in self.users: return False
        self.users[openid]['ws'] = ws

    def get_day_share_count(self, openid):
        """
        获取指定用户的本日分享次数
        """
        if openid not in self.users: return 0
        return self.users[openid]['daily_data']['day_share_count']

    def set_day_share_count(self, openid, value: int):
        """
        设置指定用户的本日分享次数
        """
        if openid not in self.users: self.register_user(openid)
        self.users[openid]['daily_data']['day_share_count'] = value
        self.dump_user(openid)

    def get_signup(self, openid):
        """
        获取指定用户的本日签到标志
        """
        if openid not in self.users: return False
        return self.users[openid]['daily_data']['signup']

    def set_signup(self, openid, value: bool):
        """
        设置指定用户的本日签到标志
        """
        if openid not in self.users: self.register_user(openid)
        self.users[openid]['daily_data']['signup'] = value
        self.dump_user(openid)

    def is_invited_user(self, openid, invited_open_id):
        """
        判断指定用户是否分享过链接给 invited_open_id 的用户
        """
        if openid not in self.users: return False
        return invited_open_id in self.users[openid]['invited_users']

    def add_invited_user(self, openid, invited_open_id):
        """
        添加指定用户分享链接给 invited_open_id 的用户的记录
        """
        if openid not in self.users: self.register_user(openid)
        self.users[openid]['invited_users'].append(invited_open_id)
        self.dump_user(openid)
        
    def read_vip_list(self):
        if not path.isfile(self.vip_file_path):
            self.logger.error('VIP 用户列表加载失败，找不到文件：%s', self.vip_file_path)
            return False
        with open(self.vip_file_path, mode='r', encoding='utf-8', errors='ignore') as f:
            data = f.read()
        try:
            new_vip_dict = json.loads(data)
            for level in self.vip_levels:
                if level in new_vip_dict: self.vip_dict[level] = new_vip_dict[level]
            self.logger.info('VIP 用户列表加载成功')
            return True
        except Exception as e:
            self.logger.error(e)
            return False

    def save_vip_list(self):
        with open(self.vip_file_path, mode='w', encoding='utf-8', errors='ignore')  as f:
            f.write(json.dumps(self.vip_dict, ensure_ascii=False))

    def get_vip_level(self, openid):
        openid = openid.strip()
        if openid == '': return -1
        for level, list in self.vip_dict.items():
            if openid in list:
                return level
        return self.free_level

    def is_vip(self, openid):
        openid = openid.strip()
        if openid == '': return False
        for level, list in self.vip_dict.items():
            if openid in list:
                return True
        return False

    def add_vip(self, openid, level):
        openid = openid.strip()
        if openid == '': return False
        if level not in self.vip_levels: return False
        self.remove_vip(openid)
        self.vip_dict[level].append(openid)
        for type in CREDIT_TYPENAME_DICT:
            self.set_total_credit(openid, type, self.default_credit[type] if level == self.free_level else self.default_credit_vip[level][type])
            self.reset_remaining_credit(openid, type)
        self.save_vip_list()
        return True

    def remove_vip(self, openid):
        openid = openid.strip()
        if openid == '': return False
        level = self.get_vip_level(openid)
        if level == self.free_level: return False
        self.vip_dict[level].remove(openid)
        self.save_vip_list()
        return True

    def append_code_list(self, openid, data):
        """
        在代码列表增加指定条目并返回 key
        """
        if openid not in self.users: return False
        key = str(uuid.uuid3(uuid.uuid4(), openid))
        self.users[openid]['code_list'][key] = data
        self.dump_user(openid)
        return True, key

    def pop_code_list(self, openid, key):
        """
        从代码列表删除指定条目
        """
        if openid not in self.users: return False
        if key not in self.users[openid]['code_list']: return False
        data = self.users[openid]['code_list'].pop(key)
        self.dump_user(openid)
        return True, data

    def get_code_list_item(self, openid, key):
        """
        返回代码列表的指定条目
        """
        if openid not in self.users: return
        if key not in self.users[openid]['code_list']: return
        return self.users[openid]['code_list'].get(key)

    def get_level_rights_by_amount(self, amount:float):
        """
        获取指定充值金额对应的等级和权益描述
        """
        level_result = None
        rights = None
        for level in self.vip_levels:
            if amount >= self.vip_prices[level]:
                level_result = level
                rights = self.vip_rights[level]
        if not rights: level_result = self.free_level
        return level_result, rights

    def get_login_time(self, openid):
        openid = openid.strip()
        if openid not in self.users: return -1
        return self.users[openid]['login_time']

    def grant_credit(self, openid, credit_type, grant_credit):
        remaining_credit = self.get_remaining_credit(openid, credit_type)
        self.set_remaining_credit(openid, credit_type, remaining_credit + grant_credit)
        return True

    def get_login_user_list(self):
        """
        返回全部已登录用户信息
        """
        infos = {}
        for openid in self.users:
            infos[openid] = {}
            for key in self.users[openid]:
                if key in EXCLUDED_DUMP_KEYS: continue
                infos[openid][key] = self.users[openid][key]
        return infos

    def dump_user(self, openid):
        """
        转储指定用户信息到 Redis
        """
        if openid not in self.users: return False
        user = {}
        for key in self.users[openid]:
            if key in EXCLUDED_DUMP_KEYS: continue
            user[key] = self.users[openid][key]
        self.cache.set(KEY_USER_INFO % openid, json.dumps(user, ensure_ascii=False))
        self.cache.hset(KEY_USER_OPENID, openid, time.time())
        return True

    def dump_all_users(self):
        """
        转储全部用户信息到 Redis
        """
        for openid in self.users:
            ret = self.dump_user(openid)
            if not ret: self.logger.error('转储用户信息时失败：openid=%s', openid)
        self.logger.info('转储全部用户信息成功')
        return True

    def load_user(self, openid):
        """
        从 Redis 加载指定用户信息
        """
        data = self.cache.get(KEY_USER_INFO % openid)
        if data is None: return False
        try:
            user = json.loads(data)
        except Exception as e:
            self.logger.error('加载用户信息时失败：openid=%s, e=%s', openid, str(e))
            return False
        ret = self.users.get(openid, {})
        for key in user:
            ret[key] = user[key]
        self.users[openid] = ret
        return True

    def load_all_users(self):
        """
        从 Redis 加载全部用户信息
        """
        openids = self.cache.hkeys(KEY_USER_OPENID)
        for openid in openids:
            self.load_user(openid)
        self.logger.info('加载用户信息成功，数量：%d', len(openids))
        return True

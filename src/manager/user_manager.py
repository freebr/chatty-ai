import json
import redis
import time
import uuid
from base64 import b64decode
from logging import getLogger, Logger
from numpy import Infinity
from os import path

from configure import Config
from definition.cls import Singleton
from definition.const import DIR_USERS, CREDIT_TYPENAME_DICT, MAX_TOKEN_CONTEXT
from definition.var import is_docker
from helper.formatter import get_feature_command_string, now
from manager.feature_manager import FeatureManager

KEY_USER_OPENID = 'USERS'
KEY_USER_INFO = 'USER:%s'
EXCLUDED_DUMP_KEYS = ['ws']

cfg = Config()
class UserManager(metaclass=Singleton):
    db: redis.StrictRedis
    default_credit: dict
    default_credit_vip: dict
    feature_mgr: FeatureManager
    # VIP 用户等级名称
    vip_levels: list
    # VIP 用户等级价格
    vip_prices: dict
    # VIP 用户等级权益
    vip_rights: dict
    # VIP 用户等级可购买性
    vip_purchasable: dict
    # VIP 用户 ID
    vip_dict: dict
    # 免费用户等级名称
    free_level: str
    # 最高可充值用户等级名称
    top_level: str
    # VIP 用户记录文件
    vip_file_path = path.join(DIR_USERS, 'vip-list.json')
    logger: Logger

    def __init__(self, **kwargs):
        self.logger = getLogger(self.__class__.__name__)
        self.users = {}
        self.vip_levels = kwargs['vip_levels']
        self.vip_prices = {}
        self.vip_purchasable = {}
        self.vip_rights = {}
        for index, level in enumerate(self.vip_levels):
            self.vip_prices[level] = kwargs['vip_prices'][index]
            self.vip_purchasable[level] = kwargs['vip_purchasable'][index]
            self.vip_rights[level] = kwargs['vip_rights'][index]
        self.free_level = kwargs['free_level']
        self.top_level = kwargs['top_level']
        self.vip_dict = {level: [] for level in self.vip_levels}

        self.feature_mgr = FeatureManager()
        self.default_credit = {}
        self.default_credit_vip = {level: {} for level in self.vip_levels}
        for type in CREDIT_TYPENAME_DICT:
            feature = get_feature_command_string(type)
            self.default_credit[type] = self.feature_mgr.get_total_feature_credit(self.free_level, feature)
            for level in self.vip_levels:
                self.default_credit_vip[level][type] = self.feature_mgr.get_total_feature_credit(level, feature)
        self.init_db()
        self.load_vip_list()
        self.load_all_users()

    def init_db(self):
        redis_config = cfg.data.databases['Redis']
        redis_host = redis_config.get('Production' if is_docker() else 'Development').get('Host')
        redis_port = redis_config.get('Production' if is_docker() else 'Development').get('Port')
        redis_password = b64decode(redis_config.get('Password')).decode()
        self.db = redis.StrictRedis(host=redis_host, port=redis_port, db=0, password=redis_password, decode_responses=True)

    def register_user(self, openid):
        """
        添加用户对话信息
        """
        openid = openid.strip()
        if openid == '': return
        if openid in self.users:
            self.users[openid]['login_time'] = now()
            return self.users[openid]
        level = self.get_vip_level(openid)
        self.users[openid] = {
            'code_list': {},
            'conversation_id': None,
            'daily_data': self.get_initial_daily_data(),
            'img2img_mode': False,
            'invited_users': [],
            'level': level,
            'login_time': now(),
            'openid': openid,
            'parent_id': None,
            'pending': False,
            'records': [],
            'voice_role': None,
            'ws': None,
            'wx_user_info': {},
        }
        for type in CREDIT_TYPENAME_DICT:
            self.reset_feature_credit(openid, get_feature_command_string(type))
        self.dump_user(openid)
        return self.users[openid]

    def reset_user(self, openid, **kwargs):
        """
        重置指定用户的全部信息
        """
        try:
            user: dict = self.users[openid]
            updates = {}
            if kwargs.get('reset_conversation', False):
                # 重置对话信息
                updates.update({
                    'code_list': {},
                    'conversation_id': None,
                    'img2img_mode': False,
                    'parent_id': None,
                    'records': [],
                })
            if kwargs.get('reset_credits', False):
                # 重置额度信息
                for type in CREDIT_TYPENAME_DICT:
                    self.reset_feature_credit(openid, get_feature_command_string(type))
            if kwargs.get('reset_daily_data', False):
                # 重置每日数据
                updates['daily_data'] = self.get_initial_daily_data()
            if kwargs.get('reset_invited_users', False):
                # 重置每日数据
                updates['invited_users'] = []
            if kwargs.get('reset_login_time', False):
                # 重置登录时间
                updates['login_time'] = None
            if kwargs.get('reset_pending', False):
                # 重置等待状态
                updates['pending'] = False
            if kwargs.get('reset_ws', False):
                # 重置 Websocket 连接（关闭连接）
                ws = user.get('ws')
                if ws: ws.close(reason='reset')
                updates['ws'] = None
            if kwargs.get('reset_wx_user_info', False):
                # 重置微信用户信息
                updates['wx_user_info'] = {}
            user.update(updates)
            self.dump_user(openid)
            self.logger.info('重置用户 %s 信息成功，开关信息：%s', openid, json.dumps(kwargs))
            return True
        except Exception as e:
            self.logger.error('重置用户 %s 信息失败：%s，开关信息：%s', openid, str(e), json.dumps(kwargs))
            return False

    def get_initial_daily_data(self):
        """
        返回初始的每日数据字典
        """
        return {
            'day_share_count': 0,
            'signup': False,
            'feature_credit': {},
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

    def clip_conversations(self, openid, max_tokens=MAX_TOKEN_CONTEXT):
        """
        返回指定用户之前不超过指定 token 数的对话组成的列表
        """
        if openid not in self.users: return []
        records = self.users[openid]['records']
        ret = []
        tokens = 0
        for i in range(-1, -len(records), -1):
            token = records[i]['__token']
            if tokens + token > MAX_TOKEN_CONTEXT: break
            ret.append(records[i])
            tokens += token
        return ret

    def add_message(self, openid, *messages):
        """
        为指定用户添加消息记录
        """
        if openid not in self.users: self.register_user(openid)
        self.users[openid]['records'] += [message for message in messages if message]
        self.dump_user(openid)

    def clear_conversation(self, openid):
        """
        清空指定或所有对话
        """
        if len(self.users) == 0: return True
        if openid == '*':
            for openid in self.users: self.reset_user(openid, reset_conversation=True, reset_pending=True)
            self.logger.info('全部用户对话已清空')
        else:
            user = self.users.get(openid)
            if not user: return True
            self.reset_user(openid, reset_conversation=True, reset_pending=True)
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

    def set_remaining_feature_credit(self, openid, feature, value=0):
        """
        设置指定用户的指定特性的当日剩余可用次数
        """
        if openid not in self.users: return False
        level = self.get_vip_level(openid)
        total_credit = self.feature_mgr.get_total_feature_credit(level, feature)
        feature_info = {
            'total': total_credit,
            'remaining': value,
        }
        self.users[openid]['daily_data']['feature_credit'][feature] = feature_info
        self.dump_user(openid)
        return True

    def reset_feature_credit(self, openid, feature):
        """
        将指定用户的指定特性的当日可用次数重置为默认值
        """
        if openid not in self.users: return False
        level = self.get_vip_level(openid)
        total_credit = self.feature_mgr.get_total_feature_credit(level, feature)
        feature_info = {
            'total': total_credit,
            'remaining': total_credit,
        }
        self.users[openid]['daily_data']['feature_credit'][feature] = feature_info
        self.dump_user(openid)
        return True

    def get_total_feature_credit(self, openid, feature):
        """
        获取指定用户的指定特性的总可用次数
        """
        level = self.get_vip_level(openid)
        if openid not in self.users:
            total_credit = self.feature_mgr.get_total_feature_credit(level, feature)
        else:
            feature_info = self.users[openid]['daily_data']['feature_credit'].get(feature, {})
            if feature_info:
                total_credit = feature_info['total']
            else:
                total_credit = self.feature_mgr.get_total_feature_credit(level, feature)
        return Infinity if total_credit == Infinity else int(total_credit)

    def get_remaining_feature_credit(self, openid, feature):
        """
        获取指定用户的指定特性的剩余可用次数
        """
        level = self.get_vip_level(openid)
        if openid not in self.users:
            remaining_credit = self.feature_mgr.get_total_feature_credit(level, feature)
        else:
            feature_info = self.users[openid]['daily_data']['feature_credit'].get(feature, {})
            if feature_info:
                remaining_credit = feature_info['remaining']
            else:
                remaining_credit = self.feature_mgr.get_total_feature_credit(level, feature)
        return Infinity if remaining_credit == Infinity else int(remaining_credit)

    def reduce_feature_credit(self, openid, feature):
        """
        使指定用户的指定特性的当日可用次数减一
        """
        if openid not in self.users: return False
        feature_info = self.users[openid]['daily_data']['feature_credit'].get(feature, {})
        if not feature_info:
            level = self.get_vip_level(openid)
            total_credit = self.feature_mgr.get_total_feature_credit(level, feature)
            feature_info = {
                'total': total_credit,
                'remaining': total_credit,
            }
        if feature_info['remaining'] <= 0: return False
        feature_info['remaining'] -= 1
        self.users[openid]['daily_data']['feature_credit'][feature] = feature_info
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
        return self.users[openid].get('ws')

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
        
    def load_vip_list(self):
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
        if openid == '': return self.free_level
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
            self.reset_feature_credit(openid, get_feature_command_string(type))
        self.save_vip_list()
        user = self.users.get(openid)
        if user: user['level'] = level
        return True

    def remove_vip(self, openid):
        openid = openid.strip()
        if openid == '': return False
        level = self.get_vip_level(openid)
        if level == self.free_level: return False
        self.vip_dict[level].remove(openid)
        self.save_vip_list()
        user = self.users.get(openid)
        if user: user['level'] = self.free_level
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

    def get_level_rights_by_amount(self, amount: float):
        """
        获取指定充值金额对应的等级和权益描述
        """
        level_result = None
        rights = None
        last_price = 0
        for level in self.vip_levels:
            if not self.vip_purchasable.get(level): continue
            if amount >= self.vip_prices[level] and last_price < self.vip_prices[level]:
                level_result = level
                last_price = self.vip_prices[level]
                rights = self.vip_rights[level]
        return level_result, rights

    def get_login_time(self, openid):
        openid = openid.strip()
        if openid not in self.users: return -1
        return self.users[openid]['login_time']

    def grant_credit(self, openid, credit_type, grant_credit):
        remaining_credit = self.get_remaining_feature_credit(openid, get_feature_command_string(credit_type))
        self.set_remaining_feature_credit(openid, get_feature_command_string(credit_type), remaining_credit + grant_credit)
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
        pipe = self.db.pipeline()
        pipe.set(KEY_USER_INFO % openid, json.dumps(user, ensure_ascii=False))
        pipe.hset(KEY_USER_OPENID, openid, time.time())
        pipe.execute()
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
        data = self.db.get(KEY_USER_INFO % openid)
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
        openids = self.db.hkeys(KEY_USER_OPENID)
        for openid in openids:
            self.load_user(openid)
        self.logger.info('加载用户信息成功，数量：%d', len(openids))
        return True

    def reload_features(self):
        """
        重新加载特性配置
        """
        return self.feature_mgr.load()
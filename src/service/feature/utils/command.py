from logging import getLogger, Logger

from manager.user_manager import UserManager
from .search_google import google_search

user_mgr = UserManager()
logger: Logger = getLogger('COMMANDEXECUTOR')

def execute_command(metadata: dict, user: dict, services: dict):
    """
    执行输入的命令
    """
    command = metadata['name']
    args = metadata['args']
    logger.info('接收命令：%s %s', command, args)
    if user_mgr.get_remaining_feature_credit(user['openid'], 'Commands.' + command) <= 0:
        # 可用额度不足
        return command, 'no-credit'
    
    service_name = ''
    result = ''
    match command:
        case '搜索':
            result = google_search(args["input"])
        case '浏览网站':
            service_name = 'BrowseService'
            args['get_links'] = True
        case '总结网页':
            service_name = 'BrowseService'
            args['get_links'] = False
        case '查询汇率':
            service_name = 'ExchangeService'
        case '查询快递':
            service_name = 'ExpressService'
        case '查询IP':
            service_name = 'IpService'
        case '查询笑话':
            service_name = 'JokeService'
        case '查询电影':
            service_name = 'MovieService'
        case '查询电话':
            service_name = 'PhoneService'
        case '查询天气':
            service_name = 'WeatherService'
        case '数学问题' | '数学图像':
            service_name = 'WolframService'
        case '非数学绘画':
            service_name = 'ImageService'
    if service_name:
        service = services.get(service_name)
        if not service:
            logger.info('服务未注册：%s', service_name)
            return command, None
        result = service.invoke(args)
    logger.info('执行命令：%s %s, 结果：%s', command, args, result)
    user_mgr.reduce_feature_credit(user['openid'], 'Commands.' + command)
    return command, result
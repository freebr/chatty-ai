from logging import getLogger, Logger

from .search_google import google_search
from helper.formatter import get_feature_command_string
from manager.user_manager import UserManager

user_mgr = UserManager()
logger: Logger = getLogger('COMMANDEXECUTOR')

def execute_command(metadata: dict, user: dict, services: dict):
    """
    执行输入的命令
    """
    command = metadata.get('name')
    args = metadata.get('args')
    logger.info('接收命令：%s %s', command, args)
    feature = get_feature_command_string(command)
    if user_mgr.get_remaining_feature_credit(user['openid'], feature) <= 0:
        # 可用额度不足
        return command, 'no-credit'
    
    service_name = ''
    result = ''
    match command:
        case '搜索':
            service_name = 'SearchService'
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
        case _:
            return command, 'not-supported'
    if service_name == 'SearchService':
        result = google_search(args["input"])
    else:
        service = services.get(service_name)
        if not service:
            logger.info('服务未注册：%s', service_name)
            return command, None
        result = service.invoke(args)
    logger.info('执行命令：%s %s, 结果：%s', command, args, result)
    user_mgr.reduce_feature_credit(user['openid'], feature)
    return command, result
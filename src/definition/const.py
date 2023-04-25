from os import environ, path

if not environ.get('DEBUG'): environ['DEBUG'] = '0'
environ['ALL_PROXY'] = 'http://127.0.0.1:8888' if environ['DEBUG'] == '1' else '' #'socks5h://127.0.0.1:7891'
environ['TZ'] = 'Asia/Shanghai'
environ['PORT_HTTP'] = '7000'
environ['URL_SITE_BASE'] = 'https://freebr.cn/chatty-ai'

ALLOWED_FILES = ['.htm', '.html', '.css', '.js', '.jpg', '.png', '.gif', '.txt', '.webp', '.wav', '.mp3', '.mp4', '.ico', '.ttf', '.map']
DEBUG_MODE = environ['DEBUG'] == '1'
# 记忆过期时间 2h
EXPIRE_TIME_MEMORY = 7200
# TTS 引擎（azure-tts/xf-tts）
TTS_ENGINE = 'azure-tts'
DIR_CERT_WS = 'cert/ws'
DIR_CERT_WXPAY = 'cert/wxpay'
DIR_CLASH = '/clash'
DIR_CONFIG = 'config'
DIR_DATA = 'data'
DIR_IMAGES_AVATAR = path.join(DIR_DATA, 'images/avatar')
DIR_IMAGES_DALLE = path.join(DIR_DATA, 'images/dalle')
DIR_IMAGES_IMG2IMG = path.join(DIR_DATA, 'images/img2img')
DIR_IMAGES_MARKDOWN = path.join(DIR_DATA, 'images/markdown')
DIR_IMAGES_POSTER = path.join(DIR_DATA, 'images/poster')
DIR_IMAGES_QRCODE = path.join(DIR_DATA, 'images/qrcode')
DIR_IMAGES_TEMPLATE = path.join(DIR_DATA, 'images/template')
DIR_IMAGES_UPLOAD = path.join(DIR_DATA, 'images/upload')
DIR_LOGS = 'logs'
DIR_STATIC = 'static'
DIR_TTS = path.join(DIR_DATA, 'tts')
DIR_USERS = path.join(DIR_DATA, 'users')
URL_CLASH_SERVER = 'http://127.0.0.1:9090'
URL_PUSH_ARTICLE_COVER_IMAGE = 'https://mmbiz.qpic.cn/mmbiz_png/kGCQTgD98bSWG0kV2r00U7twvqLibQS0yO8sATTvnjtoj8u3VwsXo0yJIjeebYJPJhQm8jKsXBXYSfdKZK4EOIQ/0'
URL_PUSH_LINK_COVER_IMAGE = 'https://mmbiz.qpic.cn/mmbiz_png/kGCQTgD98bRDoEH3CxabelcicdxDfkUdCL9eDzBxNQaZUUjZFPyMDjjenA5ESwlbI5IIJia7g8Z4BG3qTUlEW67Q/0?wx_fmt=png'
URL_SITE_BASE = environ['URL_SITE_BASE']
URL_WEIXIN_BASE = 'https://api.weixin.qq.com/cgi-bin'
BASE_ARTICLE_FILES = {
    'usage': path.abspath(path.join(DIR_CONFIG, 'usage-article-id.yml')),
    'upgrade': path.abspath(path.join(DIR_CONFIG, 'upgrade-article-id.yml')),
}
RESPONSE_EXCEED_TOKEN_LIMIT = '【系统提示】您的消息长度超出 token 限制（%d/%d），请适当删减后再提问！🤗'
RESPONSE_ERROR_RAISED = '【系统提示】当前线路过于火爆，请稍后重试...'
# 每日可赠送额度分享次数上限
MAX_DAY_SHARE_COUNT = 5
# 图生图一次最大上传图片数
MAX_UPLOAD_IMAGES = 1
# 文本生成上下文提示（含输入）的最大token数
MAX_TOKEN_CONTEXT = 3796
MAX_TOKEN_CONTEXT_WITHOUT_HISTORY = int(MAX_TOKEN_CONTEXT * .8)
# 文本生成单个输出最大token数
MAX_TOKEN_OUTPUT = 4096
# 对话使用的模型名称
MODEL_CHAT = 'gpt-3.5-turbo-0301'
# 内容审查使用的模型名称
MODEL_MODERATION = 'text-moderation-latest'
# 文本生成使用的模型名称
MODEL_TEXT_COMPLETION = 'text-davinci-003'
# 生成嵌入向量使用的模型名称
MODEL_EMBEDDING = 'text-embedding-ada-002'
# 分享赠送额度系数
SHARE_GRANT_CREDIT_SCALE = 0.9
# 签到赠送额度系数
SIGNUP_GRANT_CREDIT_SCALE = 0.5

COUNT_RECENT_MESSAGES_TO_TAKE_IN = 9
COUNT_RELEVANT_MEMORY_TO_TAKE_IN = 10

CREDIT_TYPENAME_DICT = {
    'completion': '对话',
    'image': '图片生成',
}
URL_IMG2IMG_EXPORT = 'https://freebr.cn/oxf/img2img/'
URL_POSTER_EXPORT = 'https://freebr.cn/oxf/poster/'
SYSTEM_PROMPT_IMG2IMG = """\
从input提取信息并按 JSON 格式返回：\
{"style":"keywords about the style of image",\
"prompt":"keywords that weight is positive(weight) (default weight is 1, separated by space)",\
"negative_prompts":"keywords that weight is negative(weight) (default weight is 1, separated by space)"}\
不要加任何注释。input:"""

RESPONSE_NO_DEBUG_CODE = '啊哦~代码长翅膀飞走了~'
MESSAGE_UPGRADE_FREE_LEVEL = '感谢您的赞赏，我们会继续为您提供更好的服务！'
MESSAGE_UPGRADE_VIP_LEVEL = '/爱心 恭喜您已成为我们的【%s用户】！\n%s！\n感谢您的支持，我们会继续为您提供更好的服务！'
MESSAGE_UPGRADE_FAILED = '对不起，系统出了点小问题，请联系管理员微信 freebr-cn 协助升级！'

from os import environ, path

if not environ.get('DEBUG'): environ['DEBUG'] = '0'
environ['ALL_PROXY'] = 'http://127.0.0.1:8888' if environ['DEBUG'] == '1' else '' #'socks5h://127.0.0.1:7891'
environ['TZ'] = 'Asia/Shanghai'
environ['PORT_HTTP'] = '7000'
environ['URL_SITE'] = 'https://freebr.cn'
environ['URL_API'] = path.join(environ['URL_SITE'], 'chatty-ai')
environ['URL_H5'] = path.join(environ['URL_SITE'], 'oxf')

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
URL_API = environ['URL_API']
URL_H5 = environ['URL_H5']
URL_DEFAULT_USER = path.join(URL_H5, 'template', 'default-user.png')
URL_IMG2IMG_EXPORT = path.join(URL_H5, 'img2img')
URL_POSTER_EXPORT = path.join(URL_H5, 'poster')
URL_WEIXIN_BASE = 'https://api.weixin.qq.com/cgi-bin'
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
SIGNUP_GRANT_CREDIT_SCALE = 0.5
# 签到赠送额度系数

COUNT_RECENT_MESSAGES_TO_TAKE_IN = 9
COUNT_RELEVANT_MEMORY_TO_TAKE_IN = 10

COMMAND_COMPLETION = '文本生成'
COMMAND_IMAGE = '非数学绘画'
CREDIT_TYPENAME_DICT = {
    COMMAND_COMPLETION: '对话',
    COMMAND_IMAGE: '图片生成',
}
SYSTEM_PROMPT_IMG2IMG = """\
Output the following JSON according to the content of <desc>:\
{"style":"style keyword occurred in <desc>(in Chinese, value is "不变" if not occurred)",\
"mode":"mode occurred in <desc>(value is "不变" if not occurred)",\
"prompt":"positive keywords occurred in <desc>(value is "不变" if not occurred, separated by comma)",\
"negative_prompts":"negative keywords occurred in <desc>(value is "不变" if not occurred, separated by comma)"}\
不要加任何注释。<desc>"""
REGEXP_MARKDOWN_IMAGE = r'!\[[^\]]*\]\(([^\)]+)\)'
REGEXP_TEXT_IMAGE_CREATED = r'我(已经)?为您(画|生成|绘制|绘画)了一(幅|张)图(像|片)'
REGEXP_TEXT_SORRY = r'抱歉|对不起|sorry'
# 发出耐心等待提示的等待时间 10s
WAIT_TIMEOUT = 10
# Chatty AI
![版本 0.1.0](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/language-python-blue)
![MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![last commit](https://img.shields.io/github/last-commit/freebr/chatty-ai)

> 中文名：查小特（基于 Python 的 GPT 微信公众号/网页服务器）
>
> 作者：[freebr](https://github.com/freebr)

# 最终效果展示
- 1.公众号“广州欧讯服科技有限责任公司”
- 2.微信打开 [https://freebr.cn/oxf/chat/](https://freebr.cn/oxf/chat/)

# 建议运行环境
![Alibaba Cloud Linux 3.2104 LTS 64位](https://img.shields.io/badge/Alibaba%20Cloud%20Linux-^3.2104%20LTS%2064bit-green.svg)
![Docker](https://img.shields.io/badge/Docker-^23.0.0-green.svg)
![Python](https://img.shields.io/badge/Python-^3.10.7-green.svg)

# 部署前准备
- 在微信公众号管理后台获取 `APPID`, `APPSECRET`, `APPTOKEN`, `ENCODING_AES_KEY` 信息，填入 `config/api-keys.yml.tmpl` 中的对应字段
- 在微信支付管理后台获取 `APIV3_KEY`, `APPID`, `CERT_SERIAL_NO`, `MCHID` 信息，填入 `config/wx-pay.yml.tmpl` 中的对应字段
- 在 OpenAI 账号后台获取 API key，填入 `config/api-keys.yml.tmpl` 的 `Services.OpenAI`
- 打开 `config` 中其他 `*.yml.tmpl` 文件，按照提示修改内容
- 把 `config` 中所有 `*.yml.tmpl` 文件名的 `.tmpl` 删除

# 部署方式
## 本地运行
> `[chatty_ai]# python src/main.py`

## 服务器部署
> `[chatty_ai]# . bin/start.sh`

## Docker 部署
- 4核8G环境完整构建时间约 `70s`
> `[chatty_ai]# docker compose up -d`
>
> ![docker](https://user-images.githubusercontent.com/12162720/232187178-52ac637a-30aa-43d3-8340-f49fe3d97550.png)

# 日志输出
> <details>
>   <summary>正常情况时的日志输出：</summary>
>
> 2023-03-17 08:37:44,709 - BOT - INFO: 敏感词词典加载成功，数量：17270
>
> 2023-03-17 08:37:44,711 - BOT - INFO: 加载服务[PhoneService]成功
>
> 2023-03-17 08:37:44,711 - BOT - INFO: 加载服务[WeatherService]成功
>
> 2023-03-17 08:37:44,711 - BOT - INFO: 加载服务[ExpressService]成功
>
> 2023-03-17 08:37:44,711 - BOT - INFO: 加载服务[IpService]成功
>
> 2023-03-17 08:37:44,711 - BOT - INFO: 加载服务成功，数量：4
>
> 2023-03-17 08:37:44,757 - USERMGR - INFO: VIP 用户列表加载成功
>
> 2023-03-17 08:37:44,757 - AUTOREPLYMGR - INFO: 自动回复消息模板加载成功
>
> 2023-03-17 08:37:44,758 - ARTICLEMGR - INFO: 文章 ID 列表加载成功，数量：2
>
> 2023-03-17 08:37:44,758 - GROUPCHATMGR - INFO: 群聊 ID 列表加载成功，数量：2
>
> 2023-03-17 08:37:44,758 - GROUPCHATMGR - INFO: 加载语音角色信息成功，TTS类型：ms-tts，数量：38，推荐角色数量：5
>
> 2023-03-17 08:37:44,759 - CONTROLLER - INFO: 用户 oKXSw6j9Mkw7sRgRSBO3jeRRjZ4Q 发送消息，长度：12
>
> 2023-03-17 08:37:44,764 - BOT - INFO: 消息数量：2
>
> 2023-03-17 08:37:44,764 - openai - DEBUG: message='Request to OpenAI API' method=post path=https://api.openai.com/v1/chat/completions
> </details>

# 使用建议
- 用 `supervisord` 来监测运行状况，将以上命令写入 `supervisord.conf` 或相关配置文件中，实现开机或意外中止时自动运行
- 用 `tail logs/server.log -f` 监测服务运行日志

# 目录结构
> <details>
>   <summary>打开查看</summary>
>
> bin: 命令存放目录
>
>> tts: TTS 服务
>>
>>> xf-tts: 讯飞 TTS 服务（命令位于`bin`子目录）
>>
>> start.sh: 不用容器时，本服务的部署命令
>
> cert: 证书存放目录
>
>> wxpay: 微信支付相关证书
>>
>>> client: 微信支付 SSL 证书
>>>
>>> key: 微信支付商户证书和私钥
>
> config: 配置文件存放目录（部署前需将 `.yml.tmpl` 改成 `.yml` 并修改配置）
>
>> access-tokens.yml: access token 列表
>>
>> api-keys.yml: API 密钥列表
>>
>> article-urls.yml: 文章地址列表
>>
>> autoreply.yml: 自动回复内容列表
>>
>> usage-article-id.yml: 用法介绍文章 ID
>>
>> upgrade-article-id.yml: 升级额度文章 ID
>>
>> wx-pay.yml: 微信支付商户信息
>
> data: 运行时数据存放目录
>
>> images: 图片文件存放目录（所有图片均可通过 API: `image/<type>/clear` 删除）
>>
>>> avatar: 用户头像存放目录（结合网页版使用）
>>>
>>> dalle: 文生图输出图片存放目录
>>>
>>> img2img: 图生图输出图片存放目录
>>>
>>> markdown: 消息 Markdown 代码内提取图片存放目录
>>>
>>> poster: 分享海报图片存放目录
>>>
>>> qrcode: 分享/Native支付二维码图片存放目录
>>>
>>> upload: 用户上传图片存放目录
>>>
>> sensitive-words: 敏感词典存放目录（自行上传 `*.txt` 格式文件，每行一个词语）
>>
>> tts: 合成语音输出文件存放目录
>>
>>> azure-tts: Azure TTS 合成语音输出文件存放目录
>>>
>>> xf-tts: 讯飞 TTS 合成语音输出文件存放目录
>>
>> users: 用户账号信息存放目录
>>
>>> vip-list.json: VIP 用户 openid 列表
>>>
>>> pay-info.yml: 支付信息列表
>>
>> docker-files: Docker 镜像构建所需文件
>>
>>> clash-config: Clash 配置文件，应包含 `Country.mmdb`, `config.yaml`
>>
>> logs: 日志目录
>>
>>> <日期>.log: 启动于<日期>的日志文件
>>
> src: 模块所在目录
>> controller: 控制器模块
>>
>>> api_controller.py: API 控制器，实现微信消息收发和事件处理、与 `bot` 实例的消息通信、RESTful API 接口等
>>>
>>> static_controller.py: 静态页面控制器，响应静态页面请求，如环境已部署 `nginx`, `apache` 等 HTTP 服务器则不必使用
>>>
>>> websocket_controller.py: Websocket 服务控制器，实现基于 WSS 服务器的消息收发、与 `bot` 实例的消息通信，用于面向支持流式输出的客户端（如 Web 端、小程序、APP）提供服务
>>
>> crypt.py: 微信消息加解密 SDK，[详见官方文档](https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Message_encryption_and_decryption_instructions.html)
>>
>> handler.py: 处理程序模块
>>
>>> message_handler.py: 消息内容处理程序，目前用于实现对消息的分段输出、敏感词过滤
>>>
>>> code_snippet_handler.py: 代码片段处理程序，实现将消息中代码片段链接到在线调试工具
>>>
>>> wave_manager.py: 波形文件处理程序，实现对 `*.wav` 波形文件到 `*.amr` 文件的转换
>>
>> helper: 辅助模块
>>
>>> formatter.py: 格式化模块，包含各种对字符串进行编解码和封装的常用函数
>>>
>>> wx_menu.py: 微信公众号菜单内容定义模块
>>>
>> manager: 组件模块
>>
>>> article_manager.py: 公众号文章组件模块，实现公众号文章地址的存取查询（推广告用）
>>>
>>> autoreply_manager.py: 自动回复组件模块，实现公众号各种情况下的自动回复内容的存取查询
>>>
>>> group_chat_manager.py: 群聊信息组件模块，实现群聊二维码链接的存取查询
>>>
>>> img2img_manager.py: 以图生图组件模块，实现以图生图功能
>>>
>>> key_token_manager.py: 密钥令牌组件模块，实现微信公众号及第三方服务的密钥和令牌的存取查询
>>>
>>> payment_manager.py: 支付组件模块，实现微信支付功能调用、回调事件中转、支付信息列表的存取查询
>>>
>>> poster_manager.py: 分享海报组件模块，实现分享海报的生成
>>>
>>> qrcode_manager.py: 二维码组件模块，实现二维码的生成
>>>
>>> user_manager.py: 用户信息组件模块，实现用户和账号信息的存取
>>>
>>> voices_manager.py: 合成语音组件模块，实现合成语音接口的调用
>>>
>>> wx_access_token_manager.py: 微信 access token 组件模块，实现微信公众号 access token 的查询和定时更新
>>>
>>> wxjsapi_manager.py: 微信 JSAPI 组件模块，通过调用微信 JSAPI 实现 H5 页面授权的功能，详见[官方文档](https://developers.weixin.qq.com/doc/offiaccount/OA_Web_Apps/JS-SDK.html)
>>
>> monitor: 监视模块
>>
>>> user_monitor.py: 用户信息监视模块，实现每日统计信息刷新
>>
>> service：服务模块
>>
>>> bot_service.py: 实现 OpenAI LLM 接口调用，其他服务依赖此服务
>>>
>>> exchange_service.py: 实现实时汇率查询
>>>
>>> express_service.py: 实现快递物流进度查询
>>>
>>> ip_service.py: 实现 IP 归属地查询
>>>
>>> joke_service.py: 实现笑话查询
>>>
>>> movie_service.py: 实现上映电影信息查询
>>>
>>> phone_service.py: 实现手机号码归属地查询
>>>
>>> weather_service.py: 实现实时和预报天气查询
>>>
>>> wolfram_service.py: 实现 Wolfram|Alpha 知识引擎信息查询
>>
>> const.py: 全局常量和环境变量定义模块
>>
>> var.py: 全局变量定义模块
>
> static: 静态页面存放目录
>
> supervisor: supervisord 服务的配置存放目录
>
> docker-compose.yml: Docker Compose 配置文件
>
> Dockerfile: Docker 镜像配置文件
> </details>

# 服务模块
- 服务模块类似 ChatGPT Plugin 的工作方式，都是通过系统提示的方式向 ChatGPT 提供原来的 LLM 不掌握的信息，不同在于调用服务的决定方是每一个服务而非 ChatGPT 本身。
- 每个服务都提供 3 个方法：`test`, `invoke`, `__real_query`，作用如下：
    - `test`: 测试消息是否需要调用本服务，每次处理消息均由 `BotService` 调用
    - `invoke`: 调用服务得到可用于生成系统提示的结果，当服务命中时由 `BotService` 调用
    - `__real_query`: 服务的核心程序，应以结构化的格式（如 `list`, `dict`）返回结果，由 `invoke` 方法调用

# 常见问题
- FAQs：[https://github.com/freebr/chatty-ai/wiki/FAQs](https://github.com/freebr/chatty-ai/wiki/FAQs)

# 待完成工作
- 加入实时新闻查询组件模块
- 重构敏感词汇过滤模块，提高过滤速度
- 支持其他语种/方言的语音消息识别
- 引入 VisualGPT 模型实现图片信息提取
- ...

# 联系
- 欢迎提交 [PR](https://github.com/freebr/chatty-ai/pulls)、[提出新功能建议或报告 BUG](https://github.com/freebr/chatty-ai/issues)，以及Star支持一下。程序运行遇到问题优先查看常见问题列表，其次前往 Issues 中搜索。如果你想了解更多项目细节，并与开发者们交流更多关于AI技术的实践，欢迎加入星球：
![70fdb693175faecad3dcf5a94725869](https://user-images.githubusercontent.com/12162720/232187304-d5c9ee02-b283-4fd0-9a5b-2e937a16370c.jpg)

# 赞赏
> 独立开发不易，觉得项目有用帮到你的话，就请作者喝杯可乐🥤叭🤗
> 
> ![149fa20519de2924120917d730b402a](https://user-images.githubusercontent.com/12162720/232190191-fbb991ff-0795-4b6e-a7ad-b93ae4222410.jpg)
> 
> ![83f7f783283b3df5cf7753776d73487](https://user-images.githubusercontent.com/12162720/232190198-5c05fd1d-3e88-4ffe-bad8-2f4c2e6db935.jpg)


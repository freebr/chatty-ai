from logging import Logger
import json
import re
import requests.api as requests

class ExchangeService:
    api_key = {}
    semantic_parse: any
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.api_key = kwargs['api_key']
        self.semantic_parse = kwargs['semantic_parse']

    def __real_query(self, from_currency, to_currency, amount):
        """
        查询汇率信息
        """
        try:
            if len(self.api_key) == 0: raise Exception('没有可用的 API key')
            api_key = self.api_key[0]
            url = f'https://api.jisuapi.com/exchange/convert?appkey={api_key}'
            form_data = {
                'from': from_currency['currency'],
                'to': to_currency['currency'],
                'amount': amount,
            }
            res = requests.post(url, data=form_data).json()
            data = res['result']
            if not data:
                self.logger.warn('汇率信息查询结果为空')
                return ''
            camount = data['camount']
            result = f'{amount}{from_currency["currency"]}={camount}{to_currency["currency"]}({data["updatetime"]})'
            self.logger.info(result)
            return result
        except Exception as e:
            self.logger.error('查询汇率信息失败：%s', e)
            return ''

    def test(self, message:str):
        """
        从 message 中尝试提取汇率查询信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
        for entry in currency_dict:
            match = re.search(f"\\b{entry['currency']}\\b", message, re.I)
            match = re.search(entry['name'], message, re.I) if not match else match
            if not match: continue
            return True, (message,)
        return False, None

    def invoke(self, data, **kwargs):
        """
        调用服务并返回信息，否则返回 None
        """
        # 获取模型的语义理解结果
        message = data[0]
        if not re.search(r'\d', message): message += '(num=1)'
        system_prompt = '不要回答用户问题，只从问题提取信息并按 JSON 格式返回：[{"from":"转换前","to":"转换后","num":"金额（默认为1）"}...] 数组元素等于问题个数 不要加任何注释'
        reply = self.semantic_parse(system_prompt=system_prompt, content=message)
        self.logger.info(reply)
        # 提取 JSON
        match = re.search(r'\[(.*)\]', reply, re.S)
        # 未提取到 JSON 结构，视为非汇率转换问题
        if not match: return
        json_array = match[0]
        questions = json.loads(json_array)
        results = []
        def find_currency(keyword):
            for entry in currency_dict:
                if re.match(entry['currency'], keyword, re.I) or re.match(entry['name'], keyword, re.I): return entry
            return
        for question in questions:
            from_currency = find_currency(question['from'])
            to_currency = find_currency(question['to'])
            # 未匹配到货币，视为非汇率转换问题
            if not from_currency or not to_currency: continue
            amount = 0.
            try:
                amount = float(question['num'])
            except ValueError:
                amount = float(re.match(r'\d+', message))
                # 未匹配到数值，视为非汇率转换问题
                if not amount: continue
                amount = amount[0]
            results.append(self.__real_query(from_currency, to_currency, amount))
        return 'System enquired exchange rate info:' + ';'.join(results)

currency_dict = [
    {'currency': 'AED','name': '阿联酋迪拉姆'},
    {'currency': 'AFN','name': '阿富汗尼'},
    {'currency': 'ALL','name': '阿尔巴尼亚勒克'},
    {'currency': 'AMD','name': '亚美尼亚德拉姆'},
    {'currency': 'ANG','name': '荷兰盾'},
    {'currency': 'AOA','name': '安哥拉宽扎'},
    {'currency': 'ARS','name': '阿根廷比索'},
    {'currency': 'AUD','name': '澳大利亚元|澳元|澳币'},
    {'currency': 'AWG','name': '阿鲁巴盾弗罗林'},
    {'currency': 'AZN','name': '阿塞拜疆新马纳特'},
    {'currency': 'BAM','name': '波斯尼亚马尔卡'},
    {'currency': 'BBD','name': '巴巴多斯元'},
    {'currency': 'BDT','name': '孟加拉塔卡'},
    {'currency': 'BGN','name': '保加利亚列弗'},
    {'currency': 'BHD','name': '巴林第纳尔'},
    {'currency': 'BIF','name': '布隆迪法郎'},
    {'currency': 'BMD','name': '百慕大元'},
    {'currency': 'BND','name': '文莱元'},
    {'currency': 'BOB','name': '玻利维亚诺'},
    {'currency': 'BRL','name': '巴西雷亚尔'},
    {'currency': 'BSD','name': '巴哈马元'},
    {'currency': 'BTN','name': '不丹努扎姆'},
    {'currency': 'BWP','name': '博茨瓦纳普拉'},
    {'currency': 'BYN','name': '白俄罗斯卢布（新）'},
    {'currency': 'BYR','name': '白俄罗斯卢布'},
    {'currency': 'BZD','name': '伯利兹美元'},
    {'currency': 'CAD','name': '加拿大元|加元'},
    {'currency': 'CDF','name': '刚果法郎'},
    {'currency': 'CHF','name': '瑞士法郎'},
    {'currency': 'CLP','name': '智利比索'},
    {'currency': 'CNY','name': '人民币|元钱|块钱|RMB'},
    {'currency': 'COP','name': '哥伦比亚比索'},
    {'currency': 'CRC','name': '哥斯达黎加科朗'},
    {'currency': 'CUC','name': '古巴可兑换比索'},
    {'currency': 'CUP','name': '古巴比索'},
    {'currency': 'CVE','name': '佛得角埃斯库多'},
    {'currency': 'CZK','name': '捷克克朗'},
    {'currency': 'DJF','name': '吉布提法郎'},
    {'currency': 'DKK','name': '丹麦克朗'},
    {'currency': 'DOP','name': '多明尼加比索'},
    {'currency': 'DZD','name': '阿尔及利亚第纳尔'},
    {'currency': 'EGP','name': '埃及镑'},
    {'currency': 'ERN','name': '厄立特里亚纳克法'},
    {'currency': 'ETB','name': '埃塞俄比亚比尔'},
    {'currency': 'EUR','name': '欧元'},
    {'currency': 'FJD','name': '斐济元'},
    {'currency': 'FKP','name': '福克兰镑'},
    {'currency': 'GBP','name': '英镑'},
    {'currency': 'GEL','name': '格鲁吉亚拉里'},
    {'currency': 'GHS','name': '加纳塞地'},
    {'currency': 'GIP','name': '直布罗陀镑'},
    {'currency': 'GMD','name': '冈比亚达拉西'},
    {'currency': 'GNF','name': '几内亚法郎'},
    {'currency': 'GTQ','name': '危地马拉格查尔'},
    {'currency': 'GYD','name': '圭亚那元'},
    {'currency': 'HKD','name': '港币|港元'},
    {'currency': 'HNL','name': '洪都拉斯伦皮拉'},
    {'currency': 'HRK','name': '克罗地亚库纳'},
    {'currency': 'HTG','name': '海地古德'},
    {'currency': 'HUF','name': '匈牙利福林'},
    {'currency': 'IDR','name': '印尼卢比'},
    {'currency': 'ILS','name': '以色列谢克尔'},
    {'currency': 'INR','name': '印度卢比'},
    {'currency': 'IQD','name': '伊拉克第纳尔'},
    {'currency': 'IRR','name': '伊朗里亚尔'},
    {'currency': 'ISK','name': '冰岛克朗'},
    {'currency': 'JMD','name': '牙买加元'},
    {'currency': 'JOD','name': '约旦第纳尔'},
    {'currency': 'JPY','name': '日元|日币|円'},
    {'currency': 'KES','name': '肯尼亚先令'},
    {'currency': 'KGS','name': '吉尔吉斯斯坦索姆'},
    {'currency': 'KHR','name': '柬埔寨瑞尔'},
    {'currency': 'KMF','name': '科摩罗法郎'},
    {'currency': 'KPW','name': '朝鲜圆'},
    {'currency': 'KRW','name': '韩元'},
    {'currency': 'KWD','name': '科威特第纳尔'},
    {'currency': 'KYD','name': '开曼群岛元'},
    {'currency': 'KZT','name': '哈萨克斯坦坚戈'},
    {'currency': 'LAK','name': '老挝基普'},
    {'currency': 'LBP','name': '黎巴嫩镑'},
    {'currency': 'LKR','name': '斯里兰卡卢比'},
    {'currency': 'LRD','name': '利比里亚元'},
    {'currency': 'LSL','name': '莱索托洛提'},
    {'currency': 'LTL','name': '立陶宛立特'},
    {'currency': 'LVL','name': '拉脱维亚拉图'},
    {'currency': 'LYD','name': '利比亚第纳尔'},
    {'currency': 'MAD','name': '摩洛哥迪拉姆'},
    {'currency': 'MDL','name': '摩尔多瓦列伊'},
    {'currency': 'MGA','name': '马尔加什阿里亚'},
    {'currency': 'MKD','name': '马其顿第纳尔'},
    {'currency': 'MMK','name': '缅甸元'},
    {'currency': 'MNT','name': '蒙古图格里克'},
    {'currency': 'MOP','name': '澳门币|澳门元'},
    {'currency': 'MRO|MRU','name': '毛里塔尼亚乌吉亚'},
    {'currency': 'MUR','name': '毛里求斯卢比'},
    {'currency': 'MVR','name': '马尔代夫拉菲亚'},
    {'currency': 'MWK','name': '马拉维克瓦查'},
    {'currency': 'MXN','name': '墨西哥比索'},
    {'currency': 'MYR','name': '林吉特'},
    {'currency': 'MZN','name': '新莫桑比克梅蒂卡尔'},
    {'currency': 'NAD','name': '纳米比亚元'},
    {'currency': 'NGN','name': '尼日利亚奈拉'},
    {'currency': 'NIO','name': '尼加拉瓜科多巴'},
    {'currency': 'NOK','name': '挪威克朗'},
    {'currency': 'NPR','name': '尼泊尔卢比'},
    {'currency': 'NZD','name': '新西兰元'},
    {'currency': 'OMR','name': '阿曼里亚尔'},
    {'currency': 'PAB','name': '巴拿马巴尔博亚'},
    {'currency': 'PEN','name': '秘鲁新索尔'},
    {'currency': 'PGK','name': '巴布亚新几内亚基那'},
    {'currency': 'PHP','name': '菲律宾比索'},
    {'currency': 'PKR','name': '巴基斯坦卢比'},
    {'currency': 'PLN','name': '波兰兹罗提'},
    {'currency': 'PYG','name': '巴拉圭瓜拉尼'},
    {'currency': 'QAR','name': '卡塔尔里亚尔'},
    {'currency': 'RON','name': '罗马尼亚列伊'},
    {'currency': 'RSD','name': '塞尔维亚第纳尔'},
    {'currency': 'RUB','name': '卢布'},
    {'currency': 'RWF','name': '卢旺达法郎'},
    {'currency': 'SAR','name': '沙特里亚尔'},
    {'currency': 'SBD','name': '所罗门群岛元'},
    {'currency': 'SCR','name': '塞舌尔法郎'},
    {'currency': 'SDG','name': '苏丹镑'},
    {'currency': 'SEK','name': '瑞典克朗'},
    {'currency': 'SGD','name': '新加坡元'},
    {'currency': 'SHP','name': '圣圣赫勒拿镑'},
    {'currency': 'SLL','name': '塞拉利昂利昂'},
    {'currency': 'SOS','name': '索马里先令'},
    {'currency': 'SRD','name': '苏里南元'},
    {'currency': 'STD','name': '圣多美多布拉'},
    {'currency': 'SVC','name': '萨尔瓦多科朗'},
    {'currency': 'SYP','name': '叙利亚镑'},
    {'currency': 'SZL','name': '斯威士兰里兰吉尼'},
    {'currency': 'THB','name': '泰铢|泰国铢'},
    {'currency': 'TJS','name': '塔吉克斯坦索莫尼'},
    {'currency': 'TMT','name': '土库曼斯坦马纳特'},
    {'currency': 'TND','name': '突尼斯第纳尔'},
    {'currency': 'TOP','name': '汤加潘加'},
    {'currency': 'TRY','name': '土耳其里拉'},
    {'currency': 'TTD','name': '特立尼达多巴哥元'},
    {'currency': 'TWD','name': '新台币'},
    {'currency': 'TZS','name': '坦桑尼亚先令'},
    {'currency': 'UAH','name': '乌克兰格里夫纳'},
    {'currency': 'UGX','name': '乌干达先令'},
    {'currency': 'USD','name': '美元|美刀|美金'},
    {'currency': 'UYU','name': '乌拉圭比索'},
    {'currency': 'UZS','name': '乌兹别克斯坦苏姆'},
    {'currency': 'VEF','name': '委内瑞拉玻利瓦尔'},
    {'currency': 'VND','name': '越南盾'},
    {'currency': 'VUV','name': '瓦努阿图瓦图'},
    {'currency': 'WST','name': '西萨摩亚塔拉'},
    {'currency': 'XAF','name': '中非金融合作法郎'},
    {'currency': 'XCD','name': '东加勒比元'},
    {'currency': 'XOF','name': '西非法郎'},
    {'currency': 'XPF','name': '法属波利尼西亚法郎'},
    {'currency': 'YER','name': '也门里亚尔'},
    {'currency': 'ZAR','name': '南非兰特'},
    {'currency': 'ZMW','name': '赞比亚克瓦查'},
    {'currency': 'ZWL','name': '津巴布韦元'},
]
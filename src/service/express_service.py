from logging import Logger
from random import random
import json
import re
import requests.api as requests

class ExpressService:
    semantic_parse: any
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.semantic_parse = kwargs['semantic_parse']

    def __real_query(self, input):
        """
        查询快递物流信息
        """
        try:
            company_name = input.get('company_name')
            company_code = input.get('company_code')
            express_no = input.get('express_no')
            phone = input.get('phone')
            if not company_name or not company_code:
                return {
                    'state': input,
                    'message': '请询问用户提供快递公司的名称',
                }
            # 获取 csrf token 和 wwwid
            url = f'https://m.kuaidi100.com/app/query/?coname=oxf-tech&nu={express_no}&com={company_code}'
            res = requests.get(url)
            set_cookie = res.headers['Set-Cookie']
            csrf_token = re.findall('csrftoken=(.*?);', set_cookie)[0]
            wwwid = re.findall('WWWID=(.*?);', set_cookie)[0]
            # 获取配送信息
            url = f'https://m.kuaidi100.com/query'
            form_data = {
                'coname': 'oxf-tech',
                'id': 1,
                'platform': 'MWWW',
                'postid': express_no,
                'temp': str(random()),
                'type': company_code,
                'phone': phone,
                'token': '',
                'valicode': '',
            }
            headers = {
                'Cookie': f'csrftoken={csrf_token}; WWWID={wwwid}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.39',
            }
            res = requests.post(url, data=form_data, headers=headers).json()
            # 快递公司要求提供验证码（即收/寄件人手机号码后四位）
            self.logger.info(res['status'])
            if res['status'] == '408':
                return {
                    'message': f'{company_name}要求，请询问用户提供收件人或寄件人手机号码后四位才能查询单号{express_no}的快递信息',
                }
            result = res['data']
            if len(result) == 0:
                self.logger.warn('快递信息查询结果为空')
                return ['快递信息查询结果为空，可能单号或提供的手机号码有误']
            results = ['{}：{}'.format(item['ftime'], item['context']) for item in result]
            return results
        except Exception as e:
            self.logger.error('查询快递信息失败：%s', e)
            return ['快递信息查询结果为空，可能单号或提供的手机号码有误']

    def extract_info(self, system_prompt:str, message:str, conditions:list=[]):
        """
        通过语义理解提取快递查询信息
        """
        try:
            if len(conditions):
                message += '\n已知信息：' + json.dumps(conditions, ensure_ascii=False)
            reply = self.semantic_parse(system_prompt=system_prompt, content=message)
            self.logger.info(reply)
            # 提取 JSON
            match = re.search(r'\[(.*)\]', reply, re.S)
            # 未提取到 JSON 结构，放弃提取
            if not match: return
            json_array = match[0]
            questions = json.loads(json_array)
            results = []
            for question in questions:
                target_express = {
                    'name': '',
                    'code': '',
                }
                company_name = re.sub('快递|物流|速运|速递', '', question['company'])
                for express in express_dict:
                    if company_name in express['name']:
                        target_express = express
                        break
                result = {
                    'company_name': target_express['name'],
                    'company_code': target_express['code'],
                    'express_no': question.get('no'),
                    'phone': question.get('phone'),
                }
                results.append(result)
            return results
        except Exception as e:
            self.logger.error(e)
            return

    def test(self, message:str):
        """
        从 message 中尝试提取快递查询信息
        如提取成功，返回 True 以及查询所需的信息，否则返回 False
        """
        if not re.search('快递|物流|速运|速递', message): return False, None
        found = False
        for express in express_dict:
            if re.search(express['pattern'], message, re.I):
                found = True
                break
        # 没有匹配到快递单号，命中测试不通过
        if not found: return False, None
        results = self.extract_info(
            system_prompt='不要回答用户问题，只从问题提取信息并按 JSON 格式返回：[{"no":"问题中出现的快递单号，没有则为空","company":"快递公司","phone":"可选，问题中出现的手机号或尾号，没有则为空"}...] 数组元素等于问题个数 不要加任何注释',
            message=message,
        )
        if not results: return False, None
        return len(results) > 0, results

    def invoke(self, data, **kwargs):
        """
        调用服务并返回信息，否则返回 None
        """
        state = kwargs['state']
        stateful = False
        stateful_message = []
        if state:
            extract_results = self.extract_info(
                system_prompt='不要回答用户问题，只从问题提取信息并按 JSON 格式返回：[{"no":"可选，问题中出现的快递单号，没有则为空","company":"快递公司","phone":"可选，问题中出现的手机号或尾号，没有则为空"}...] 数组元素等于问题个数 不要加任何注释',
                message='结合已知信息和以下信息（可能是快递公司名称或用户提供的手机尾号）查快递：' + data,
                conditions=state,
            )
            if not extract_results: return 'System enquired express info: none'
        else:
            extract_results = data
        results = []
        for index, question in enumerate(extract_results):
            if state:
                for key in ['company_name', 'company_code', 'express_no', 'phone']:
                    if not question[key]: question[key] = state[index][key]
            express_info = self.__real_query(question)
            # 需要提供进一步信息才能查询
            if type(express_info) == dict:
                stateful = True
                stateful_message.append(express_info['message'])
            else:
                result = {
                    'company_name': question['company_name'],
                    'info': '\n'.join(express_info),
                }
                extract_results[index] = result
                results.append(result)
        if stateful:
            stateful_result = {
                'state': extract_results,
                'message': ';'.join(stateful_message),
            }
            return stateful_result
        return 'System enquired express info:' + json.dumps(results, ensure_ascii=False)

express_dict = [
    {
        'code': 'zhaijisong',
        'name': '宅急送',
        'pattern': r'[a-zA-Z0-9]{10}|^(42|16)[0-9]{8}|^A[0-9]{12}'
    },
    {
        'code': 'jd',
        'name': '京东',
        'pattern': r'JD[LDVABCEX]{0,2}[0-9]{11,13}'
    },
    {
        'code': 'shunfeng',
        'name': '顺丰|顺风|顺峰',
        'pattern': r'[A-Za-z0-9-]{4,35}'
    },
    {
        'code': 'shentong',
        'name': '申通',
        'pattern': r'(888|588|688|468|568|668|768|868|968)[0-9]{9}|^(11|22)[0-9]{10}|^(STO)[0-9]{10}|^(37|33|11|22|44|55|66|77|88|99)[0-9]{11}|^(4)[0-9]{11}'
    },
    {
        'code': 'shentong',
        'name': '神通',
        'pattern': r'(888|588|688|468|568|668|768|868|968)[0-9]{9}|^(11|22)[0-9]{10}|^(STO)[0-9]{10}|^(37|33|11|22|44|55|66|77|88|99)[0-9]{11}|^(4)[0-9]{11}'
    },
    {
        'code': 'shentong',
        'name': '深通',
        'pattern': r'(888|588|688|468|568|668|768|868|968)[0-9]{9}|^(11|22)[0-9]{10}|^(STO)[0-9]{10}|^(37|33|11|22|44|55|66|77|88|99)[0-9]{11}|^(4)[0-9]{11}'
    },
    {
        'code': 'shentong',
        'name': '伸通',
        'pattern': r'(888|588|688|468|568|668|768|868|968)[0-9]{9}|^(11|22)[0-9]{10}|^(STO)[0-9]{10}|^(37|33|11|22|44|55|66|77|88|99)[0-9]{11}|^(4)[0-9]{11}'
    },
    {
        'code': 'ems',
        'name': 'EMS',
        'pattern': r'[A-Z]{2}[0-9]{9}[A-Z]{2}|^(10|11)[0-9]{11}|^(50|51)[0-9]{11}|^(95|97)[0-9]{11}'
    },
    {
        'code': 'yunda',
        'name': '韵达',
        'pattern': r'(10|11|12|13|14|15|16|17|19|18|50|55|58|80|88|66|31|77|39)[0-9]{11}|^[0-9]{13}'
    },
    {
        'code': 'zhongtong',
        'name': '中通',
        'pattern': r'((768|765|778|828|618|680|518|528|688|010|880|660|805|988|628|205|717|718|728|761|762|763|701|757|719|751|358|100|200|118|128|689|738|359|779|852)[0-9]{9})|^((5711|2008|7380|1180|2009|2013|2010|1000|1010)[0-9]{8})|^((8010|8021|8831|8013)[0-9]{6})|^((1111|90|36|11|50|53|37|39|91|93|94|95|96|98)[0-9]{10})|^((a|b|h)[0-9]{13})|^((90|80|60)[0-9]{7})|^((80|81)[0-9]{6})|^((21|23|24|25|93|94|95|96|97|110|111|112|113|114|115|116|117|118|119|121|122|123|124|125|126|127|128|129|130|131)[0-9]{8})|^(100|101|102|103|104|105|106|107|503|504|505|506|507)[0-9]{10}|^(4)[0-9]{11}|^(120)[0-9]{9}|^(780)[0-9]{9}|^(881)[0-9]{9}|^(882|885)[0-9]{9}|^(91|92)[0-9]{10}|^(54|55|56)[0-9]{10}|^(63)[0-9]{10}|^(7)[0-9]{9}|^(64)[0-9]{10}|^(72)[0-9]{10}|^(220|221|223|224|225|226|227|228|229)[0-9]{7}|^(21|22|23|24|25|26|27|28|29)[0-9]{10}|^3[0-9]{9}|^2710[0-9]{11}|^731[0-9]{11}|^751[0-9]{11}|^7320[0-9]{10}'
    },
    {
        'code': 'huitongkuaidi',
        'name': '百世',
        'pattern': r'((A|B|D|E)[0-9]{12})|^(BXA[0-9]{10})|^(K8[0-9]{11})|^(02[0-9]{11})|^(000[0-9]{10})|^(C0000[0-9]{8})|^((21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|61|63)[0-9]{10})|^((50|51)[0-9]{12})|^7[0-9]{13}|^6[0-9]{13}|^58[0-9]{14}'
    },
    {
        'code': 'yuantong',
        'name': '圆通',
        'pattern': r'[A-Za-z0-9]{2}[0-9]{10}|^[A-Za-z0-9]{2}[0-9]{8}|^[6-9][0-9]{17}|^[DD]{2}[8-9][0-9]{15}|^[Y][0-9]{12}'
    },
    {
        'code': 'quanfengkuaidi',
        'name': '全峰',
        'pattern': r'[0-6|9][0-9]{11}|^[7][0-8][0-9]{10}|^[0-9]{15}|^[S][0-9]{9,11}(-|)P[0-9]{1,2}|^[0-9]{13}|^[8][0,2-9][0,2-9][0-9]{9}|^[8][1][0,2-9][0-9]{9}|^[8][0,2-9][0-9]{10}|^[8][1][1][0][8][9][0-9]{6}'
    },
    {
        'code': 'tiantian',
        'name': '天天',
        'pattern': r'[0-9]{12}'
    },
    {
        'code': 'ems',
        'name': 'E邮宝',
        'pattern': r'[A-Z]{2}[0-9]{9}[A-Z]{2}|^(10|11)[0-9]{11}|^(50|51)[0-9]{11}|^(95|97)[0-9]{11}'
    },
    {
        'code': 'youshuwuliu',
        'name': '优速',
        'pattern': r'VIP[0-9]{9}|V[0-9]{11}|[0-9]{12}|^LBX[0-9]{15}-[2-9AZ]{1}-[1-9A-Z]{1}|^(9001)[0-9]{8}'
    },
    {
        'code': 'debangwuliu',
        'name': '德邦',
        'pattern': r'[5789]\\d{9}'
    },
    {
        'code': 'guotongkuaidi',
        'name': '国通',
        'pattern': r'(3(([0-6]|[8-9])\\d{8})|((2|4|5|6)\\d{9})|(7(?![0|1|2|3|4|5|7|8|9])\\d{9})|(8(?![2-9])\\d{9})|(2|4)\\d{11})'
    },
    {
        'code': 'suer',
        'name': '速尔',
        'pattern': r'(SUR)[0-9]{12}|^[0-9]{12}'
    },
    {
        'code': 'lianbangkuaidi',
        'name': '联邦',
        'pattern': r'[0-9]{12}'
    },
    {
        'code': 'huaqiang',
        'name': '华强',
        'pattern': r'[A-Za-z0-9]*[0|2|4|6|8]'
    },
    {
        'code': 'quanyikuaidi',
        'name': '全一',
        'pattern': r'\\d{12}|\\d{11}'
    },
    {
        'code': 'tiandihuayu',
        'name': '天地华宇',
        'pattern': r'[A-Za-z0-9]{8,9}'
    },
    {
        'code': 'huitongkuaidi',
        'name': '百世',
        'pattern': r'[0-9]{11,12}'
    },
    {
        'code': 'longbanwuliu',
        'name': '龙邦',
        'pattern': r'[0-9]{12}|^LBX[0-9]{15}-[2-9AZ]{1}-[1-9A-Z]{1}|^[0-9]{15}|^[0-9]{15}-[1-9A-Z]{1}-[1-9A-Z]{1}'
    },
    {
        'code': 'xinbangwuliu',
        'name': '新邦',
        'pattern': r'[0-9]{8}|^[0-9]{10}'
    },
    {
        'code': 'kuaijiesudi',
        'name': '快捷',
        'pattern': r'(?!440)(?!510)(?!520)(?!5231)([0-9]{9,13})|^(P330[0-9]{8})|^(D[0-9]{11})|^(319)[0-9]{11}|^(56)[0-9]{10}|^(536)[0-9]{9}'
    },
    {
        'code': 'youzhengguonei',
        'name': '邮政',
        'pattern': r'([GA]|[KQ]|[PH]){2}[0-9]{9}([2-5][0-9]|[1][1-9]|[6][0-5])|^[99]{2}[0-9]{11}|^[96]{2}[0-9]{11}|^[98]{2}[0-9]{11}'
    },
    {
        'code': 'ganzhongnengda',
        'name': '能达',
        'pattern': r'((88|)[0-9]{10})|^((1|2|3|5|)[0-9]{9})|^(90000[0-9]{7})'
    },
    {
        'code': 'rufengda',
        'name': '如风达',
        'pattern': r'[\\x21-\\x7e]{1,100}'
    },
    {
        'code': 'lianhaowuliu',
        'name': '联昊通',
        'pattern': r'[0-9]{9,12}'
    },
    {
        'code': 'jiajiwuliu',
        'name': '佳吉',
        'pattern': r'[7,1,9][0-9]{9}'
    },
    {
        'code': 'xinfengwuliu',
        'name': '信丰',
        'pattern': r'130[0-9]{9}|13[7-9]{1}[0-9]{9}|18[8-9]{1}[0-9]{9}'
    },
    {
        'code': 'guangdongyouzhengwuliu',
        'name': '广东EMS',
        'pattern': r'[a-zA-Z]{2}[0-9]{9}[a-zA-Z]{2}'
    },
]
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, ResultReason, CancellationReason
from azure.cognitiveservices.speech.audio import AudioOutputConfig
from handler.wave_handler import WaveHandler
from logging import getLogger, Logger
from os import mkdir, path, spawnv, P_WAIT
from time import time

class VoicesManager:
    engine = ''
    workdir: str
    tts_executor: dict
    voices_info: dict
    wave_handler: WaveHandler
    SPEECH_KEY = ''
    SPEECH_REGION = ''
    speech_config: SpeechConfig
    logger: Logger = None
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.engine = kwargs['engine']
        self.workdir = path.abspath(kwargs['workdir'])
        self.tts_executor = kwargs['tts_executor']
        self.SPEECH_KEY = kwargs['SPEECH_KEY']
        self.SPEECH_REGION = kwargs['SPEECH_REGION']
        self.speech_config = SpeechConfig(subscription=self.SPEECH_KEY, region=self.SPEECH_REGION)
        self.wave_handler = WaveHandler(logger=getLogger('WAVEMGR'))

    def run_tts(self, text, **kwargs):
        """
        调用 TTS 接口
        """
        voice_name = kwargs['voice_name']
        output_filename = str(round(time())) + ('.mp3' if self.engine == 'azure-tts' else '.wav')
        output_filepath = path.join(self.workdir, output_filename)
        if not path.exists(self.workdir): mkdir(self.workdir)
        result = False
        kwargs = {
            'output_filepath': output_filepath,
            'voice_name': voice_name,
            'speed': self.voices_info[voice_name][1],
            'pitch': self.voices_info[voice_name][2],
        }
        match self.engine:
            case 'azure-tts':
                result, output_filepath = self.run_azure_tts(text, **kwargs)
            case 'xf-tts':
                result, output_filepath = self.run_xf_tts(text, **kwargs)
        if result:
            self.logger.info('合成语音[%s]成功，文本长度：%s', voice_name, len(text))
        else:
            self.logger.info('合成语音[%s]未成功，文本长度：%s', voice_name, len(text))
        return result, output_filepath

    def run_azure_tts(self, text, **kwargs):
        """
        调用“Azure TTS”接口获取语音文件
        """
        output_filepath = kwargs['output_filepath']
        voice_name = kwargs['voice_name']
        speed = kwargs['speed']
        pitch = kwargs['pitch']
        self.speech_config.speech_synthesis_voice_name=self.voices_info[voice_name][0]
        audio_config = AudioOutputConfig(use_default_speaker=False, filename=output_filepath)
        speech_synthesizer = SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_config)
        speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()
        if speech_synthesis_result.reason == ResultReason.SynthesizingAudioCompleted:
            self.logger.info('语音文件已生成：%s', output_filepath)
            return True, output_filepath
        elif speech_synthesis_result.reason == ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            self.logger.warn('合成语音[角色：%s]取消：%s', voice_name, cancellation_details.reason)
            if cancellation_details.reason == CancellationReason.Error:
                if cancellation_details.error_details:
                    self.logger.error('合成语音[角色：%s]出错：%s', voice_name, cancellation_details.error_details)
            return False, None

    def run_xf_tts(self, text, **kwargs):
        """
        调用“讯飞 TTS”接口获取语音文件
        """
        program = self.tts_executor.get('xf-tts')
        if not program: return False, None
        program = path.abspath(program)
        if not path.isfile(program):
            self.logger.error('合成语音失败：启动程序 %s 不存在', program)
            return False, None
        output_filepath = kwargs['output_filepath']
        voice_name = kwargs['voice_name']
        speed = kwargs['speed']
        pitch = kwargs['pitch']
        params = (
            output_filepath,
            text,
            voice_name,
            speed,
            pitch,
        )
        ret = spawnv(P_WAIT, program, (program,) + params)
        self.logger.info('执行启动程序返回：%s', ret)
        if ret != 0: raise Exception(ret)
        self.logger.info('语音文件已生成：%s', output_filepath)
        # 转换为 amr 格式
        convert_filepath = output_filepath + '.amr'
        self.wave_handler.wave2amr(wave_path=output_filepath, output_filepath=convert_filepath)
        return True, convert_filepath
    
    def get_voices_info(self, engine):
        """
        根据 TTS 类型获取可用语音角色列表
        """
        if engine == 'azure-tts':
            # [voice_name, rate(%), pitch(%), answer_lang, gender]
            self.voices_info = {
                'Brandon': ['en-US-BrandonNeural', '0', '0', 'en', 'm'],
                'Christopher': ['en-US-ChristopherNeural', '0', '0', 'en', 'm'],
                'Eric': ['en-US-EricNeural', '0', '0', 'en', 'm'],
                'Guy': ['en-US-GuyNeural', '0', '0', 'en', 'm'],
                'Jacob': ['en-US-JacobNeural', '0', '0', 'en', 'm'],
                'Tony': ['en-US-TonyNeural', '0', '0', 'en', 'm'],
                'William': ['en-AU-WilliamNeural', '0', '0', 'en', 'm'],
                'Ana': ['en-US-AnaNeural', '0', '0', 'en', 'f'],
                'Cora': ['en-US-CoraNeural', '0', '0', 'en', 'f'],
                'Jenny': ['en-US-JennyNeural', '0', '0', 'en', 'f'],
                'Leah': ['en-ZA-LeahNeural', '0', '0', 'en', 'f'],
                'Michelle': ['en-US-MichelleNeural', '0', '0', 'en', 'f'],
                'Monica': ['en-US-MonicaNeural', '0', '0', 'en', 'f'],
                'Sara': ['en-US-SaraNeural', '0', '0', 'en', 'f'],
                '云扬': ['zh-CN-YunyangNeural', '0', '0', 'cn', 'm'],
                '云希': ['zh-CN-YunxiNeural', '0', '0', 'cn', 'm'],
                '云野': ['zh-CN-YunyeNeural', '0', '0', 'cn', 'm'],
                '云枫': ['zh-CN-YunfengNeural', '0', '0', 'cn', 'm'],
                '云皓': ['zh-CN-YunhaoNeural', '0', '0', 'cn', 'm'],
                '云健': ['zh-CN-YunjianNeural', '0', '0', 'cn', 'm'],
                '雲龍': ['zh-HK-WanLungNeural', '0', '0', 'cn', 'm'],
                '雲哲': ['zh-TW-YunJheNeural', '0', '0', 'cn', 'm'],
                '晓晓': ['zh-CN-XiaoxiaoNeural', '0', '0', 'cn', 'f'],
                '晓辰': ['zh-CN-XiaochenNeural', '0', '0', 'cn', 'f'],
                '晓涵': ['zh-CN-XiaohanNeural', '0', '0', 'cn', 'f'],
                '晓墨': ['zh-CN-XiaomoNeural', '0', '0', 'cn', 'f'],
                '晓秋': ['zh-CN-XiaoqiuNeural', '0', '0', 'cn', 'f'],
                '晓睿': ['zh-CN-XiaoruiNeural', '0', '0', 'cn', 'f'],
                '晓双': ['zh-CN-XiaoshuangNeural', '0', '0', 'cn', 'f'],
                '晓萱': ['zh-CN-XiaoxuanNeural', '0', '0', 'cn', 'f'],
                '晓颜': ['zh-CN-XiaoyanNeural', '0', '0', 'cn', 'f'],
                '晓悠': ['zh-CN-XiaoyouNeural', '0', '0', 'cn', 'f'],
                '晓北-东北': ['zh-CN-LN-XiaobeiNeural', '0', '0', 'cn', 'f'],
                '云希-四川': ['zh-CN-SC-YunxiNeural', '0', '0', 'cn', 'f'],
                '曉曼-香港': ['zh-HK-HiuMaanNeural', '0', '0', 'cn', 'f'],
                '曉佳-香港': ['zh-HK-HiuGaaiNeural', '0', '0', 'cn', 'f'],
                '曉臻-臺灣': ['zh-TW-HsiaoChenNeural', '0', '0', 'cn', 'f'],
                '曉雨-臺灣': ['zh-TW-HsiaoYuNeural', '0', '0', 'cn', 'f'],
            }
            recommended_voices = ['晓晓', '云皓', '曉臻-臺灣', 'Brandon', 'Monica']
        if engine == 'xf-tts':
            # [voice_name, rate(num), pitch(num), answer_lang, gender]
            self.voices_info = {
                'Ryan': ['x2_engam_ryan', '45', '50', 'en', 'm'],
                'John': ['x3_john', '45', '50', 'en', 'm'],
                'Catherine': ['x2_enus_catherine', '45', '50', 'en', 'f'],
                'Laura': ['x2_engam_laura', '45', '50', 'en', 'f'],
                'Lindsay': ['x2_engam_lindsay', '45', '50', 'en', 'f'],
                '逍遥': ['x2_xiaohou', '50', '50', 'cn', 'f'],
                '小璇': ['x4_lingxiaoxuan_en', '50', '50', 'cn', 'f'],
            }
            recommended_voices = ['Ryan', 'Catherine', 'Laura', '逍遥', '小璇']
        self.logger.info('加载语音角色信息成功，TTS类型：%s，数量：%d，推荐角色数量：%d', engine, len(self.voices_info), len(recommended_voices))
        return self.voices_info, recommended_voices
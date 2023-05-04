from logging import getLogger, Logger
from os import path
import subprocess

class WaveHandler:
    logger: Logger
    def __init__(self, **kwargs):
        self.logger = getLogger(self.__class__.__name__)

    def wave2amr(self, wave_path, output_filepath=None):
        wave_dir, name = path.split(wave_path)
        if name.split('.')[-1]!='wav':
            self.logger.error('不是 WAV 文件：%s', name)
            return 0
        if output_filepath is None or output_filepath.split('.')[-1]!='amr':
            amr_name = name.split('.')[0] +'.amr'
            output_filepath = path.join(wave_dir, amr_name)
        else:
            amr_dir, amr_name = path.split(output_filepath)
        error = subprocess.call(['tts/xf-tts/bin/ffmpeg', '-i', wave_path, '-y', output_filepath])
        if error:
            self.logger.error(error)
            return 0
        self.logger.info('WAV 文件已转换为 AMR 格式：%s', amr_name)
        return output_filepath, amr_name
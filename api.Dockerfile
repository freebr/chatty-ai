FROM python:3.11.2-slim
LABEL maintainer freebrOuyang
COPY bin/tts /var/www/chatty-ai/tts
ENV LD_LIBRARY_PATH=/var/www/chatty-ai/tts/xf-tts/libs/:$LD_LIBRARY_PATH
WORKDIR /var/www/chatty-ai
# Install python packages
COPY requirements.txt .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
ENTRYPOINT ["sh", "-c",\
"chmod +x tts/xf-tts/bin/xf-tts tts/xf-tts/bin/ffmpeg;\
python dist/main.py;"]

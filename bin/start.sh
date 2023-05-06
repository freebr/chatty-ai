dir_root="/root/web/chatty-ai"
echo "复制 supervisor 配置文件..."
cp -f $dir_root/supervisor/chatty-ai.ini /etc/supervisord.d/ >/dev/null 2>&1

echo "安装 python 包..."
cd $dir_root
pip install -r requirements.txt

# if [ ! -d "clash" ]; then
#     echo "部署 Clash..."
#     mkdir clash && cd clash
#     curl https://ghproxy.com/https://github.com/Dreamacro/clash/releases/download/v1.13.0/clash-linux-amd64-v3-v1.13.0.gz -O
#     gzip -d clash-linux-amd64-v3-v1.13.0.gz
#     mv clash-linux-amd64-v3-v1.13.0 clash
#     chmod +x clash
#     cd $dir_root
# fi
# process=`ps -ef | grep clash | grep -v grep`
# if [ "$process" == "" ]; then
#     echo "启动 Clash..."
#     sh -c "clash/clash -d docker-files/clash-config -f docker-files/clash-config/config.yaml &" >/dev/null 2>&1
# fi

echo "添加 tts executor 的执行权限..."
chmod +x tts/xf-tts/bin/xf-tts tts/xf-tts/bin/ffmpeg

# echo "修改 git config..."
# git config receive.denyCurrentBranch ignore

echo "准备日志目录..."
mkdir logs >/dev/null 2>&1
echo>logs/*.log

echo "运行 supervisord, supervisorctl..."
# dir_deploy=.deploy
# conf_file="$dir_deploy/etc/supervisord.conf"
if [ "$1" == "--init" ]; then
    # supervisord -c $conf_file
    supervisord
    # echo "alias supervisor='supervisorctl -c $conf_file'" >> ~/.bashrc
fi
# eval supervisorctl -c $conf_file reload
supervisorctl reload
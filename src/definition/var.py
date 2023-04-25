import os

# 开启 Websocket 服务器的数量
COUNT_WEBSOCKET_INSTANCE = 1
def setWebsocketInstanceCount(new_count: int):
    global COUNT_WEBSOCKET_INSTANCE
    if not 1 < new_count < 100: return
    COUNT_WEBSOCKET_INSTANCE = new_count

def getWebsocketInstanceCount():
    return COUNT_WEBSOCKET_INSTANCE

__is_docker: bool = None
def is_docker():
    global __is_docker
    if __is_docker is None: __is_docker = os.path.exists('/.dockerenv')
    return __is_docker
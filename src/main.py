if __name__ == '__main__':
    from const import DIR_CERT_WS, DIR_LOGS
    from os import environ, getcwd, mkdir, path
    import datetime
    import logging
    import time
    for h in logging.root.handlers: logging.root.removeHandler(h)
    if not path.exists(DIR_LOGS): mkdir(DIR_LOGS)
    logging.basicConfig(
        filename=path.join(getcwd(), f'{DIR_LOGS}/{time.strftime("%Y-%m-%d", time.localtime())}.log'),
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
        encoding='utf-8',
    )
    if time.__dict__.get('tzset'):
        time.tzset()
    else:
        logging.Formatter.converter = lambda sec, what: (datetime.datetime.now() + datetime.timedelta(hours=8)).timetuple()
    from controller.api_controller import APIController
    from controller.websocket_controller import WebsocketController
    from var import setWebsocketInstanceCount
    import web

if __name__ == '__main__':
    urls = (
        '/chatty-ai(/.*)?', 'APIController',
    )

    class MyApplication(web.application):
        logger: logging.Logger
        def __init__(self, **kwargs):
            super().__init__(kwargs.get('urls'), globals())
            self.logger = logging.getLogger('APP')
        
        def run(self, port, *middleware):
            setWebsocketInstanceCount(3)
            ws = WebsocketController(addr='0.0.0.0', secure=True, workdir=DIR_CERT_WS)
            ws.emit()
            func = self.wsgifunc(*middleware)
            self.logger.info('HTTP 服务器已启动，监听 0.0.0.0:%d...', port)
            return web.httpserver.runsimple(func, ('0.0.0.0', port))

    print('当前为开发模式' if environ['DEBUG'] == '1' else '当前为生产模式')
    port = int(environ['PORT_HTTP'])
    web.webapi.internalerror = web.debugerror
    app = MyApplication(urls=urls)
    app.run(port=port)
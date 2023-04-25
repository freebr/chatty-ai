from definition.const import ALLOWED_FILES, DIR_STATIC
import logging
import mimetypes
import os
import re
import web

class StaticController:
    logger = None
    def __init__(self):
        self.logger = logging.getLogger('STATICCTLR')
    
    def try_request_file(self, req_path: str):
        query = web.changequery()[len(req_path):]
        self.logger.info('Request: %s', req_path)
        if req_path[0] == '/': req_path = req_path[1:]
        req_path = re.sub('/{2,}', '/', req_path)
        abs_path = os.path.abspath(os.path.join(DIR_STATIC, req_path))
        if os.path.isdir(abs_path):
            if req_path and not req_path.endswith('/'):
                self.logger.info('Request: %s 301', req_path)
                req_path = '/' + req_path + '/' + query
                return web.Redirect(req_path)
            abs_path = os.path.join(abs_path, 'index.html')
        if not os.path.isfile(abs_path):
            self.logger.error('Request: %s: 404', req_path)
            return web.NotFound()
        if os.path.splitext(abs_path)[1].lower() not in ALLOWED_FILES:
            self.logger.error('Request: %s: 404 (fake)', req_path)
            return web.NotFound()
        self.logger.info('Request: %s -> %s', req_path, abs_path)
        content_type = mimetypes.guess_type(abs_path)[0] or ''
        if re.search('text|application/json', content_type):
            content_type += '; charset=utf-8'
            mode = 'r'
        else:
            mode = 'rb'
        with open(abs_path, mode) as f:
            data = f.read()
        web.header('Content-Type', f'{content_type}')
        return data

    def GET(self, req_path: str):
        if not req_path: req_path = ''
        return self.try_request_file(req_path)
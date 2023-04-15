from asyncio import new_event_loop, set_event_loop, get_event_loop, sleep
from logging import Logger
from manager.user_manager import UserManager
from time import localtime

class UserMonitor:
    last_day: str
    user_mgr: UserManager
    logger: Logger = None

    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.last_day = localtime().tm_mday
        self.user_mgr = kwargs['user_mgr']

    def run(self):
        set_event_loop(new_event_loop())
        get_event_loop().run_until_complete(self.monitor_main())
    
    async def monitor_main(self):
        while True:
            await sleep(10)
            if self.last_day != localtime().tm_mday:
                self.last_day = localtime().tm_mday
                if self.user_mgr.reset_all_daily_data():
                    self.logger.info('清除全部用户每日数据成功')
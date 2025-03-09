# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def job():
    logger.info("执行定时任务...")

# 创建调度器
scheduler = BackgroundScheduler()

# 添加任务：每 10 分钟执行一次
scheduler.add_job(job, 'interval', minutes=10)

# 启动调度器
scheduler.start()
logger.info("调度器已启动")

try:
    # 主程序保持运行
    while True:
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
    logger.info("调度器已关闭")

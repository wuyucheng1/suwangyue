# 导入哈希库，用于后续可生成唯一ID（代码内暂时未实际使用）
import hashlib
# 序列化json数据
import json
# 多线程模块，实现并发逻辑
import threading
# 时间模块，延时、时间戳
import time
# Flask Web框架核心：创建实例、路由、请求、响应、模板渲染、SSE流
from flask import *
# 队列模块，用于消息异步分发
import queue
# 类型注解，提升代码可读性与类型提示
import typing as ty
# 统计计数器，用于牌型数字计数
from collections import Counter
from settings import *
from tools import *
from views import *


# ========== 游戏主流程线程：一局游戏完整流程 ==========
def game_main_process():
    # 等待凑齐指定人数再开始游戏
    game_event.wait()
    game_event.clear()
    # 1. 初始化游戏、发牌
    init_game()
    time.sleep(5)
    # 2. 推送明牌信息
    push_open_card_info()
    # 3. 第一轮下注
    bet_round()
    # 4. 暗牌展示阶段
    show_hidden_card_delay()
    # 5. 第二轮下注
    bet_round()
    # 6. 翻开暗牌
    push_hidden_card_info()
    # 7. 胜负判定+筹码结算
    settle_game()


# ========== 程序入口：启动多线程 + Flask服务 ==========
if __name__ == "__main__":
    # 启动游戏主流程守护线程
    game_thread = threading.Thread(target=game_main_process, daemon=True)
    game_thread.start()
    # 启动消息分发守护线程
    dispatch_thread = threading.Thread(target=msg_dispatch_thread, daemon=True)
    dispatch_thread.start()
    # 启动Flask Web服务
    app.run(debug=debug)
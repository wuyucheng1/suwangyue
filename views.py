from settings import *
import json
# ========== 翻开暗牌接口：前端主动查询单玩家暗牌 ==========
@app.route('/api/fapai', methods=["POST", "GET"])
def get_single_hidden_card():
    args = request.args
    player_id = args['id']
    # 返回该玩家暗牌名称+农历日期
    return json.dumps({
        'name': festival_name[player_dict[player_id].cards[1]],
        'time': lunar_date[player_dict[player_id].cards[1]]
    })

# 临时消息列表：玩家加入房间消息暂存
temp_msg_list = []

# ========== 玩家注册/设置昵称接口 ==========
@app.route("/api/name", methods=["POST", "GET"])
def set_player_name():
    global temp_msg_list
    args = request.args
    player_id = args['id']
    # 新建玩家对象并加入玩家字典
    player_dict[player_id] = Player(name="", coin=5, cards=[])
    # 设置玩家昵称
    player_dict[player_id].name = args['name']
    # 记录玩家上线消息
    temp_msg_list.append({
        'event': 'addplayer',
        'data': {'name': f'{args["name"]}', 'id': f'{args["id"]}'}
    })

    # 人数凑齐，推送所有玩家上线消息并唤醒游戏
    if len(player_dict) == max_player_num:
        for msg in temp_msg_list:
            global_msg_queue.put(msg)
        game_event.set()
    # 超出最大人数，拒绝加入
    elif len(player_dict) > max_player_num:
        return Response('滚', 500)
    return "succeed"

# ========== 首页路由：返回前端页面，分配简易玩家ID ==========
@app.route("/")
def web_index():
    # 用当前玩家数量作为临时ID
    player_id = str(len(player_dict.keys()))
    # 渲染首页html模板，并把ID传给前端
    return render_template("./index.html", id=player_id)

# ========== 全局消息转发线程：把全局队列消息分发到每个玩家独立队列 ==========
def msg_dispatch_thread():
    global global_msg_queue
    while True:
        # 全局队列有消息则分发
        if not global_msg_queue.empty():
            msg = global_msg_queue.get()
            for pid in player_dict.keys():
                player_dict[pid].msg_queue.put(msg)
        time.sleep(1)

# ========== SSE数据流生成器：向前端持续推送消息（长连接） ==========
def sse_msg_generator(player_id):
    while True:
        # 玩家个人队列有消息，推送给前端
        if not player_dict[player_id].msg_queue.empty():
            msg = player_dict[player_id].msg_queue.get()
            yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
        # 无消息，发送心跳保活
        else:
            yield ":this is a command\n\n"
        time.sleep(1)

# ========== SSE流式接口：每个玩家独立长连接通道 ==========
@app.route("/api/stream/<id>")
def sse_stream(id: str):
    # 非法玩家ID，拒绝连接
    if id not in player_dict.keys():
        return Response("gun", 400)
    # 返回SSE响应流
    return Response(stream_with_context(sse_msg_generator(id)), mimetype='text/event-stream')
# ========== 下注接口：跟注/加注/认输 前端请求入口 ==========
@app.route("/api/grj", methods=["POST", "GET"])
def player_bet_action():
    global global_msg_queue, base_bet, total_bet, finished_player_count
    # 获取URL参数
    args = request.args
    player_id = args["id"]
    # 如果是加注，读取加注数量
    if args['cho'] == 'j':
        raise_coin = int(args['number'])

    # 逻辑1：跟注 g
    if args["cho"] == 'g' and player_dict[player_id].coin >= base_bet:
        player_dict[player_id].coin -= base_bet
        total_bet += base_bet
        finished_player_count += 1
        global_msg_queue.put({
            'event': "guanbo",
            'data': f"{player_dict[player_id].name}跟注，现在场上总共有{total_bet}个道"
        })
    # 逻辑2：加注 j
    elif args["cho"] == 'j' and player_dict[player_id].coin >= raise_coin:
        base_bet = raise_coin - 1
        total_bet += base_bet + 1
        finished_player_count = 0
        global_msg_queue.put({
            'event': "guanbo",
            'data': f"{player_dict[player_id].name}加注{raise_coin}颗道，现在场上总共有{total_bet}个道"
        })
    # 逻辑3：认输 r
    elif args["cho"] == 'r':
        player_dict[player_id].status = 0
        finished_player_count += 1
        global_msg_queue.put({
            'event': "guanbo",
            'data': f"{player_dict[player_id].name}认输，现在场上总共有{total_bet}个道"
        })
    # 筹码不足：跟注失败
    elif args["cho"] == 'g' and player_dict[player_id].coin < base_bet:
        return "dao"
    # 筹码不足：加注失败
    elif args["cho"] == 'j' and player_dict[player_id].coin < raise_coin:
        return "dao"

    # 所有玩家完成操作，唤醒游戏主线程
    if finished_player_count == max_player_num:
        game_event.set()
    return "succeed"

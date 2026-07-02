from settings import *
# 导入随机模块：随机整数、随机抽样
from random import randint, sample
from collections import Counter

# ========== 游戏初始化函数：发牌、重置玩家状态 ==========
def init_game():
    global public_card_idx, player_dict
    # 推送游戏开始事件
    global_msg_queue.put({'event': 'start', 'data': {'a': 'a'}})
    # 生成0~35所有牌下标列表
    all_card_idx = [i for i in range(36)]
    # 随机抽牌：1张公共牌 + 每位玩家2张手牌(明+暗)
    random_cards = sample(all_card_idx, k=max_player_num * 2 + 1)
    # 第0位设为公共牌
    public_card_idx = random_cards[0]
    #print(random_cards)

    idx = 1
    # 遍历所有玩家，依次分配手牌
    for player_id in player_dict.keys():
        print(player_id)
        # 给玩家分配明牌、暗牌
        player_dict[player_id].cards = [random_cards[idx * 2 - 1], random_cards[idx * 2]]
        # 重置玩家状态为正常
        player_dict[player_id].status = 1
        # 重置玩家筹码为初始5
        player_dict[player_id].coin = 5
        idx += 1

# ========== 推送明牌与公共牌信息给前端 ==========
def push_open_card_info():
    # 组装明牌推送消息
    msg_data = {
        'event': 'minpai',
        'data': {
            'public': {
                'name': festival_name[public_card_idx],
                'time': lunar_date[public_card_idx]
            }
        }
    }
    # 遍历玩家，追加每个玩家明牌信息
    for player_id in player_dict.keys():
        msg_data['data'][player_id] = {
            'name': festival_name[player_dict[player_id].cards[0]],
            'time': lunar_date[player_dict[player_id].cards[0]]
        }
    # 存入全局消息队列
    global_msg_queue.put(msg_data)

# ========== 游戏结束阶段：翻开所有玩家暗牌并推送 ==========
def push_hidden_card_info():
    msg_data = {'event': 'kaipai', 'data': {}}
    # 遍历玩家，组装暗牌数据
    for player_id in player_dict.keys():
        msg_data['data'][player_id] = {
            'name': festival_name[player_dict[player_id].cards[1]],
            'time': lunar_date[player_dict[player_id].cards[1]]
        }
    global_msg_queue.put(msg_data)

# ========== 根据牌下标，提取数字并去掉0，返回纯数字列表 ==========
def parse_card_number(card_idx: int) -> list:
    """根据牌的下标，返回拆分去0后的数字列表"""
    date_str = digital_date[card_idx]
    # 逐个字符转数字，过滤掉字符'0'
    return [int(char) for char in date_str if char != '0']

# ========== 判定牌型大小（朔月模式：类似扑克牌型比对） ==========
def calc_card_rank(num_list: list) -> tuple:
    """
    计算牌型等级与比较键
    返回：(等级值, 比较键) —— 等级值越小牌型越大；同牌型下比较键越大越强
    牌型优先级：0=四条 > 1=顺子 > 2=葫芦 > 3=三条 > 4=两对 > 5=一对 > 6=散牌
    """
    # 统计每个数字出现次数
    num_counter = Counter(num_list)
    # 按【出现次数降序、数字大小降序】排序
    sorted_items = sorted(num_counter.items(), key=lambda x: (-x[1], -x[0]))
    count_list = [cnt for _, cnt in sorted_items]
    value_list = [val for val, _ in sorted_items]

    # 1. 四条（四张相同数字）
    if count_list[0] >= 4:
        return 0, [value_list[0]]

    # 2. 顺子：数字唯一且连续，长度至少5
    unique_nums = sorted(num_counter.keys())
    is_straight = True
    for i in range(1, len(unique_nums)):
        if unique_nums[i] != unique_nums[i-1] + 1:
            is_straight = False
            break
    if is_straight and len(unique_nums) >= 5:
        return 1, [len(unique_nums), unique_nums[-1]]

    # 3. 葫芦：三条 + 一对
    if count_list[0] == 3 and count_list[1] >= 2:
        return 2, [value_list[0], value_list[1]]

    # 4. 三条
    if count_list[0] == 3:
        rest_nums = sorted([v for v, c in num_counter.items() if c != 3], reverse=True)
        return 3, [value_list[0]] + rest_nums

    # 5. 两对
    if count_list[0] == 2 and count_list[1] == 2:
        pair_vals = sorted([value_list[0], value_list[1]], reverse=True)
        rest_nums = sorted([v for v, c in num_counter.items() if c != 2], reverse=True)
        return 4, pair_vals + rest_nums

    # 6. 一对
    if count_list[0] == 2:
        rest_nums = sorted([v for v, c in num_counter.items() if c != 2], reverse=True)
        return 5, [value_list[0]] + rest_nums

    # 7. 散牌（无任何组合）
    return 6, sorted(num_list, reverse=True)

# ========== 朔月阶段胜负判定：按扑克牌型比大小 ==========
def judge_moon_fight(public_idx: int, players: dict) -> list:
    """
    朔月阶段胜负判定
    :param public_idx: 公共牌在digital_date列表中的下标
    :param players: 玩家字典，格式 {"id": Player对象}
    :return: 获胜者id列表（平局时返回多个）
    """
    # 解析公共牌数字
    public_nums = parse_card_number(public_idx)
    player_rank_list = []

    # 逐个玩家计算牌型
    for pid, player_info in players.items():
        open_idx, hidden_idx = player_info.cards
        # 合并：公共牌 + 明牌 + 暗牌 所有数字
        all_nums = public_nums + parse_card_number(open_idx) + parse_card_number(hidden_idx)
        rank, compare_key = calc_card_rank(all_nums)
        player_rank_list.append((rank, compare_key, pid))

    # 排序：牌型等级升序（越小越大），同等级按比较键降序
    player_rank_list.sort(key=lambda x: (x[0], [-k for k in x[1]]))
    best_rank, best_key, _ = player_rank_list[0]
    # 筛选出所有胜者（支持多人平局）
    winner_list = [pid for r, k, pid in player_rank_list if r == best_rank and k == best_key]
    return winner_list

# ========== 望月阶段胜负判定：数字总和规则 ==========
def judge_moon_sum(public_idx: int, players: dict) -> list:
    """
    望月阶段胜负判定（总和≤16时越接近16越强，超过16直接爆牌出局）
    :param public_idx: 公共牌在digital_date列表中的下标
    :param players: 玩家字典
    :return: 获胜者id列表；全员爆牌时返回空列表
    """
    public_nums = parse_card_number(public_idx)
    alive_player_list = []

    for pid, player_info in players.items():
        open_idx, hidden_idx = player_info.cards
        # 计算玩家所有牌数字总和
        total_sum = sum(public_nums) + sum(parse_card_number(open_idx)) + sum(parse_card_number(hidden_idx))
        # 总和≤16 才算有效玩家
        if total_sum <= 16:
            alive_player_list.append((total_sum, pid))

    # 全部玩家爆牌，无胜者
    if not alive_player_list:
        return []

    # 总和从大到小排序（越接近16越强）
    alive_player_list.sort(key=lambda x: -x[0])
    best_sum = alive_player_list[0][0]
    # 选出所有总和最大的玩家
    winner_list = [pid for s, pid in alive_player_list if s == best_sum]
    return winner_list

# ========== 下注阶段逻辑：等待所有玩家操作完成 ==========
def bet_round():
    global finished_player_count
    finished_player_count = 0
    # 推送下注开始事件
    global_msg_queue.put({'event': 'grj', 'data': 'start'})
    # 阻塞线程，等待所有玩家操作完毕唤醒
    game_event.wait()
    # 重置事件状态
    game_event.clear()
    # 推送下注结束事件
    global_msg_queue.put({'event': 'grj', 'data': 'end'})

# ========== 暗牌展示延时：暗牌阶段停留5秒 ==========
def show_hidden_card_delay():
    global_msg_queue.put({'event': 'anpai', 'data': 'start'})
    # 延时5秒
    time.sleep(5)

# ========== 结算判定：执行朔月判胜负、分配筹码 ==========
def settle_game():
    # 调用朔月判定规则得到胜者
    winner_ids = judge_moon_fight(public_card_idx, player_dict)
    # 推送结算结果
    global_msg_queue.put({'event': 'guanbo', 'data': f'胜者{winner_ids}'})
    # 给胜者分配本局总筹码
    for pid in winner_ids:
        player_dict[pid].coin += (total_bet + len(winner_ids) - 1) // len(winner_ids)

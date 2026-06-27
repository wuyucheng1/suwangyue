from random import randint,sample
import hashlib
from logging import Logger
import json
import threading
import time
from flask import *
import queue

app=Flask(__name__)
debug=False
playernumber=3
# 列表1：节气、节日名称
ming = [
    "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
    "立夏", "小满", "芒种", "夏至", "小暑", "大暑",
    "立秋", "处暑", "白露", "秋分", "寒露", "霜降",
    "立冬", "小雪", "大雪", "冬至", "小寒", "大寒",
    "春节", "元宵", "社日", "上巳", "端午", "七夕",
    "中元", "中秋", "重阳", "寒衣", "腊八", "除夕"
]

# 列表2：中文农历日期
riqi = [
    "正月初六", "正月廿一", "二月初六", "二月廿一", "三月初六", "三月廿一",
    "四月初六", "四月廿一", "五月初六", "五月廿一", "六月初六", "六月廿一",
    "七月初八", "七月廿三", "八月初八", "八月廿三", "九月初八", "九月廿三",
    "十月初八", "十月廿三", "冬月初八", "冬月廿三", "腊月初八", "腊月廿三",
    "正月初一", "正月十五", "二月初二", "三月初三", "五月初五", "七月初七",
    "七月十五", "八月十五", "九月初九", "十月初一", "腊月初八", "腊月三十"
]

# 列表3：四位数字字符串日期 格式MMDD
dian = [
    "0106", "0121", "0206", "0221", "0306", "0321",
    "0406", "0421", "0506", "0521", "0606", "0621",
    "0708", "0723", "0808", "0823", "0908", "0923",
    "1008", "1023", "1108", "1123", "1208", "1223",
    "0101", "0115", "0202", "0303", "0505", "0707",
    "0715", "0815", "0909", "1001", "1208", "1230"
]
players={}
qu=queue.Queue()
event=threading.Event()
#players[id]['name']=player name
#players[id]['dao]=player道数量
#players[id]['pai'][0]=player明牌
#players[id]['pai'][1]=player暗牌
#players[id]['qu']=queue()
#qu.put({'event':...,'data':...})
public=0
def init():
    global public,players
    qu.put({'event':'start','data':{'a':'a'}})
    tempRandChoice=[i for i in range(36)]
    temp=sample(tempRandChoice,k=playernumber*2+1)
    public=temp[0]
    print(temp)
    #print(players.keys())
    i=1
    for j in players.keys():
        print(j)
        players[j]['pai']=[temp[i*2-1],temp[i*2]]
        players[j]['sta']=1
        players[j]['dao']=5
        i+=1

def minpai():
    a={'event':'minpai','data':{'public':{'name':ming[public],'time':riqi[public]}}}
    for i in players.keys():
        a['data'][i]={'name':ming[players[i]['pai'][0]],
                      'time':riqi[players[i]['pai'][0]]}
    qu.put(a)
def kaipai():
    a={'event':'kaipai','data':{}}
    for i in players.keys():
        a['data'][i]={'name':ming[players[i]['pai'][1]],
                      'time':riqi[players[i]['pai'][1]]}
    qu.put(a)
from collections import Counter
def get_nums_by_idx(idx: int) -> list:
    """根据牌的下标，返回拆分去0后的数字列表"""
    date_str = dian[idx]
    return [int(c) for c in date_str if c != '0']


def get_hand_rank(all_nums: list) -> tuple:
    """
    计算牌型等级与比较键
    返回：(等级值, 比较键) —— 等级值越小牌型越大；同牌型下比较键越大越强
    牌型优先级：0=四条 > 1=顺子 > 2=葫芦 > 3=三条 > 4=两对 > 5=一对 > 6=散牌
    """
    count = Counter(all_nums)
    sorted_counts = sorted(count.items(), key=lambda x: (-x[1], -x[0]))
    counts = [cnt for _, cnt in sorted_counts]
    values = [val for val, _ in sorted_counts]

    # 四条
    if counts[0] >= 4:
        return 0, [values[0]]

    # 顺子：唯一数字连续且长度≥5
    unique_nums = sorted(count.keys())
    is_straight = True
    for i in range(1, len(unique_nums)):
        if unique_nums[i] != unique_nums[i-1] + 1:
            is_straight = False
            break
    if is_straight and len(unique_nums) >= 5:
        return 1, [len(unique_nums), unique_nums[-1]]

    # 葫芦：三条+对子
    if counts[0] == 3 and counts[1] >= 2:
        return 2, [values[0], values[1]]

    # 三条
    if counts[0] == 3:
        rest = sorted([v for v, c in count.items() if c != 3], reverse=True)
        return 3, [values[0]] + rest

    # 两对
    if counts[0] == 2 and counts[1] == 2:
        pair_vals = sorted([values[0], values[1]], reverse=True)
        rest = sorted([v for v, c in count.items() if c != 2], reverse=True)
        return 4, pair_vals + rest

    # 一对
    if counts[0] == 2:
        rest = sorted([v for v, c in count.items() if c != 2], reverse=True)
        return 5, [values[0]] + rest

    # 散牌
    return 6, sorted(all_nums, reverse=True)


def shuo_yue_judge(public_idx: int, players: dict) -> list:
    """
    朔月阶段胜负判定
    :param public_idx: 公共牌在dian列表中的下标
    :param players: 玩家字典，格式 {"id": {"pai": [明牌下标, 暗牌下标]}}
    :return: 获胜者id列表（平局时返回多个）
    """
    public_nums = get_nums_by_idx(public_idx)
    player_ranks = []

    for pid, info in players.items():
        open_idx, hidden_idx = info["pai"]
        all_nums = public_nums + get_nums_by_idx(open_idx) + get_nums_by_idx(hidden_idx)
        rank, key = get_hand_rank(all_nums)
        player_ranks.append((rank, key, pid))

    # 排序：等级升序，比较键降序
    player_ranks.sort(key=lambda x: (x[0], [-k for k in x[1]]))
    best_rank, best_key, _ = player_ranks[0]
    winners = [pid for r, k, pid in player_ranks if r == best_rank and k == best_key]
    return winners


def wang_yue_judge(public_idx: int, players: dict) -> list:
    """
    望月阶段胜负判定（总和≤16时越接近16越强，超过16直接爆牌出局）
    :param public_idx: 公共牌在dian列表中的下标
    :param players: 玩家字典，格式 {"id": {"pai": [明牌下标, 暗牌下标]}}
    :return: 获胜者id列表；全员爆牌时返回空列表
    """
    public_nums = get_nums_by_idx(public_idx)
    alive_players = []

    for pid, info in players.items():
        open_idx, hidden_idx = info["pai"]
        total = sum(public_nums) + sum(get_nums_by_idx(open_idx)) + sum(get_nums_by_idx(hidden_idx))
        if total <= 16:
            alive_players.append((total, pid))

    if not alive_players:
        return []

    # 总和越大越接近16
    alive_players.sort(key=lambda x: -x[0])
    best_total = alive_players[0][0]
    winners = [pid for t, pid in alive_players if t == best_total]
    return winners




def main():
    global gens
    event.wait()
    event.clear()
    init()
    #print('aaa')
    time.sleep(5)
    minpai()
    qu.put({'event':'grj','data':'start'})
    event.wait()
    event.clear()
    qu.put({'event':'grj','data':'end'})
    
    qu.put({'event':'anpai','data':'start'})
    time.sleep(5)
    #qu.put({'event':'anpai','data':'end'})

    gens=0
    qu.put({'event':'grj','data':'start'})
    event.wait()
    event.clear()
    qu.put({'event':'grj','data':'end'})
    kaipai()
    temp=shuo_yue_judge(public,players)
    qu.put({'event':'guanbo','data':f'胜者{temp}'})
    for i in temp:
        players[i]['dao']+=(sum+len(temp)-1)//len(temp)
    


mma=1
sum=0
gens=0
@app.route("/api/grj",methods=["POST","GET"])
def grj():
    global qu,mma,sum,gens
    #g跟注，j加注，r认输
    args=request.args
    id=args["id"]
    if(args['cho']=='j'):
        daoshu=int(args['number'])
    if args["cho"]=='g' and players[id]['dao']>=mma:
        players[id]['dao']-=mma
        sum+=mma
        gens+=1
        qu.put({'event':"guanbo",'data':f"{players[id]['name']}跟注，现在场上总共有{sum}个道"})
    elif args["cho"]=='j' and players[id]['dao']>=daoshu:
        mma=daoshu-1
        sum+=mma+1
        gens=0
        qu.put({'event':"guanbo",'data':f"{players[id]['name']}加注{daoshu}颗道，现在场上总共有{sum}个道"})
    elif args["cho"]=='r':
        players[id]['sta']=0
        gens+=1
        qu.put({'event':"guanbo",'data':f"{players[id]['name']}认输，现在场上总共有{sum}个道"})
    elif args["cho"]=='g' and players[id]['dao']<mma:
        return "dao"
    elif args["cho"]=='j' and players[id]['dao']<daoshu:
        return "dao"
    if gens==playernumber:
        event.set()
    return "succeed"

@app.route('/api/fapai',methods=["POST","GET"])
def fapai():
    args=request.args
    return json.dumps({'name':ming[players[args['id']]['pai'][1]],
                       'time':riqi[players[args['id']]['pai'][1]]})

templist=[]
@app.route("/api/name",methods=["POST","GET"])
def name():
    global templist
    args=request.args
    players[args['id']]['name']=args['name']
    templist.append({'event':'addplayer','data':{'name':f'{args['name']}','id':f'{args['id']}'}})
    if(len(players)==playernumber):
        for i in templist:
            qu.put(i)
        event.set()
    elif len(players)>playernumber:
        return Response('滚',500)
    return "succeed"

@app.route("/")
def index():
    #id=hashlib.md5(str(time.time()+randint(1,1000)).encode('utf-8')).hexdigest()
    id=str(len(players.keys()))
    players[id]={'qu':queue.Queue()}
    return render_template("./index.html",id=id)

def main1():
    global qu
    while True:
        if not qu.empty():
            temp=qu.get()
            for i in players.keys():
                players[i]['qu'].put(temp)
        time.sleep(1)

def gen(id):
    while True:
        if not players[id]['qu'].empty():
            temp=players[id]['qu'].get()
            yield f"event: {temp['event']}\ndata: {json.dumps(temp['data'])}\n\n"
        else:
            yield ":this is a command\n\n"
        time.sleep(1)

@app.route("/api/stream/<id>")
def stream(id:str):
    if(not id in players.keys()):
        return Response("gun",400)
    return Response(stream_with_context(gen(id)),mimetype='text/event-stream')

if __name__=="__main__":
    thread=threading.Thread(target=main,daemon=True)
    thread.start()
    thread1=threading.Thread(target=main1,daemon=True)
    thread1.start()
    app.run(debug=debug)
from random import randint,choices
import hashlib
import json
import threading
import time
from flask import *
import queue
app=Flask(__name__)
debug=True
playernumber=5
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
#qu.put({'event':...,'data':...})
public=0
def init():
    global public
    qu.put({'event':'start','a':'a'})
    tempRandChoice=[i for i in range(1,37)]
    temp=choices(tempRandChoice,k=playernumber*2+1)
    public=temp[0]
    for i,j in temp[1::2],players.keys():
        players[j]['pai']=[].append(i)
        players[j]['dao']=5
    for i,j in temp[2::2],players.keys():
        players[j]['pai'].append(i)

def minpai():
    a={'event':'minpai','data':{'public':{'name':ming[public],'time':riqi[public]}}}
    for i in players.keys():
        a['data'][i]={'name':ming[players[i]['pai'][0]],
                      'time':riqi[players[i]['pai'][0]]}
    qu.put(a)
def main():
    event.wait()
    event.clear()
    init()
    minpai()


mma=1
sum=0
@app.route("/api/grj",methods=["POST"])
def grj():
    sta=[]
    global qu,mma,sum,gens
    #g跟注，j加注，r认输
    #TODO:公示状态
    args=request.args
    id=args["id"]
    if sta[id]!=1:
        return 'gun'
    if args["cho"]=='g' and players[id]['dao']>=mma:
        players[id]['dao']-=mma
        sum+=mma
        gens+=1
    elif args["cho"]=='j' and players[id]['dao']>=args['number']:
        mma=args['number']-1
        sum+=mma+1
        gens=0
    elif args["cho"]=='r':
        sta[id]=0
    event.set()
    return "success"

@app.route('/api/fapai',methods=["POST"])
def fapai():
    args=request.args
    return json.dumps({'name':ming[players[args['id']]['pai'][1]],
                       'time':riqi[players[args['id']]['pai'][1]]})

@app.route("/api/name",methods=["POST"])
def name():
    args=request.args
    players[args['id']]['name']=args['name']
    qu.put({'event':'addplayer','data':{'name':f'{args[name]}'}})
    if(len(players)==playernumber):
        event.set()
    return "succeed"

@app.route("/")
def index():
    id=hashlib.md5(str(time.time()+randint(1,1000)).encode('utf-8')).hexdigest()
    players[id]={}
    return render_template("./index.html",id=id)

def gen():
    global qu
    while True:
        if not qu.empty():
            temp=qu.get()
            yield f"event: {temp['event']}\ndata: {json.dumps(temp['data'])}\n\n"
        else:
            yield ":this is a command\n\n"
        time.sleep(1)

@app.route("/api/stream/")
def stream():
    return Response(stream_with_context(gen()),mimetype='text/event-stream')

if __name__=="__main__":
    #thread=threading.Thread(target=main)
    #thread.start()
    app.run(debug=debug)
from random import randint,choices
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
ids=[]
playere=[]
chudao=0
qu=queue.Queue()
start=False
event=threading.Event()
sta={}
#TODO:修改发牌逻辑保证发牌每张只有一张
def fapai():
    global qu
    a=choices(range(36),k=playernumber)
    for i,cho in players,a:
        id=i[0]
        players[id]['pai'].append(cho)
        qu.put(str({'event':'minpai','id':id,'pai':{'name':ming[cho],'time':riqi[cho]}}))
gens=0
def operate():
    global qu
    i=0
    while True:
        id=ids[i]
        qu.put(str({'event':'operate','id':id,'res':'start'}))
        event.wait()
        event.clear()
        if gens==playernumber:
            break
        i+=1
        i%=playernumber
anpai={}
def faanpai():
    global qu
    a=choices(range(36),playernumber)
    for i,j in players,a:
        anpai[i[0]]=j
    for i in players:
        id=i[0]
        qu.put(str({'event':'anpai','id':id,'res':'start'}))
        event.wait()
        event.clear()
def main():
    while True:
        if start:
            break
        time.sleep(1)
    fapai()
    operate()
    faanpai()


@app.route("/api/id",methods=["POST"])
def getid():
    global qu
    name = request.args.get("neme")
    if name in players.keys():
        return "{'id':'error','error':'名称已存在'}"
    else:
        a=randint(1,10000)
        while not (a in ids):
            a=randint(1,10000)
        players[id]={'pai':[],'dao':chudao}
        playere.append(str({'event':'addplayer','name':name,'id':id}))
        sta[id]=1
        if len(playere)==playernumber:
            for i in playere:
                qu.put(i)
            playere.clear()
        return "{'id':'"+str(a)+"'}"

mma=1
sum=0
@app.route("/api/grj",methods=["POST"])
def grj():
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

@app.route("/api/anpai",methods=["POST"])
def getanpai():
    global qu
    args=request.args
    id=args['id']['pai'].append(anpai[id])
    players[id]
    return str({'name':ming[anpai[id]],'time':riqi[anpai[id]]})

@app.route("/")
def index():
    return render_template("./index.html")

def gen():
    global qu
    while True:
        if not qu.empty():
            yield f"event: json\ndata: {qu.get()}\n\n"
        else:
            yield ":this is a command\n\n"
        time.sleep(1)

@app.route("/api/stream/")
def stream():
    return Response(stream_with_context(gen()),mimetype='text/event-stream')

if __name__=="__main__":
    thread=threading.Thread(target=main)
    thread.start()
    app.run(debug=debug)
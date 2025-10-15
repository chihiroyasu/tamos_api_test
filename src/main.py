import uvicorn
from fastapi import FastAPI, WebSocket, Response, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build
from google.oauth2 import service_account
from fastapi.responses import JSONResponse, FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
from PIL import Image
from io import BytesIO
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import sys
sys.path.append('/home/user/.local/lib/python3.10/site-packages')
from apscheduler.schedulers.background import BackgroundScheduler
sys.path.append('/home/user/.local/lib/python3.10/site-packages')
import mysql.connector
from pydantic import BaseModel
import gspread
from google.oauth2.service_account import Credentials
import base64
from pathlib import Path
import glob
import subprocess
import time
import csv
import logging
import aiofiles
import yaml
from src.hosizora.tentai_keisan_gif import tentai_keisan_gif
from src.getSunImage.auto_get_SunImage import get_seestar_image, download_file_with_service_account
from src.getSunImage.sunspots_area import process_latest_image
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

access_log = logging.getLogger('uvicorn.access')
ac_file_handler = logging.FileHandler('/app/src/log/uvicorn_access.log')
ac_format = logging.Formatter('%(asctime)s [%(levelname)s]  %(message)s')
access_log.addHandler(ac_file_handler)
ac_file_handler.setFormatter(ac_format)


error_log = logging.getLogger('uvicorn.error')
error_log.setLevel(logging.WARNING)
er_file_handler = logging.FileHandler('/app/src/log/uvicorn_error.log')
er_format = logging.Formatter('%(asctime)s [%(levelname)s]  %(message)s {%(filename)s:%(funcName)s:%(lineno)d}')
error_log.addHandler(er_file_handler)
er_file_handler.setFormatter(er_format)

MYSQL_HOST = 'WebDataBase_mysql'
MYSQL_DATABASE = 'livee'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'tenki2022'
MYSQL_PORT = '3307'

db_config  = {
    "host": "WebDataBase_mysql",
    "user": "root",
    "password": "tenki2022",
    "database": "livee",
    # 'port': 3306,
}


app = FastAPI()
app.mount('/skytree_dir', StaticFiles(directory='/mnt/data/201'))
app.mount('/fuji_dir', StaticFiles(directory='/mnt/data/203'))
app.mount('/matome', StaticFiles(directory='/mnt/data/narabe1'))

#cors設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web-tamos.vercel.app",
        "https://tamos-web.vercel.app",
        "https://web-gold-phi.vercel.app",
        "http://localhost:3000",
        "http://toms-server.tail2925.ts.net",
        "http://100.119.204.18:3000",
        "http://100.72.175.120:3000",
        "http://localhost:3030",
        "http://100.119.204.18:3030",
        ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

scheduler = BackgroundScheduler()

available_devices = ["livee", "bushitsu", "1go", "2go", "3go", "4go", "5go"]
deviceNameToId = {
    "livee": "10",
    "bushitsu": "11",
    "1go": "201",
    "2go": "202",
    "3go": "203",
    "4go": "204",
    "5go": "205",
}

#db接続関数
def connect_db(device):
    return mysql.connector.connect(
        user="root", password="tenki2022", host="mysql", database=device
    )

# 画像の圧縮関数(-> JPEG)
def compress_img(img: Image.Image, quality: int = 30) -> BytesIO:
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return buffer #バイナリデータ



### リアルタイムデータ表示ページ('/')
## 都心方面リアルタイムデータ取得(fetchLatestImages)
#最新撮影画像の取得
@app.get("/latest_image")
def response_latest():
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    day = time.strftime("%d")
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    formatted_time = now.strftime('%Y%m%d-%H%M')[:-1] + '0'
    path = "/mnt/data/201"
    files = glob.glob(path + f"/{formatted_time}*jpg")

    if not files:
        path = f"/mnt/data/201/{year}/{mon}"
        night = f"{year}{mon}{day}-19"
        files = glob.glob(path + f"/{night}*jpg")

        if not files:
            prev_day = now - timedelta(days=1)
            prev_day_str = prev_day.strftime('%Y%m%d')
            night = f"{prev_day_str}-19"
            files = glob.glob(path + f"/{night}*jpg")

            if not files:
                return {"error": "No image file found at the specified time."}

    files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
    file_path = files_sorted[0] if files else None

    if not file_path:
        return {"error": "No image file found after sorting."}
    
    img = Image.open(file_path)
    buffer = compress_img(img)
    return StreamingResponse(buffer, media_type="image/jpeg")


#10分前撮影画像の取得
@app.get("/10minago_image")
def response_ten_min_ago(background_tasks: BackgroundTasks):
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    day = time.strftime("%d")
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    ten_minutes_ago = now - timedelta(minutes=10)
    ten_ago = ten_minutes_ago.strftime('%Y%m%d-%H%M')
    formatted_ten_ago = ten_ago[:-1] + '0'
    path = "/mnt/data/201"
    files = glob.glob(path + f"/{formatted_ten_ago}*jpg")

    if not files:
        path = f"/mnt/data/201/{year}/{mon}"
        night = f"{year}{mon}{day}-19"
        files = glob.glob(path + f"/{night}*jpg")

        if not files:
            prev_day = now - timedelta(days=1)
            prev_day_str = prev_day.strftime('%Y%m%d')
            night = f"{prev_day_str}-19"
            files = glob.glob(path + f"/{night}*jpg")

            if not files:
                return {"error": "No image file found at the specified time."}

    files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
    file_path = files_sorted[1] if len(files_sorted) > 1 else files_sorted[0]

    if not file_path:
        return {"error": "No image file found after sorting."}
    
    img = Image.open(file_path)
    buffer = compress_img(img)
    return StreamingResponse(buffer, media_type="image/jpeg")


#20分前の撮影画像の取得
@app.get("/20minago_image")
def response_twe_min_ago(background_tasks: BackgroundTasks):
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    day = time.strftime("%d")
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    twe_minutes_ago = now - timedelta(minutes=20)
    twe_ago = twe_minutes_ago.strftime('%Y%m%d-%H%M')
    formatted_twe_ago = twe_ago[:-1] + '0'
    path = "/mnt/data/201"
    files = glob.glob(path + f"/{formatted_twe_ago}*jpg")

    if not files:
        path = f"/mnt/data/201/{year}/{mon}"
        night = f"{year}{mon}{day}-19"
        files = glob.glob(path + f"/{night}*jpg")

        if not files:
            prev_day = now - timedelta(days=1)
            prev_day_str = prev_day.strftime('%Y%m%d')
            night = f"{prev_day_str}-19"
            files = glob.glob(path + f"/{night}*jpg")

            if not files:
                return {"error": "No image file found at the specified time."}

    files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
    file_path = files_sorted[1] if len(files_sorted) > 1 else files_sorted[0]

    if not file_path:
        return {"error": "No image file found after sorting."}
    
    img = Image.open(file_path)
    buffer = compress_img(img)
    return StreamingResponse(buffer, media_type="image/jpeg")


# 画像の圧縮
def compress_image(file_path: str, background_tasks: BackgroundTasks):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_path = temp_file.name
            with Image.open(file_path) as img:
                img = img.convert("RGB")  # RGB変換
                img.save(temp_path, "JPEG", quality=50)  # 圧縮処理
            background_tasks.add_task(os.remove, temp_path)
            return temp_path
    except Exception as e:
        raise Exception(f"Failed to process image: {str(e)}")


# 最新撮影画像に合わせたinfoの取得
@app.get("/latest_info")
def latest_imfo():
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    formatted_time = now.strftime('%Y/%m/%d %H:%M')[:-1] + '0'
    
    db = connect_db("livee")
    query = "select temperature, humidity from geppo where date like '%0:00' order by date desc limit 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        weather_info = rows[0]
        return {"time": formatted_time, "weather_info": weather_info}
    else:
        return {"time": formatted_time, "weather_info": []}
 
   
# 10min前の画像に合わせたinfoの取得
@app.get("/10minago_info")
def latest_imfo():
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    ten_minutes_ago = now - timedelta(minutes=10)
    ten_ago = ten_minutes_ago.strftime('%Y/%m/%d %H:%M')
    formatted_ten_ago = ten_ago[:-1] + '0'
    
    db = connect_db("livee")
    query = "select temperature, humidity from geppo where date like '%0:00' order by date desc limit 1, 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        weather_info = rows[0]
        return {"time": formatted_ten_ago, "weather_info": weather_info}
    else:
        return {"time": formatted_ten_ago, "weather_info": []}
    

# 20min前の画像に合わせたinfoの取得
@app.get("/20minago_info")
def latest_imfo():
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    twe_minutes_ago = now - timedelta(minutes=20)
    twe_ago = twe_minutes_ago.strftime('%Y/%m/%d %H:%M')
    formatted_ten_ago = twe_ago[:-1] + '0'
    
    db = connect_db("livee")
    query = "select temperature, humidity from geppo where date like '%0:00' order by date desc limit 2, 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        weather_info = rows[0]
        return {"time": formatted_ten_ago, "weather_info": weather_info}
    else:
        return {"time": formatted_ten_ago, "weather_info": []}


@app.get("/testtest")
def testtest():
    return "aa"


# 最新撮影画像に合わせた自動視程判別結果の取得
@app.get("/latest_class")
def latest_class():
    db = connect_db("1go")
    query = "select class from visibility order by id desc limit 1"   #where date like 何たらに
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        classes = [row[0] for row in rows]
        return classes
    else:
        return []
    

# 10min前の撮影画像に合わせた自動視程判別結果の取得
@app.get("/10minago_class")
def latest_class():
    db = connect_db("1go")
    query = "select class from visibility order by id desc limit 1, 1"   #where date like 何たらに
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        classes = [row[0] for row in rows]
        return classes
    else:
        return []
    

# 20min前の撮影画像に合わせた自動視程判別結果の取得
@app.get("/20minago_class")
def latest_class():
    db = connect_db("1go")
    query = "select class from visibility order by id desc limit 2, 1"   #where date like 何たらに
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        classes = [row[0] for row in rows]
        return classes
    else:
        return []



## 富士山方面リアルタイムデータの取得(fetchFujiLatestImages)
# 富士山方面最新撮影画像の取得
@app.get("/Fuji_latest_image")
def latest_image(background_tasks: BackgroundTasks):
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    minute = int(now.strftime("%M"))
    formatted_time = now.strftime('%Y%m%d-%H%M')[:-2] + ('30' if minute >= 30 else '00')
    path = "/mnt/data/203/night"
    files = glob.glob(f"{path}/{formatted_time}*jpg")
    if not files:
        path = "/mnt/data/203/bigdata"
        files = glob.glob(f"{path}/{formatted_time}*jpg")
        if not files:
            return {"error": "No image file found at the specified time."}
    files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
    compressed_path = compress_image(files_sorted[0], background_tasks)
    return FileResponse(compressed_path, media_type="image/jpeg")


# 30min前の富士山方面撮影画像の取得
@app.get("/Fuji_30minago_image")
def image_30min_ago(background_tasks: BackgroundTasks):
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST) - timedelta(minutes=30)
    minute = int(now.strftime("%M"))
    formatted_time = now.strftime('%Y%m%d-%H%M')[:-2] + ('30' if minute >= 30 else '00')
    path = "/mnt/data/203/night"
    files = glob.glob(f"{path}/{formatted_time}*jpg")
    if not files:
        path = "/mnt/data/203/bigdata"
        files = glob.glob(f"{path}/{formatted_time}*jpg")
        if not files:
            return {"error": "No image file found at the specified time."}
    files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
    compressed_path = compress_image(files_sorted[0], background_tasks)
    return FileResponse(compressed_path, media_type="image/jpeg")


# 60min前の富士山方面撮影画像の取得
@app.get("/Fuji_60minago_image")
def image_60min_ago(background_tasks: BackgroundTasks):
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST) - timedelta(minutes=60)
    minute = int(now.strftime("%M"))
    formatted_time = now.strftime('%Y%m%d-%H%M')[:-2] + ('30' if minute >= 30 else '00')
    path = "/mnt/data/203/night"
    files = glob.glob(f"{path}/{formatted_time}*jpg")
    if not files:
        path = "/mnt/data/203/bigdata"
        files = glob.glob(f"{path}/{formatted_time}*jpg")
        if not files:
            return {"error": "No image file found at the specified time."}
    files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
    compressed_path = compress_image(files_sorted[0], background_tasks)
    return FileResponse(compressed_path, media_type="image/jpeg")


# 富士山方面自動判別結果(富士山のTrue or False)の取得
@app.get("/Fuji_latest_class")
def latest_class():
    db = connect_db("1go")
    query = "select class from visibility order by id desc limit 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
  
    if rows:
        classes = [row[0] for row in rows]
        classes = "Φ"  #いずれTrue or False映せると良いね
        return classes
    else:
        return []


# 30min前の富士山方面自動判別結果の取得
@app.get("/Fuji_30minago_class")
def latest_class():
    db = connect_db("1go")
    query = "select class from visibility order by id desc limit 1, 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        classes = [row[0] for row in rows]
        classes = "Φ"
        return classes
    else:
        return []
    
    
# 60min前の富士山方面自動判別結果の取得
@app.get("/Fuji_60minago_class")
def latest_class():
    db = connect_db("1go")
    query = "select class from visibility order by id desc limit 2, 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        classes = [row[0] for row in rows]
        classes = "Φ"
        return classes
    else:
        return []


#  最新撮影画像に合わせたinfoの取得
@app.get("/Fuji_latest_info")
def latest_imfo():
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    minute = int(now.strftime("%M"))
    if minute >= 30:
        formatted_time = now.strftime('%Y/%m/%d %H:%M')[:-2] + '30'
    else:
        formatted_time = now.strftime('%Y/%m/%d %H:%M')[:-2] + '00'
    
    db = connect_db("livee")
    query = "select temperature, humidity from geppo where date like '%0:00' order by date desc limit 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    # return {"time": formatted_time, "weather_info": rows}
    if rows:
        weather_info = rows[0]
        return {"time": formatted_time, "weather_info": weather_info}
    else:
        return {"time": formatted_time, "weather_info": []}


# 30min前の画像に合わせたinfoの取得
@app.get("/Fuji_30minago_info")
def latest_imfo():
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST) - timedelta(minutes=30)
    minute = int(now.strftime("%M"))
    if minute >= 30:
        formatted_time = now.strftime('%Y/%m/%d %H:%M')[:-2] + '30'
    else:
        formatted_time = now.strftime('%Y/%m/%d %H:%M')[:-2] + '00'
    
    db = connect_db("livee")
    query = "select temperature, humidity from geppo where date like '%0:00' order by date desc limit 1, 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        weather_info = rows[0]
        return {"time": formatted_time, "weather_info": weather_info}
    else:
        return {"time": formatted_time, "weather_info": []}
    
    
# 60min前の画像に合わせたinfoの取得
@app.get("/Fuji_60minago_info")
def latest_imfo():
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST) - timedelta(minutes=60)
    minute = int(now.strftime("%M"))
    if minute >= 30:
        formatted_time = now.strftime('%Y/%m/%d %H:%M')[:-2] + '30'
    else:
        formatted_time = now.strftime('%Y/%m/%d %H:%M')[:-2] + '00'
    
    db = connect_db("livee")
    query = "select temperature, humidity from geppo where date like '%0:00' order by date desc limit 2, 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
    if rows:
        weather_info = rows[0]
        return {"time": formatted_time, "weather_info": weather_info}
    else:
        return {"time": formatted_time, "weather_info": []}



## 視程観測装置撮影ログ等の取得(fetchLogs)
@app.get("/{device}/logs")
def fetch_log(device):
    if device not in available_devices:
        raise HTTPException(status_code=404, detail={"message": "device not found"})
    log_root = f"/mnt/data/{deviceNameToId[device]}/log"
    res = {}
    for file_name in os.listdir(log_root):
        log_content = ""
        cmd = f"tail -n5 {os.path.join(log_root, file_name)}".split(" ")
        for output in subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.readlines():
            log_content += output.decode("utf-8")
        if log_content:
            res[file_name] = log_content
    return res



## 各方面観測装置のinfo(USB使用率など)取得
@app.get("/{device}/info")
def fetch_latest_data(device):
    if device not in available_devices:
        raise HTTPException(status_code=404, detail={"message": "device not found"})
    table_col = {
        "hourly": [
            "date",
            "temperature",
            "humidity",
            "cpuTemperature",
        ],
        "daily": [
            "uptime",
            "usbUsage",
            "sdCardUsage",
        ],
    }
    db = connect_db(device)
    res = {}
    for table, colNames in table_col.items():
        for name in colNames:
            sql_query = f"SELECT {name} FROM {table} ORDER BY id DESC LIMIT 1"
            with db.cursor() as cursor:
                cursor.execute(sql_query)
                res[name] = cursor.fetchone()[0]
    return res


@app.get("/{device}/usages")
def fetch_usages(device):
    if device not in available_devices:
        raise HTTPException(status_code=404, detail={"message": "device not found"})
    
    graphColNames = [
        "date",
        "temperature",
        "humidity",
        "cpuTemperature",
        "cpuUsage",
        "memUsage",
    ]
    
    db = connect_db(device)
    res = {}
    
    for name in graphColNames:
        sql_query = f"SELECT {name} FROM hourly ORDER BY date DESC LIMIT 24"
        with db.cursor() as cursor:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
        
        if name == "date":
            res[name] = [row[0].strftime('%H:%M') for row in rows]
        else:
            res[name] = [row[0] for row in rows]
    
    return res




### Live-E!データ閲覧ページ('/weather')
## 気象データの取得(search)
# 指定させた気象データの取得
@app.get("/pastdata/{kind}/{start_date}/{last_date}")
def fetch_sql_data(kind: str, start_date: str, last_date: str):
    db = connect_db("livee")
    res = {}
    
    query = f"SELECT date, {kind} FROM geppo WHERE date BETWEEN '{start_date}' AND '{last_date}'"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        data = [{"date": row[0], kind: row[1]} for row in rows]
        res["data"] = data
    return res

## 指定された気象データのCSV出力
# データ検索
def get_sql_data(firstKind: str, secondKind: str, begin_date: str, end_date: str) -> List[Dict]:
    db = connect_db("livee")
    res = {}
    query = f"SELECT date, {firstKind}, {secondKind} FROM geppo WHERE date BETWEEN '{begin_date}' AND '{end_date}'"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        data = [{"data": row[0], firstKind: row[1], secondKind: row[2]} for row in rows]
        res["data"] = data
    return res


# CSVを作成する関数
def create_csv_from_data(data: List[Dict], filename: str) -> None:
    if not data:
        return
    header = list(data[0].keys())
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(data)


# CSVファイルを投げる
@app.get("/pastdata/{firstKind}/{secondKind}/{begin_date}/{end_date}")
def get_and_return_csv(firstKind: str, secondKind: str, begin_date: str, end_date: str):
    data = get_sql_data(firstKind, secondKind, begin_date, end_date)["data"]
    csv_filename = f"{firstKind}{secondKind}-{begin_date}-{end_date}.csv"
    create_csv_from_data(data, csv_filename)
    return FileResponse(csv_filename, filename=csv_filename)

    



### 各観測装置撮影データの一覧表示ページ('/images')
## 指定された画像の取得(fetchSelectedImages)
# 指定区間の画像ファイルリスト取得
class Searched_images(BaseModel):
    name: List[str] = None
    urls: List[str] = None
    times: List[str] = None
    description: List[str] = None      #descriptionは実装するの難しい

pwd = os.path.dirname(__file__)
conf_path = os.path.join(pwd, 'settings.yaml')
with open(conf_path) as f:
    conf = yaml.safe_load(f)
base_path = conf['base_path']


def generate_path(device, year, month=None, day=None, time=None):
    if device not in base_path:
        raise ValueError(f"Unknown device: {device}")
    
    templates = base_path[device]

    if device == "まとめ画像(スカイツリー方面)":
        if year and month:
            # print(templates["month"].format(year=year, month=month))
            return templates["month"].format(year=year, month=month)
        elif year and not month:
            return templates["year"].format(year=year)
        else:
            return templates["failed"]
    
    elif device == "壱号機(スカイツリー方面)":
        if month and day and time:
            return templates["month_day_time"].format(year=year, month=month, day=day, time=time)
        elif month and day and not time:
            return templates["month_day"].format(year=year, month=month, day=day)
        elif month and not day and time:
            return templates["month_time"].format(year=year, month=month, time=time)
        elif month and not day and not time:
            return templates["month"].format(year=year, month=month)
        elif not month and day and time:
            return templates["day_time"].format(year=year, day=day, time=time)
        elif not month and day and not time:
            return templates["day"].format(year=year, day=day)
        elif not month and not day and time:
            return templates["time"].format(year=year, time=time)
        else:
            return base_path["failed"]
        
    elif device == "参号機(富士山方面)":
        if month and day and time:
            return templates["month_day_time"].format(year=year, month=month, day=day, time=time)
        elif month and day and not time:
            return templates["month_day"].format(year=year, month=month, day=day)
        elif month and not day and time:
            return templates["month_time"].format(year=year, month=month, time=time)
        elif month and not day and not time:
            return templates["month"].format(year=year, month=month)
        elif not month and day and time:
            return templates["day_time"].format(year=year, day=day, time=time)
        elif not month and day and not time:
            return templates["day"].format(year=year, day=day)
        elif not month and not day and time:
            return templates["time"].format(year=year, time=time)
        else:
            return base_path["failed"]
        
    else:
        return base_path["failed"]


#画像探索とパスの加工(staticsを使っているため)
def search_images(device:str, year:str, month:str = None, day:str = None, time:str =None):
    #画像探索
    search_path = generate_path(device, year, month, day, time)
    images_path = sorted(glob.glob(search_path))
    #画像ファイル名(名前のみ)
    names = [os.path.basename(p) for p in images_path]
    #パスの加工(url用)
    #年のディレクトリまでは消してそれぞれマウントしたところに置き換える
    parts = [required_part.split('/') for required_part in images_path]
    urls = []
    for part_list in parts:
        if part_list[3] == '201':
            urls.append('/skytree_dir/' + os.path.join(*part_list[4:]))
        elif part_list[3] == '203':
            urls.append('/fuji_dir/' + os.path.join(*part_list[4:]))
        elif part_list[3] == 'narabe1':
            urls.append('/matome/' + os.path.join(*part_list[4:]))
        else:
            urls.append(base_path['failed'])
    #nameを利用して画像の時間を調べる
    if parts[0][3] == 'narabe1':
        times = ["不明"] * len(images_path)
    else:
        #time_parts = names.split('_')
        times = [time_part.split('-')[1][:2] + '時' for time_part in names]
    
    return names, urls, times
    
@app.get("/searchImages/", response_model=Searched_images)
def searchImage(type:str, Y:str, m:str = None, d:str = None, H:str = None):
    name, urls, times = search_images(type, Y, m, d, H)
    result = Searched_images(
        name= name,
        urls= urls,
        times= times
    )
    return result



### マニュアル観測結果閲覧ページ
## マニュアル観測時間(都心方向)の撮影画像の取得(fetchImages)
# 観測時間(8:00)の視程画像
@app.get("/morning/vis/image")
def response_morning_vis():
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    day = time.strftime("%d")
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    formatted_date = now.strftime('%Y%m%d-0800')
    path = "/mnt/data/201"
    files = glob.glob(path + f"/{formatted_date}*jpg")
    if not files:
        path = f"/mnt/data/201/{year}/{mon}"
        files = glob.glob(path + f"/{formatted_date}*jpg")
        if not files:
            prev_day = now - timezone(days=1)
            prev_day_str = prev_day.strftime('%Y%m%d-0800')
            files = glob.glob(path + f"/{prev_day_str}*jpg")
            files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
            file_path = files_sorted[0]
            return FileResponse(file_path)
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    if files:
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    return {"error": "No image file found at the specified time."}


# 観測時間(13:00)の視程画像だがnoonとする
@app.get("/noon/vis/image")
def response_noon_vis():
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    day = time.strftime("%d")
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    formatted_date = now.strftime('%Y%m%d-1300')
    path = "/mnt/data/201"
    files = glob.glob(path + f"/{formatted_date}*jpg")
    if not files:
        path = f"/mnt/data/201/{year}/{mon}"
        files = glob.glob(path + f"/{formatted_date}*jpg")
        if not files:
            prev_day = now - timezone(days=1)
            prev_day_str = prev_day.strftime('%Y%m%d-1300')
            files = glob.glob(path + f"/{prev_day_str}*jpg")
            files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
            file_path = files_sorted[0]
            return FileResponse(file_path)
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    if files:
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    return {"error": "No image file found at the specified time."}


# 観測時間(15:00)の視程画像
@app.get("/afternoon/vis/image")
def response_afternoon_vis():
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    day = time.strftime("%d")
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    formatted_date = now.strftime('%Y%m%d-1500')
    path = "/mnt/data/201"
    files = glob.glob(path + f"/{formatted_date}*jpg")
    if not files:
        path = f"/mnt/data/201/{year}/{mon}"
        files = glob.glob(path + f"/{formatted_date}*jpg")
        if not files:
            prev_day = now - timezone(days=1)
            prev_day_str = prev_day.strftime('%Y%m%d-1500')
            files = glob.glob(path + f"/{prev_day_str}*jpg")
            files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
            file_path = files_sorted[0]
            return FileResponse(file_path)
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    if files:
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    return {"error": "No image file found at the specified time."}



## マニュアル観測時間(富士山方向)の撮影画像の取得(fetchImages)
# 観測時間(8:00)の富士山画像
@app.get("/morning/fuji/image")
def response_morning_fuji():
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    day = time.strftime("%d")
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    formatted_date = now.strftime('%Y%m%d-0800')
    path = "/mnt/data/203/bigdata"
    files = glob.glob(path + f"/{formatted_date}*jpg")
    if not files:
        path = f"/mnt/data/203/bigdata/{year}/{mon}"
        files = glob.glob(path + f"/{formatted_date}*jpg")
        if not files:
            prev_day = now - timezone(days=1)
            prev_day_str = prev_day.strftime('%Y%m%d-0800')
            files = glob.glob(path + f"/{prev_day_str}*jpg")
            files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
            file_path = files_sorted[0]
            return FileResponse(file_path)
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    if files:
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    return {"error": "No image file found at the specified time."}


# 観測時間(13:00)の富士山画像
@app.get("/noon/fuji/image")
def response_noon_fuji():
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    day = time.strftime("%d")
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    formatted_date = now.strftime('%Y%m%d-1300')
    path = "/mnt/data/203/bigdata"
    files = glob.glob(path + f"/{formatted_date}*jpg")
    if not files:
        path = f"/mnt/data/203/bigdata/{year}/{mon}"
        files = glob.glob(path + f"/{formatted_date}*jpg")
        if not files:
            prev_day = now - timezone(days=1)
            prev_day_str = prev_day.strftime('%Y%m%d-1300')
            files = glob.glob(path + f"/{prev_day_str}*jpg")
            files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
            file_path = files_sorted[0]
            return FileResponse(file_path)
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    if files:
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    return {"error": "No image file found at the specified time."}


# 観測時間(15:00)の富士山画像
@app.get("/afternoon/fuji/image")
def response_afternoon_fuji():
    year = time.strftime("%Y")
    mon = time.strftime("%m")
    day = time.strftime("%d")
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    formatted_date = now.strftime('%Y%m%d-1500')
    path = "/mnt/data/203/bigdata"
    files = glob.glob(path + f"/{formatted_date}*jpg")
    if not files:
        path = f"/mnt/data/203/bigdata/{year}/{mon}"
        files = glob.glob(path + f"/{formatted_date}*jpg")
        if not files:
            prev_day = now - timezone(days=1)
            prev_day_str = prev_day.strftime('%Y%m%d-1500')
            files = glob.glob(path + f"/{prev_day_str}*jpg")
            files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
            file_path = files_sorted[0]
            return FileResponse(file_path)
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    if files:
        files_sorted = sorted(files, key=lambda x: int(x[-6:-4]))
        file_path = files_sorted[0]
        return FileResponse(file_path)
    return {"error": "No image file found at the specified time."}



## マニュアル観測結果の取得(fetchImages) <- 関数再掲(分割予定)
# Lineに送信されたvisibilityやMt.Fujiの情報
@app.get("/manualReport/vis/info")
def fetch_manual_result():
    db = connect_db("manual")
    query = f"select date, time, weather, flag, class from visibility order by id desc limit 1"
    with db.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()  # fetchone()を使用して単一行を取得
        if row:
            data = {"date": row[0], "time": row[1], "weather": row[2], "Fuji": row[3], "class": row[4]}
        else:
            data = {}  # データがない場合の対応
    return data



#黒点相対数のグラフ用配列
@app.get("/manualReport/sunspot/list")
def fetch_manual_result():
    db = connect_db("manual")
    query = f"select number from sunspot order by id desc limit 30"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        data = [row[0] for row in rows]
    return data
@app.get("/manualReport/sunspot/datelist")
def fetch_manual_sunspot_date():
    db = connect_db("manual")
    query = f"select date from sunspot order by id desc limit 30"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        data = [row[0] for row in rows]
    return data
@app.get("/thesedays/avgTemp")
def these_avgTemp():
    db = connect_db("livee")
    query = f"select temperature from geppo order by date desc limit 30" #平均気温に変える必要ありこれは試作段階
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        data = [row[0] for row in rows]
    return data


##機械判別と目視判別の結果推移並べる用配列   [[[[[試作段階]]]]]
#まずは朝の視程比較グラフ
@app.get("/manualReport/vis/morning/dateList")
def manual_date_morningsList():
    db = connect_db("manual")
    query = f'select date from visibility where time = "8:00" limit 15;'
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        # data = [{"date": row[0], "": row[1]} for row in rows]
        data = [row[0] for row in rows]
    return data
@app.get("/manualReport/vis/morning/classList")
def manual_vis_morningsList():
    db = connect_db("manual")
    query = f'select class from visibility where time = "8:00" limit 15'
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        # data = [{"date": row[0], "": row[1]} for row in rows]
        data = [row[0] for row in rows]
    return data
@app.get("/machine/vis/morning/classes")
def machine_vis_morningsList():
    db = connect_db("1go")
    query = f'select class from visibility where date like "%0800" limit 15'
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        # data = [{"date": row[0], "": row[1]} for row in rows]
        data = [row[0] for row in rows]
    return data

@app.get("/manualReport/sunspot/info")
def fetch_manual_result():
    # 最新の黒点画像を取得
    sunspot_path = "/mnt/data/sunspot"
    files = glob.glob(f"{sunspot_path}/*/*/*.png")
    if not files:
        return JSONResponse(content={"error": "No image files found"}, status_code=404)

    # ファイル名でソートして最新の画像を選択
    files_sorted = sorted(files, key=lambda x: os.path.basename(x)[:8])
    latest_file_path = files_sorted[-1]
    file_name = os.path.basename(latest_file_path)

    # ファイル名から日付情報を抽出
    formatted_time = file_name[:8]  
    year = formatted_time[:4]
    mon = formatted_time[4:6]
    hour = formatted_time[6:8]
    date_str = f"{year}/{mon}/{hour}"

    # 輪郭画像のパスと面積を抽出
    contour_path_dir = f"/mnt/data/sunspot/{year}/{mon}/contoured_images"
    contour_file_name = f"{file_name[:-4]}_*_contour.png"  
    contour_files = glob.glob(os.path.join(contour_path_dir, contour_file_name))
    if not contour_files:
        return JSONResponse(content={"error": "Contour image not found", "filename":file_name}, status_code=404)

    # 最新の輪郭画像を選択
    contour_file_path = sorted(contour_files, key=lambda x: os.path.basename(x)[:8])[-1]
    contour_file_name = os.path.basename(contour_file_path)

    # 輪郭画像のファイル名から面積を抽出
    try:
        total_area = float(contour_file_name.split("_")[1])
    except (IndexError, ValueError):
        total_area = 0  # 面積が取得できない場合のデフォルト値

    # レスポンスを返す
    return JSONResponse(content={
        "date": date_str,
        "image_url": f"/sunspot/image/{file_name}",
        "contour_image_url": f"/sunspot/contour_image/{contour_file_name}",
        "total_area": total_area
    })

@app.get("/sunspot/image/{file_name}")
def get_sunspot_image(file_name: str):
    year = file_name[:4]
    month = file_name[4:6]
    file_path = f"/mnt/data/sunspot/{year}/{month}/masked_images/{file_name}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path, media_type="image/png")


@app.get("/latest/temper")
def get_latestTemper():
    db = connect_db("livee")
    query = "select date, temperature from geppo where date like '%0:00' order by date desc limit 42"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
    
    formatted = []
    for row in rows:
        formatted_time = row[0].strftime('%H:%M')
        per = [formatted_time, row[1]]
        formatted.append(per)

    return formatted
@app.get("/latest/humidity")
def get_latestTemper():
    db = connect_db("livee")
    query = "select date, humidity from geppo where date like '%0:00' order by date desc limit 42"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    formatted = []
    for row in rows:
        formatted_time = row[0].strftime('%H:%M')
        per = [formatted_time, row[1]]
        formatted.append(per)

    return formatted
@app.get("/latest/pressure")
def get_latestTemper():
    db = connect_db("livee")
    query = "select date, pressure from geppo where date like '%0:00' order by date desc limit 42"
    with db.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
    
    formatted = []
    for row in rows:
        formatted_time = row[0].strftime('%H:%M')
        per = [formatted_time, row[1]]
        formatted.append(per)

    return formatted





### 過去観測資料検索閲覧ページ('/past')
## 過去観測資料の検索
#folderIDの取得

credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
print(f"Checking credentials path: {credentials_path}")

if not os.path.exists(credentials_path):
    print("Error: credentials.json does not exist at the expected location!")

SCOPES = ['https://www.googleapis.com/auth/drive']

credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
sa_creds = service_account.Credentials.from_service_account_file(credentials_path)
scoped_creds = sa_creds.with_scopes(SCOPES)
drive_service = build('drive', 'v3', credentials=scoped_creds)
        
def list_files(folder_id):
    results = []
    query = f"'{folder_id[0]}' in parents and trashed = false"
    
    response = drive_service.files().list(
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        q=query,
        fields="files(id, name)"
    ).execute()

    files = response.get('files', [])

    for file in files:
        results.append(file)

    return results

@app.get("/folderID/{kind}/{year}/{month}")
def get_imageIDs(kind: str, year: str, month: str):
    db = connect_db("google")
    cursor = db.cursor()
    months = f"{year}{month}"
    query = f"SELECT folder_id from {kind} where month like '{months}%'"
    cursor.execute(query)
    result = cursor.fetchall()
    folder_ids = [row[0] for row in result]
    file_ids = list_files(folder_ids)
    response_data = {"year": year, "month": month, "files": file_ids}
    return response_data



### 試作やtestなど
# @app.post("/searchImages_demo")
# def serachImage_demo(equipment: str, yy: str = this_year, month: str = this_month, day: str = today, time: str = now):
#     device = equipments[equipment]
@app.post(
    "/{device}/latest_image",
    responses={200: {"content": {"image/jpeg"}}},
    response_class=Response
)
def fetch_latest_image(device: str) -> Response:
    def get_biggest_img(folder_captures: Dict[str, int]):
        latest_img_list = []
        date = datetime.today().strftime("%Y/%m")
        for folder, captures in folder_captures.items():
            root = f"/mnt/data/{deviceNameToId[device]}/{folder}/{date}"
            images = [e for e in os.listdir[root] if e.endswith(".jpg")]
            
            for img_name in sorted(images, reverse=True)[0:captures]:
                latest_img_list.append(f"{root}/{img_name}")
        sorted_images = sorted(latest_img_list, key=lambda path: os.path.getsize(path))
        return sorted_images[-1]
    
    if device not in available_devices:
        raise HTTPException(status_code=404, detail={"message": "device not found"})
    if device == "1go":
        biggest_img = get_biggest_img({"": 3})
    elif device == "2go":
        biggest_img = get_biggest_img({"jpg": 1})
    elif device == "3go":
        biggest_img = get_biggest_img({"bigdata": 5, "sunset": 1, "night": 1})
    else:
        raise HTTPException(status_code=404, detail={"message": "device not found"})

    with open(biggest_img, "rb") as f:
        img = f.read()
    return Response(content=img, media_type="image/jpeg")  


@app.post("/test")
def read_root():
    return {"Hello": "World"}
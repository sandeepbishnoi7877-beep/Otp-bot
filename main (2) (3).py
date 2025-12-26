#!/usr/bin/env python3

import requests

import time

import re

import sys

import signal

import sqlite3

import threading

import hashlib

from datetime import datetime

# ================= CONFIG =================

BASE_URL = "http://51.89.99.105/NumberPanel"

LOGIN_POST_URL = f"{BASE_URL}/signin"

USERNAME = "Rakesh7799"

PASSWORD = "ck787723"

API_URL = f"{BASE_URL}/agent/res/data_smscdr.php"

BOT_TOKEN = "7831990068:AAH7i2jjIBafP9iaXqX8KHorrIh30eMQtVs"

CHAT_ID = "-1003457853242"

REFRESH = 20

DB_FILE = "sms.db"

# ========================================

stop_event = threading.Event()

sent_hashes = set()

# ================= DB ====================

def db_init():

    global sent_hashes

    conn = sqlite3.connect(DB_FILE)

    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS sent (h TEXT PRIMARY KEY)")

    conn.commit()

    cur.execute("SELECT h FROM sent")

    sent_hashes = {x[0] for x in cur.fetchall()}

    conn.close()

    print(f"[DB] Loaded {len(sent_hashes)} hashes")

def db_add(h):

    conn = sqlite3.connect(DB_FILE)

    with conn:

        conn.execute("INSERT OR IGNORE INTO sent VALUES (?)", (h,))

    conn.close()

# =============== TELEGRAM =================

def tg_send(text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:

        requests.post(url, json={

            "chat_id": CHAT_ID,

            "text": text,

            "parse_mode": "HTML"

        }, timeout=15)

        print("✅ Sent")

    except:

        pass

# =============== UTILS ====================

def otp_extract(msg):

    m = re.findall(r"\b\d{4,8}\b", msg or "")

    return m[0] if m else "N/A"

def mask(num):

    s = re.sub(r"\D", "", str(num))

    return "xxxxx" + s[-4:] if len(s) > 4 else s

# =============== LOGIN ====================

def login(session):

    print("[LOGIN] Sending credentials")

    payload = {

        "username": USERNAME,

        "password": PASSWORD

    }

    r = session.post(LOGIN_POST_URL, data=payload, timeout=20)

    return r.status_code == 200

# =============== WATCH ====================

def watch(session):

    while not stop_event.is_set():

        try:

            now = datetime.now()

            r = session.get(API_URL, params={

                "fdate1": now.strftime("%Y-%m-%d 00:00:00"),

                "fdate2": now.strftime("%Y-%m-%d %H:%M:%S")

            }, timeout=30)

            try:

                data = r.json()

            except:

                time.sleep(10)

                continue

            for row in data.get("aaData", []):

                dt, num, plat, msg = row[0], row[2], row[3], row[5]

                h = hashlib.md5(f"{dt}|{num}|{msg}".encode()).hexdigest()

                if h in sent_hashes:

                    continue

                otp = otp_extract(msg)

                text = (

                    f"<b>📱 {mask(num)}</b>\n"

                    f"<b>🌐 {plat}</b>\n"

                    f"<b>🔐 OTP:</b> <code>{otp}</code>"

                )

                tg_send(text)

                db_add(h)

                sent_hashes.add(h)

        except Exception as e:

            print("[ERROR]", e)

            time.sleep(15)

        time.sleep(REFRESH)

# ============== HEARTBEAT =================

def heartbeat():

    while True:

        print("[HB] Alive")

        time.sleep(300)

# ================ MAIN ====================

def main():

    print("=== OTP BOT START ===")

    db_init()

    threading.Thread(target=heartbeat, daemon=True).start()

    session = requests.Session()

    if not login(session):

        print("[LOGIN] Failed, retry in 60s")

        time.sleep(60)

        return main()

    print("[LOGIN] Success")

    tg_send("✅ OTP Bot Started")

    watch(session)

# ============== SIGNAL ====================

signal.signal(signal.SIGINT, lambda a,b: sys.exit(0))

signal.signal(signal.SIGTERM, lambda a,b: sys.exit(0))

if __name__ == "__main__":

    main()
import requests
import pymysql
import json
import random
import time
from time import sleep

# ==== 1. 配置 ====
COOKIE = "请使用你的COOKIE"
AID = "560964992"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Cookie": COOKIE
}

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123456",   #你的密码
    "charset": "utf8mb4"
}


# ==== 2. 初始化 MySQL ====
def init_mysql():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("CREATE DATABASE IF NOT EXISTS bilibili CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
    conn.select_db("bilibili")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        rpid BIGINT PRIMARY KEY,    -- 评论唯一ID
        mid BIGINT,                 -- 用户ID
        uname VARCHAR(255),         -- 用户名
        message TEXT,               -- 评论内容
        like_count INT,             -- 点赞数
        ctime DATETIME              -- 评论时间
    );
    """)
    conn.commit()
    print("数据库和数据表已初始化")
    return conn


# ==== 3. 获取 / 保存上次页码 ====
def get_last_page():
    try:
        with open("last_page.txt", "r") as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return 1


def save_last_page(page):
    with open("last_page.txt", "w") as f:
        f.write(str(page))


# ==== 4. 爬取评论 ====
def fetch_comments(page):
    url = f"https://api.bilibili.com/x/v2/reply/main?jsonp=jsonp&next={page}&type=1&oid={AID}&mode=3&plat=1"

    # 自动重试机制
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            print(f"状态码: {resp.status_code}")  #  新增
            print(resp.text[:300])
            data = resp.json()
            break
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"第 {page} 页请求失败 ({attempt + 1}/3)：{e}")
            sleep(2 + attempt * 2)
    else:
        print(f"第 {page} 页连续失败3次，跳过。")
        return []

    if data.get("code") != 0:
        print(f" 接口返回错误：code={data.get('code')} message={data.get('message')}")
        return []

    replies = data.get("data", {}).get("replies", [])
    if not replies:
        print(f" 第 {page} 页无评论，可能是最后一页。")
        return []

    comments = []
    for r in replies:
        comments.append({
            "rpid": r["rpid"],
            "mid": r["member"]["mid"],
            "uname": r["member"]["uname"],
            "message": r["content"]["message"],
            "like_count": r["like"],
            "ctime": r["ctime"]
        })
    print(f" 第 {page} 页成功获取 {len(comments)} 条评论")
    return comments


# ==== 5. 保存到数据库 ====
def save_to_mysql(conn, comments):
    cursor = conn.cursor()
    sql = """
    INSERT INTO comments (rpid, mid, uname, message, like_count, ctime)
    VALUES (%s, %s, %s, %s, %s, FROM_UNIXTIME(%s))
    ON DUPLICATE KEY UPDATE like_count=VALUES(like_count), message=VALUES(message);
    """
    for c in comments:
        cursor.execute(sql, (
            c["rpid"], c["mid"], c["uname"], c["message"], c["like_count"], c["ctime"]
        ))
    conn.commit()
    print(f" 已保存 {len(comments)} 条评论")


# ==== 6. 主函数 ====
def main():
    conn = init_mysql()
    start_page = get_last_page()
    print(f" 从第 {start_page} 页开始爬取")

    all_comments = []
    page = start_page

    while True:
        comments = fetch_comments(page)
        if not comments:
            print(" 爬取结束。")
            break

        save_to_mysql(conn, comments)
        save_last_page(page)
        all_comments.extend(comments)

        # 随机暂停 2~5 秒防止被封
        sleep_time = random.uniform(2, 5)
        print(f" 暂停 {sleep_time:.2f} 秒防反爬")
        sleep(sleep_time)

        page += 1

    conn.close()
    print(f" 总共获取 {len(all_comments)} 条评论")


if __name__ == "__main__":
    main()

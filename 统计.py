# 文件：统计.py
import pymysql
import torch
from transformers import BertTokenizer, BertForSequenceClassification
from collections import Counter

# === 1. 模型加载 ===
MODEL_PATH = r"C:\Users\Administrator\PycharmProjects\PythonProject2\models\jigndong"

print("正在加载模型，请稍候...")
tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
model = BertForSequenceClassification.from_pretrained(MODEL_PATH)
model.eval()
print(" 模型加载成功")


# === 2. 读取数据库中的所有评论 ===
def load_comments():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="123456",
        database="bilibili",
        charset="utf8mb4"
    )
    cursor = conn.cursor()

    cursor.execute("SELECT message FROM comments WHERE message IS NOT NULL AND message != ''")
    results = cursor.fetchall()

    conn.close()

    comments = [r[0] for r in results]
    print(f" 已读取 {len(comments)} 条评论")
    return comments


# === 3. 情感预测函数 ===
def predict_sentiment(texts):
    sentiments = []

    for text in texts:
        inputs = tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors="pt"
        )
        with torch.no_grad():
            outputs = model(**inputs)
            scores = torch.softmax(outputs.logits, dim=1)
            label = torch.argmax(scores, dim=1).item()
        sentiments.append(label)

    return sentiments


# === 4. 主程序 ===
if __name__ == "__main__":
    comments = load_comments()
    if not comments:
        print(" 没有读取到评论，请检查数据库。")
        exit()

    sentiments = predict_sentiment(comments)

    # === 5. 统计情感比例 ===
    counter = Counter(sentiments)
    total = len(sentiments)

    pos = counter.get(1, 0)
    neg = counter.get(0, 0)
    neu = counter.get(2, 0)  # 如果模型有三分类，这里会自动适配

    print("\n===  评论情感统计结果 ===")
    print(f"总评论数：{total}")
    print(f"正面评价：{pos} 条 ({pos/total:.2%})")
    print(f"负面评价：{neg} 条 ({neg/total:.2%})")
    if neu:
        print(f"中性评价：{neu} 条 ({neu/total:.2%})")

    print("\n示例输出前5条评论：")
    for i in range(min(5, total)):
        label = sentiments[i]
        sentiment_str = "好评" if label == 1 else ("差评" if label == 0 else "中性")
        print(f"[{sentiment_str}] {comments[i]}")

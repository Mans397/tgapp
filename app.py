# site/app.py
import os
import logging
import psycopg2
from flask import Flask, send_from_directory, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "postgress_84r8"),
    "user": os.environ.get("DB_USER", "postgress"),
    "password": os.environ.get("DB_PASSWORD", "WhOroBljONgc6B0R60GgeMyUjXaKBL0v"),
    "host": os.environ.get("DB_HOST", "dpg-cv6u5qd6l47c73dbtbrg-a.oregon-postgres.render.com"),
    "port": os.environ.get("DB_PORT", "5432"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# Простая инициализация БД (создание таблиц, если их нет).
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                points INTEGER DEFAULT 0,
                first_name TEXT,
                last_name TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS merch (
                id SERIAL PRIMARY KEY,
                name TEXT,
                cost INTEGER,
                stock INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                merch_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()

@app.route("/")
def index():
    """
    Отдаём статический index.html, лежащий в папке ./static.
    """
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def static_files(path):
    """
    Любые другие файлы из ./static (CSS, JS, картинки).
    """
    return send_from_directory("static", path)

@app.route("/api/items", methods=["GET"])
def get_items():
    """
    Возвращает список товаров (мерча).
    """
    items = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, cost, stock FROM merch ORDER BY id ASC")
            for row in cur.fetchall():
                items.append({
                    "id": row[0],
                    "name": row[1],
                    "cost": row[2],
                    "stock": row[3]
                })
    return jsonify(items)

@app.route("/api/buy", methods=["POST"])
def buy_item():
    """
    Принимает JSON: { "user_id": 123, "item_id": 1 }
    Проверяет баллы, уменьшает stock, записывает в purchases.
    Возвращает JSON с результатом.
    """
    data = request.get_json()
    user_id = data.get("user_id")
    item_id = data.get("item_id")

    # 1. Проверяем товар
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, cost, stock FROM merch WHERE id=%s", (item_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "message": "Товар не найден"}), 404

            merch_id, name, cost, stock = row
            if stock <= 0:
                return jsonify({"success": False, "message": "Товар закончился"}), 400

            # 2. Проверяем баллы пользователя
            cur.execute("SELECT points FROM users WHERE user_id=%s", (user_id,))
            user_row = cur.fetchone()
            points = user_row[0] if user_row else 0

            if points < cost:
                return jsonify({"success": False, "message": f"Недостаточно баллов ({points}/{cost})"}), 400

            # 3. Списываем баллы
            new_points = points - cost
            # обновим запись в users
            cur.execute("""
                UPDATE users SET points=%s WHERE user_id=%s
            """, (new_points, user_id))

            # 4. Уменьшим stock на 1
            new_stock = stock - 1
            cur.execute("UPDATE merch SET stock=%s WHERE id=%s", (new_stock, merch_id))

            # 5. Запишем покупку
            cur.execute("INSERT INTO purchases (user_id, merch_id) VALUES (%s, %s)",
                        (user_id, merch_id))

        conn.commit()

    return jsonify({
        "success": True,
        "message": f"Покупка '{name}' за {cost} баллов успешна!",
        "new_stock": new_stock,
        "new_points": new_points
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
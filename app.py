# site/app.py
import os
import logging
import psycopg2
import random
import string
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
    """Создаёт подключение к PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    """
    Создаёт (при необходимости) таблицы:
      - users (user_id BIGINT, points)
      - merch (товары)
      - purchases (покупки) + purchase_code
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Таблица users
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    points INTEGER DEFAULT 0
                )
            """)

            # Таблица merch
            cur.execute("""
                CREATE TABLE IF NOT EXISTS merch (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    cost INTEGER,
                    stock INTEGER,
                    image_url TEXT DEFAULT ''
                )
            """)

            # Таблица purchases
            cur.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    merch_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    purchase_code TEXT,
                    purchase_url TEXT
                )
            """)
            # Уникальный индекс на purchase_code
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_code
                ON purchases(purchase_code)
            """)
        conn.commit()

def generate_code(length=8):
    """Генерируем случайный код из A-Z0-9."""
    import string, random
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Инициализируем базу при старте
init_db()

@app.route("/")
def index():
    """Отдаём статический index.html из ./static."""
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def static_files(path):
    """Раздаём статические файлы (CSS, JS, etc.) из ./static."""
    return send_from_directory("static", path)

@app.route("/api/items", methods=["GET"])
def get_items():
    """
    Возвращает список товаров (мерча) в JSON:
    [
      { "id": ..., "name": "...", "cost": ..., "stock": ..., "image_url": "..." },
      ...
    ]
    """
    items = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, cost, stock, image_url FROM merch ORDER BY id ASC")
            for row in cur.fetchall():
                items.append({
                    "id": row[0],
                    "name": row[1],
                    "cost": row[2],
                    "stock": row[3],
                    "image_url": row[4] or ""
                })
    return jsonify(items)

@app.route("/api/buy", methods=["POST"])
def buy_item():
    """
    Принимает JSON: { "user_id": 123, "item_id": 1 }.
    1) Проверяет товар (stock, cost)
    2) Проверяет баллы пользователя
    3) Списывает баллы, уменьшает stock
    4) Записывает purchase с уникальным purchase_code
    5) Возвращает JSON: { success, message, purchase_code }
    """
    data = request.get_json()
    user_id = data.get("user_id")
    item_id = data.get("item_id")

    if not user_id or not item_id:
        return jsonify({"success": False, "message": "user_id / item_id отсутствуют"}), 400

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Товар
            cur.execute("SELECT id, name, cost, stock FROM merch WHERE id=%s", (item_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "message": "Товар не найден"}), 404

            merch_id, name, cost, stock = row
            if stock <= 0:
                return jsonify({"success": False, "message": "Товар закончился"}), 400

            # 2. Проверяем баллы
            cur.execute("SELECT points FROM users WHERE user_id=%s", (user_id,))
            row_user = cur.fetchone()
            points = row_user[0] if row_user else 0

            if points < cost:
                return jsonify({
                    "success": False,
                    "message": f"Недостаточно баллов (у вас {points}, нужно {cost})."
                }), 400

            # 3. Списываем баллы
            new_points = points - cost
            cur.execute("""
                INSERT INTO users (user_id, points) VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET points = EXCLUDED.points
            """, (user_id, new_points))

            # 4. stock--
            new_stock = stock - 1
            cur.execute("UPDATE merch SET stock=%s WHERE id=%s", (new_stock, merch_id))

            # 5. purchase_code
            code = generate_code(8)
            url = f"https://tgapp-fml5.onrender.com/ticket/{code}"
            cur.execute("""
                INSERT INTO purchases (user_id, merch_id, purchase_code, purchase_url)
                VALUES (%s, %s, %s, %s)
                RETURNING id, timestamp
            """, (user_id, merch_id, code, url))
            purchase_row = cur.fetchone()
            purchase_id = purchase_row[0]
            purchase_time = purchase_row[1]

        conn.commit()

    return jsonify({
        "success": True,
        "message": f"Товар «{name}» куплен за {cost} баллов!",
        "purchase_code": code,
        "new_stock": new_stock,
        "new_points": new_points
    })

@app.route("/ticket/<purchase_code>")
def view_ticket(purchase_code):
    """
    Страница-подтверждение для кода purchase_code.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.timestamp, p.user_id,
                       m.name as merch_name, m.cost
                FROM purchases p
                LEFT JOIN merch m ON p.merch_id = m.id
                WHERE p.purchase_code=%s
            """, (purchase_code,))
            row = cur.fetchone()
            if not row:
                return f"<h1>Код {purchase_code} не найден.</h1>", 404

            p_id, p_timestamp, p_userid, merch_name, merch_cost = row

    html = f"""
    <html>
    <head>
      <title>Ticket #{purchase_code}</title>
      <style>
        body {{
          font-family: sans-serif;
          margin: 0; padding: 0;
          background: #f0f0f0;
        }}
        .ticket {{
          max-width: 600px;
          margin: 50px auto;
          background: #fff;
          padding: 20px;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        h1 {{
          margin-top: 0;
        }}
        .info p {{
          margin: 5px 0;
        }}
      </style>
    </head>
    <body>
      <div class="ticket">
        <h1>Подтверждение покупки</h1>
        <div class="info">
          <p><b>Код:</b> {purchase_code}</p>
          <p><b>Товар:</b> {merch_name} (стоимость {merch_cost} баллов)</p>
          <p><b>Дата:</b> {p_timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
          <p><b>Покупатель (user_id):</b> {p_userid}</p>
        </div>
      </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


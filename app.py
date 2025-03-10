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
    """Возвращает новое подключение к PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    """
    Создаем (при необходимости) таблицы и поля.
    Добавляем поле purchase_code в purchases, если его нет.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Таблица users
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    first_name TEXT,
                    last_name TEXT
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
                    purchase_code TEXT
                )
            """)
            # Уникальный индекс на purchase_code (если нужно)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_code 
                ON purchases(purchase_code)
            """)
        conn.commit()

def generate_code(length=8):
    """Генерирует случайный код из заглавных букв и цифр."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Инициализируем БД при старте
init_db()

@app.route("/")
def index():
    """
    Отдаём статический index.html, лежащий в ./static (главная страница).
    """
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def static_files(path):
    """
    Любые другие файлы из ./static (CSS, JS, картинки, etc.).
    """
    return send_from_directory("static", path)

@app.route("/api/items", methods=["GET"])
def get_items():
    """
    Возвращает список товаров (мерча):
    [
      {id, name, cost, stock, image_url}, ...
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
    Принимает JSON: { "user_id": 123, "item_id": 1 }
    Проверяет баллы, уменьшает stock, записывает в purchases + генерирует purchase_code.
    Возвращает JSON с результатом и purchase_code.
    """
    data = request.get_json()
    user_id = data.get("user_id")
    item_id = data.get("item_id")

    if not user_id or not item_id:
        return jsonify({"success": False, "message": "Invalid parameters"}), 400

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Ищем товар
            cur.execute("SELECT id, name, cost, stock FROM merch WHERE id=%s", (item_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "message": "Товар не найден"}), 404

            merch_id, name, cost, stock = row
            if stock <= 0:
                return jsonify({"success": False, "message": "Товар закончился"}), 400

            # 2. Проверяем баллы пользователя (по умолчанию 0)
            cur.execute("SELECT points FROM users WHERE user_id=%s", (user_id,))
            user_row = cur.fetchone()
            points = user_row[0] if user_row else 0

            if points < cost:
                return jsonify({
                    "success": False,
                    "message": f"Недостаточно баллов (у вас {points}, нужно {cost})."
                }), 400

            # 3. Списываем баллы:
            new_points = points - cost
            # Если пользователя нет - вставим, иначе обновим
            cur.execute("""
                INSERT INTO users (user_id, points) VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET points = EXCLUDED.points
            """, (user_id, new_points))

            # 4. Уменьшим stock на 1
            new_stock = stock - 1
            cur.execute("UPDATE merch SET stock=%s WHERE id=%s", (new_stock, merch_id))

            # 5. Генерируем purchase_code (8 символов, уникальный)
            purchase_code = generate_code(8)
            # Вставляем запись в purchases
            cur.execute("""
                INSERT INTO purchases (user_id, merch_id, purchase_code)
                VALUES (%s, %s, %s)
                RETURNING id, timestamp
            """, (user_id, merch_id, purchase_code))
            purchase_row = cur.fetchone()
            purchase_id = purchase_row[0]
            timestamp = purchase_row[1]

        conn.commit()

    return jsonify({
        "success": True,
        "message": f"Вы успешно купили «{name}» за {cost} баллов!",
        "new_stock": new_stock,
        "new_points": new_points,
        "purchase_code": purchase_code
    })

@app.route("/ticket/<purchase_code>")
def view_ticket(purchase_code):
    """
    Страница, где можно увидеть детали покупки по коду.
    Можно показать руководству, чтобы они проверили реальность покупки.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.timestamp, p.user_id,
                       m.name as merch_name, m.cost,
                       u.first_name, u.last_name
                FROM purchases p
                LEFT JOIN merch m ON p.merch_id = m.id
                LEFT JOIN users u ON p.user_id = u.user_id
                WHERE p.purchase_code = %s
            """, (purchase_code,))
            row = cur.fetchone()
            if not row:
                return f"<h1>Код «{purchase_code}» не найден.</h1>", 404

            (p_id, p_timestamp, p_userid, merch_name, merch_cost, first_name, last_name) = row

    full_name = ((first_name or "") + " " + (last_name or "")).strip()

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
          <p><b>Покупатель (user_id):</b> {p_userid} {'('+full_name+')' if full_name else ''}</p>
        </div>
      </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
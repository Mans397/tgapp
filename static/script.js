function getQueryParams() {
    // Простейшая функция парсинга URL: ?uid=123&other=...
    const params = {};
    const query = window.location.search;
    if (query.startsWith("?")) {
        const pairs = query.substring(1).split("&");
        for (const pair of pairs) {
            const [key, val] = pair.split("=");
            params[decodeURIComponent(key)] = decodeURIComponent(val);
        }
    }
    return params;
}

document.addEventListener("DOMContentLoaded", () => {
    const userInfoElem = document.getElementById("user-info");
    const itemsDiv = document.getElementById("items");

    // 1. Определяем user_id из ?uid=
    const queryParams = getQueryParams();
    const userId = queryParams.uid;

    if (!userId) {
        userInfoElem.textContent = "Не задан ?uid=..., откройте ссылку из бота!";
        itemsDiv.innerHTML = "<p>Невозможно загрузить товары без user_id</p>";
        return;
    }

    userInfoElem.textContent = `Ваш user_id: ${userId}`;

    // 2. Загружаем товары
    async function loadItems() {
        itemsDiv.innerHTML = "Загружаем товары...";
        try {
            const resp = await fetch("/api/items");
            const items = await resp.json();
            if (!Array.isArray(items)) {
                throw new Error("Неверный формат /api/items");
            }
            renderItems(items);
        } catch (err) {
            itemsDiv.innerHTML = `Ошибка: ${err.message}`;
        }
    }

    // 3. Отрисуем товары
    function renderItems(items) {
        if (items.length === 0) {
            itemsDiv.innerHTML = "Нет товаров";
            return;
        }
        itemsDiv.innerHTML = "";

        items.forEach(item => {
            const div = document.createElement("div");
            div.className = "card";
            div.innerHTML = `
        <img src="${item.image_url}" alt="${item.name}" class="card-image" 
             onerror="this.src='https://via.placeholder.com/200?text=No+Image'"/>
        <h2 class="card-title">${item.name}</h2>
        <p class="card-cost">Цена: ${item.cost} баллов</p>
        <p class="card-stock">Осталось: ${item.stock}</p>
        <button class="buy-btn" data-id="${item.id}">Купить</button>
      `;
            itemsDiv.appendChild(div);
        });
    }

    // 4. Обработчик «Купить»
    itemsDiv.addEventListener("click", async (e) => {
        if (e.target.classList.contains("buy-btn")) {
            const itemId = parseInt(e.target.dataset.id, 10);
            try {
                const resp = await fetch("/api/buy", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ user_id: userId, item_id: itemId })
                });
                const result = await resp.json();
                if (result.success) {
                    alert(
                        `${result.message}\n` +
                        `Код покупки: ${result.purchase_code}\n` +
                        `Ссылка: ${window.location.origin}/ticket/${result.purchase_code}`
                    );
                } else {
                    alert(`Ошибка: ${result.message}`);
                }
                // Перезагрузить товары
                loadItems();
            } catch (error) {
                alert("Ошибка запроса: " + error.message);
            }
        }
    });

    // 5. При загрузке страницы сразу загрузим список товаров
    loadItems();
});
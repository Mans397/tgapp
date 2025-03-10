// static/script.js

document.addEventListener("DOMContentLoaded", () => {
    const tg = window.Telegram?.WebApp;
    let userId = null;

    const userInfoElem = document.getElementById("user-info");
    const itemsDiv = document.getElementById("items");

    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        // Открыто внутри Telegram WebApp
        userId = tg.initDataUnsafe.user.id;
        console.log("Определён user_id из Telegram WebApp:", userId);
        userInfoElem.textContent = `Your Telegram user_id: ${userId}`;
    } else {
        // Не в Телеграме
        userInfoElem.textContent = "Пожалуйста, откройте мини-приложение через команду /webshop в боте.";
        itemsDiv.innerHTML = "<p>Товары не загружаются вне Telegram WebApp.</p>";
        return;
    }

    // Если хотим развернуть на весь экран
    tg.expand();

    // Функция загрузки товаров
    async function loadItems() {
        itemsDiv.innerHTML = "<p>Загружаем товары...</p>";
        try {
            const resp = await fetch("/api/items");
            const items = await resp.json();
            if (!Array.isArray(items)) {
                throw new Error("Неправильный формат /api/items");
            }
            renderItems(items);
        } catch (err) {
            itemsDiv.innerHTML = `<p>Ошибка при загрузке: ${err.message}</p>`;
        }
    }

    function renderItems(items) {
        if (items.length === 0) {
            itemsDiv.innerHTML = "<p>Нет товаров</p>";
            return;
        }
        itemsDiv.innerHTML = ""; // очистим

        items.forEach(item => {
            const card = document.createElement("div");
            card.className = "card";

            card.innerHTML = `
        <img src="${item.image_url}" alt="${item.name}" class="card-image" 
             onerror="this.src='https://via.placeholder.com/200?text=No+Image';"/>
        <h2 class="card-title">${item.name}</h2>
        <p class="card-cost">Цена: ${item.cost} баллов</p>
        <p class="card-stock">Осталось: ${item.stock}</p>
        <button class="buy-btn" data-id="${item.id}">Купить</button>
      `;
            itemsDiv.appendChild(card);
        });
    }

    itemsDiv.addEventListener("click", async (e) => {
        if (e.target.classList.contains("buy-btn")) {
            const itemId = parseInt(e.target.dataset.id, 10);
            try {
                const resp = await fetch("/api/buy", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        user_id: userId,
                        item_id: itemId
                    })
                });
                const result = await resp.json();
                if (result.success) {
                    // Покажем код
                    alert(
                        `${result.message}\n\n` +
                        `Код покупки: ${result.purchase_code}\n` +
                        `Ссылка: ${window.location.origin}/ticket/${result.purchase_code}`
                    );
                } else {
                    alert(`Ошибка: ${result.message}`);
                }
                // Перезагрузим товары
                loadItems();
            } catch (error) {
                alert("Сетевая ошибка: " + error.message);
            }
        }
    });

    // При первом рендере сразу грузим товары
    loadItems();
});
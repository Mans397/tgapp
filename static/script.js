document.addEventListener("DOMContentLoaded", () => {
    // 1. Получаем/генерируем user_id (храним в localStorage)
    let userId = localStorage.getItem("user_id");
    if (!userId) {
        userId = Math.floor(1000 + Math.random() * 9000); // 4-значное
        localStorage.setItem("user_id", userId);
    }

    const userInfo = document.getElementById("user-info");
    userInfo.textContent = `Your user_id: ${userId}`;

    const itemsDiv = document.getElementById("items");

    // 2. Загружаем товары
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

    // 3. Рендер товаров
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

    // 4. При клике «Купить»
    itemsDiv.addEventListener("click", async (e) => {
        if (e.target.classList.contains("buy-btn")) {
            const itemId = parseInt(e.target.dataset.id, 10);
            try {
                const resp = await fetch("/api/buy", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        user_id: parseInt(userId),
                        item_id: itemId
                    })
                });
                const result = await resp.json();
                if (result.success) {
                    // Покажем код
                    alert(`${result.message}\n\nВаш код: ${result.purchase_code}\n\nСсылка: ${window.location.origin}/ticket/${result.purchase_code}`);
                } else {
                    alert(`Ошибка: ${result.message}`);
                }
                // Перезагружаем товары
                loadItems();
            } catch (error) {
                alert("Сетевая ошибка: " + error.message);
            }
        }
    });

    // 5. При загрузке страницы сразу тянем товары
    loadItems();
});
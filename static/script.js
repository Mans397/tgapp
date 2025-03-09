document.addEventListener("DOMContentLoaded", () => {
    const loadBtn = document.getElementById("loadBtn");
    const itemsDiv = document.getElementById("items");
    const userIdInput = document.getElementById("userIdInput");

    loadBtn.addEventListener("click", async () => {
        itemsDiv.innerHTML = "Загружаем...";
        const resp = await fetch("/api/items");
        const items = await resp.json();
        itemsDiv.innerHTML = "";

        items.forEach(item => {
            const div = document.createElement("div");
            div.className = "item";
            div.innerHTML = `
        <h2>${item.name}</h2>
        <p>Цена: ${item.cost} баллов</p>
        <p>Осталось: ${item.stock}</p>
        <button data-id="${item.id}" class="buyBtn">Купить</button>
      `;
            itemsDiv.appendChild(div);
        });
    });

    itemsDiv.addEventListener("click", async (e) => {
        if (e.target.classList.contains("buyBtn")) {
            const itemId = e.target.dataset.id;
            const userId = userIdInput.value; // забрали user_id из поля
            const resp = await fetch("/api/buy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, item_id: parseInt(itemId) })
            });
            const result = await resp.json();
            if (result.success) {
                alert("Успешная покупка!");
            } else {
                alert("Ошибка: " + result.message);
            }
            // перезагрузим товары
            loadBtn.click();
        }
    });
});
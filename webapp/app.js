const tg = window.Telegram && window.Telegram.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
  if (tg.setHeaderColor) {
    try { tg.setHeaderColor("secondary_bg_color"); } catch (e) { /* older clients */ }
  }
}

const initData = tg ? tg.initData : "";

const els = {
  loading: document.getElementById("loading"),
  empty: document.getElementById("empty"),
  list: document.getElementById("list"),
  countPill: document.getElementById("count-pill"),
};

function haptic(kind) {
  if (tg && tg.HapticFeedback) {
    if (kind === "success" || kind === "error" || kind === "warning") {
      tg.HapticFeedback.notificationOccurred(kind);
    } else {
      tg.HapticFeedback.impactOccurred(kind || "light");
    }
  }
}

function showState(state) {
  els.loading.classList.toggle("hidden", state !== "loading");
  els.empty.classList.toggle("hidden", state !== "empty");
  els.list.classList.toggle("hidden", state !== "list");
}

function shareUrlFor(item) {
  const imdbUrl = `https://www.imdb.com/title/${encodeURIComponent(item.imdb_id)}/`;
  const text = encodeURIComponent(`${item.title} (${item.year})`);
  return `https://t.me/share/url?url=${encodeURIComponent(imdbUrl)}&text=${text}`;
}

function renderCard(item) {
  const li = document.createElement("li");
  li.className = "card";
  li.dataset.imdbId = item.imdb_id;

  const hasPoster = item.poster && item.poster !== "N/A";
  const posterHtml = hasPoster
    ? `<img class="poster" src="${item.poster}" alt="${item.title} poster" />`
    : `<div class="poster placeholder">🎬</div>`;

  const typeLabel = item.media_type === "series" ? "📺 Series" : "🎬 Movie";

  li.innerHTML = `
    ${posterHtml}
    <div class="card-body">
      <div>
        <div class="card-title">${item.title}</div>
        <div class="card-meta">${typeLabel} · ${item.year || "-"}</div>
      </div>
      <div class="card-actions">
        <button class="action-btn delete">🗑 Delete</button>
        <button class="action-btn share">🔗 Share</button>
      </div>
    </div>
  `;

  li.querySelector(".delete").addEventListener("click", () => deleteItem(item, li));
  li.querySelector(".share").addEventListener("click", () => {
    haptic("light");
    const url = shareUrlFor(item);
    if (tg && tg.openTelegramLink) {
      tg.openTelegramLink(url);
    } else {
      window.open(url, "_blank");
    }
  });

  return li;
}

async function deleteItem(item, cardEl) {
  cardEl.classList.add("removing");

  try {
    const res = await fetch("/api/watchlist/delete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": initData,
      },
      body: JSON.stringify({ imdb_id: item.imdb_id }),
    });

    if (!res.ok) throw new Error("Delete failed");

    haptic("success");
    setTimeout(() => {
      cardEl.remove();
      updateCount();
      if (els.list.children.length === 0) showState("empty");
    }, 150);
  } catch (err) {
    haptic("error");
    cardEl.classList.remove("removing");
    if (tg && tg.showAlert) {
      tg.showAlert("Couldn't remove this title. Please try again.");
    }
  }
}

function updateCount() {
  els.countPill.textContent = String(els.list.children.length);
}

async function loadWatchlist() {
  showState("loading");

  try {
    const res = await fetch("/api/watchlist", {
      headers: { "X-Telegram-Init-Data": initData },
    });

    if (!res.ok) throw new Error("Failed to load watchlist");

    const data = await res.json();
    const items = data.items || [];

    els.list.innerHTML = "";

    if (items.length === 0) {
      showState("empty");
      updateCount();
      return;
    }

    items.forEach((item) => els.list.appendChild(renderCard(item)));
    updateCount();
    showState("list");
  } catch (err) {
    els.loading.textContent = "Couldn't load your watchlist. Pull to refresh and try again.";
  }
}

loadWatchlist();

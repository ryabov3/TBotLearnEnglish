export const tg = typeof window !== "undefined" && window.Telegram ? window.Telegram.WebApp : null;

export async function apiFetch(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (tg && tg.initData) {
    headers["X-Telegram-Init-Data"] = tg.initData;
  }

  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Ошибка сервера (${res.status})`);
  }
  return data;
}

export function openBotDeepLink(botUsername, payload, onFallback) {
  if (botUsername && tg && tg.openTelegramLink) {
    tg.openTelegramLink(`https://t.me/${botUsername}?start=${payload}`);
    tg.close();
  } else if (onFallback) {
    onFallback();
  }
}

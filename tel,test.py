import asyncio
import traceback
import difflib
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from playwright.async_api import async_playwright
import os

TOKEN = os.environ.get("BOT_TOKEN")

async def search_steam(item_name: str) -> str:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            })

            search_url = (
                f"https://steamcommunity.com/market/search?q={item_name}"
                "&category_730_ItemSet%5B%5D=any"
                "&category_730_ProPlayer%5B%5D=any"
                "&category_730_StickerCapsule%5B%5D=any"
                "&category_730_Tournament%5B%5D=any"
                "&category_730_TournamentTeam%5B%5D=any"
                "&category_730_Type%5B%5D=any"
                "&category_730_Weapon%5B%5D=any"
                "&appid=730"
            )
            await page.goto(search_url, wait_until="domcontentloaded")

            try:
                await page.wait_for_selector(".market_listing_row", timeout=20000)
            except Exception:
                await browser.close()
                return "❌ No search results appeared (timeout)."

            first_item = await page.query_selector(".market_listing_row")
            if not first_item:
                await browser.close()
                return "❌ No result elements found."

            item_title = "Unknown"
            try:
                title_el = await first_item.query_selector(".market_listing_item_name")
                if title_el:
                    txt = await title_el.text_content()
                    if txt:
                        item_title = txt.strip()
            except:
                pass

            item_price = None
            for sel in [".market_listing_price_with_fee", ".normal_price", ".sale_price"]:
                try:
                    price_el = await first_item.query_selector(sel)
                    if price_el:
                        txt = await price_el.text_content()
                        if txt and txt.strip():
                            item_price = txt.strip()
                            break
                except:
                    continue
            if not item_price:
                item_price = "Price not available"

            await browser.close()

            ratio = difflib.SequenceMatcher(None, item_name.lower(), item_title.lower()).ratio()
            similarity_percent = int(ratio * 100)

            return (
                f"🎯 Item: {item_title}\n"
                f"💰 Price: {item_price}\n"
                f"🔍 Similarity: {similarity_percent}%"
            )

    except Exception as outer:
        tb = traceback.format_exc()
        print(f"[search_steam] unexpected error:\n{tb}")
        return "⚠️ Unexpected error during search."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text.lower().startswith("item "):
        return

    item_name = text[5:].strip()
    if not item_name:
        return

    await update.message.reply_text(f"🔎 Searching for '{item_name}' on Steam Market...")

    result = await search_steam(item_name)
    await update.message.reply_text(result)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running...")
    app.run_polling()

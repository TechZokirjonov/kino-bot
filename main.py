import os

import asyncio

import logging

import asyncpg

from datetime import datetime, timedelta

from aiohttp import web

from aiogram import Bot, Dispatcher, F, types

from aiogram.filters import Command

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup



# --- SOZLAMALAR ---

BOT_TOKEN = "8919520773:AAE64XexisrCiNY2QRgistWW8hQr5JR07Bg"

ADMIN_ID = 5603202969

ADMIN_USERNAME = "mz0401"

DATABASE_URL = os.environ.get("DATABASE_URL")



bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

db_pool = None



# --- BAZA BILAN ISHLASH ---

async def db_start():

    global db_pool

    db_pool = await asyncpg.create_pool(DATABASE_URL)

    async with db_pool.acquire() as conn:

        await conn.execute("""

            CREATE TABLE IF NOT EXISTS movies (

                code TEXT PRIMARY KEY,

                title TEXT,

                file_id TEXT,

                caption TEXT,

                is_premium INTEGER DEFAULT 0

            )

        """)

        await conn.execute("""

            CREATE TABLE IF NOT EXISTS users (

                user_id BIGINT PRIMARY KEY,

                joined_date TEXT

            )

        """)

        await conn.execute("""

            CREATE TABLE IF NOT EXISTS subscriptions (

                user_id BIGINT PRIMARY KEY,

                expire_date TEXT

            )

        """)



# --- FSM (Holatlar) ---

class AddMovie(StatesGroup):

    is_premium = State()

    code = State()

    title = State()

    file_id = State()

    caption = State()



class Broadcast(StatesGroup):

    text = State()



# --- START ---

@dp.message(Command("start"))

async def cmd_start(message: types.Message):

    user_id = message.from_user.id

    now_date = datetime.now().isoformat()

    

    async with db_pool.acquire() as conn:

        await conn.execute(

            "INSERT INTO users (user_id, joined_date) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",

            user_id, now_date

        )



    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="⭐ Premium sotib olish", callback_data="buy_premium")],

        [InlineKeyboardButton(text="👤 Profilim", callback_data="my_profile")]

    ])

    await message.answer("Salom! 🎬 Kino kodini yuboring yoki quyidagi bo'limlardan foydalaning:", reply_markup=keyboard)



# --- PROFIL VA OBUNANI TEKSHIRISH ---

async def check_user_premium(user_id: int) -> bool:

    async with db_pool.acquire() as conn:

        row = await conn.fetchrow("SELECT expire_date FROM subscriptions WHERE user_id = $1", user_id)

    

    if not row:

        return False

    expire_str = row['expire_date']

    if expire_str == "LIFETIME":

        return True

    

    expire_date = datetime.fromisoformat(expire_str)

    if datetime.now() < expire_date:

        return True

    return False



@dp.callback_query(F.data == "my_profile")

async def my_profile(call: types.CallbackQuery):

    user_id = call.from_user.id

    async with db_pool.acquire() as conn:

        row = await conn.fetchrow("SELECT expire_date FROM subscriptions WHERE user_id = $1", user_id)



    status = "Oddiy ❌"

    if row:

        expire_val = row['expire_date']

        if expire_val == "LIFETIME":

            status = "Bir umrlik Premium ⭐ (Cheksiz)"

        else:

            expire_date = datetime.fromisoformat(expire_val)

            if datetime.now() < expire_date:

                status = f"Premium ⭐ ({expire_date.strftime('%Y-%m-%d %H:%M')} gacha)"

            else:

                status = "Muddati tugagan ❌"



    await call.message.edit_text(

        f"👤 **Sizning profilingiz:**\n\n"

        f"🆔 ID: `{user_id}`\n"

        f"⭐ Obuna holati: {status}",

        parse_mode="Markdown",

        reply_markup=InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="⭐ Premium sotib olish", callback_data="buy_premium")],

            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_start")]

        ])

    )



@dp.callback_query(F.data == "back_start")

async def back_start(call: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="⭐ Premium sotib olish", callback_data="buy_premium")],

        [InlineKeyboardButton(text="👤 Profilim", callback_data="my_profile")]

    ])

    await call.message.edit_text(

        "Salom! 🎬 Kino kodini yuboring yoki quyidagi bo'limlardan foydalaning:",

        reply_markup=keyboard

    )



# --- PREMIUM SOTIB OLISH MENYUSI ---

@dp.callback_query(F.data == "buy_premium")

async def buy_premium(call: types.CallbackQuery):

    user_id = call.from_user.id

    async with db_pool.acquire() as conn:

        row = await conn.fetchrow("SELECT expire_date FROM subscriptions WHERE user_id = $1", user_id)



    has_active_sub = False

    sub_info = ""



    if row:

        expire_val = row['expire_date']

        if expire_val == "LIFETIME":

            has_active_sub = True

            sub_info = "Sizda **Bir umrlik (Lifetime) Premium** obuna mavjud ⭐"

        else:

            expire_date = datetime.fromisoformat(expire_val)

            if datetime.now() < expire_date:

                has_active_sub = True

                sub_info = f"Sizda faol Premium obuna mavjud ⭐\n📅 Tugash vaqti: **{expire_date.strftime('%Y-%m-%d %H:%M')}**"



    if has_active_sub:

        text = (

            "🎉 **Tabriklaymiz!**\n\n"

            f"{sub_info}\n\n"

            "Barcha Premium kinolardan cheklovlarsiz foydalanishingiz mumkin!"

        )

        reply_markup = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_start")]

        ])

    else:

        text = (

            "⭐ **Premium obuna turlari va narxlari:**\n\n"

            "1️⃣ **1 oylik:** 10 000 so'm\n"

            "2️⃣ **1 yillik:** 120 000 so'm\n"

            "3️⃣ **Bir umrlik (Lifetime):** 22$\n\n"

            "💬 Obuna bo'lish yoki batafsil ma'lumot olish uchun adminga murojaat qiling."

        )

        reply_markup = InlineKeyboardMarkup(inline_keyboard=[

            [InlineKeyboardButton(text="👨‍💻 Adminga yozish", url=f"https://t.me/{ADMIN_USERNAME}")],

            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_start")]

        ])



    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)



# --- ADMIN PANEL ---

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)

async def cmd_admin(message: types.Message):

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="admin_add")],

        [InlineKeyboardButton(text="👑 Premium berish", callback_data="admin_give_sub")],

        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stat")],

        [InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_broadcast")]

    ])

    await message.answer("Assalomu alaykum Admin! Kerakli bo'limni tanlang:", reply_markup=keyboard)



@dp.callback_query(F.data == "admin_stat", F.from_user.id == ADMIN_ID)

async def admin_stat(call: types.CallbackQuery):

    async with db_pool.acquire() as conn:

        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")

        all_users = await conn.fetch("SELECT joined_date FROM users")

        movies_count = await conn.fetchval("SELECT COUNT(*) FROM movies")

        prem_movies = await conn.fetchval("SELECT COUNT(*) FROM movies WHERE is_premium = 1")

    

    now = datetime.now()

    today_count = 0

    week_count = 0

    month_count = 0

    

    for u in all_users:

        date_str = u['joined_date']

        if date_str:

            try:

                j_date = datetime.fromisoformat(date_str)

                if j_date.date() == now.date():

                    today_count += 1

                if now - j_date <= timedelta(days=7):

                    week_count += 1

                if now - j_date <= timedelta(days=30):

                    month_count += 1

            except Exception:

                pass



    await call.message.answer(

        f"📊 **Bot statistikasi:**\n\n"

        f"👥 **Foydalanuvchilar:**\n"

        f" • Jami: {users_count} ta\n"

        f" • Bugun qo'shilganlar: {today_count} ta\n"

        f" • So'nggi 7 kunda: {week_count} ta\n"

        f" • So'nggi 30 kunda: {month_count} ta\n\n"

        f"🎬 **Kinolar:**\n"

        f" • Jami kinolar: {movies_count} ta\n"

        f" • ⭐ Premium kinolar: {prem_movies} ta",

        parse_mode="Markdown"

    )

    await call.answer()



@dp.callback_query(F.data == "admin_give_sub", F.from_user.id == ADMIN_ID)

async def admin_give_sub_info(call: types.CallbackQuery):

    await call.message.answer(

        "Foydalanuvchiga premium berish uchun quyidagi buyruqdan foydalan: \n\n"

        "`/give <user_id> <days>`\n"

        "Masalan (30 kun): `/give 123456789 30`\n"

        "Bir umrlik uchun: `/give 123456789 lifetime`",

        parse_mode="Markdown"

    )



@dp.message(Command("give"), F.from_user.id == ADMIN_ID)

async def give_subscription(message: types.Message):

    args = message.text.split()

    if len(args) < 3:

        await message.answer("Xato format! Ishlatilishi: `/give <user_id> <days yoki lifetime>`", parse_mode="Markdown")

        return

    

    target_id = int(args[1])

    duration = args[2]

    

    if duration.lower() == "lifetime":

        expire_val = "LIFETIME"

    else:

        days = int(duration)

        expire_val = (datetime.now() + timedelta(days=days)).isoformat()

        

    async with db_pool.acquire() as conn:

        await conn.execute(

            "INSERT INTO subscriptions (user_id, expire_date) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET expire_date = $2",

            target_id, expire_val

        )

    

    await message.answer(f"✅ `{target_id}` ID egasiga muvaffaqiyatli Premium berildi!", parse_mode="Markdown")

    try:

        await bot.send_message(target_id, "🎉 Tabriklaymiz! Sizga botda Premium obuna taqdim etildi ⭐")

    except Exception:

        pass



# --- KINO QO'SHISH ---

@dp.callback_query(F.data == "admin_add", F.from_user.id == ADMIN_ID)

async def admin_add_start(call: types.CallbackQuery, state: FSMContext):

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="🟢 Oddiy kino", callback_data="type_0")],

        [InlineKeyboardButton(text="⭐ Premium kino", callback_data="type_1")]

    ])

    await call.message.answer("Kino turini tanlang:", reply_markup=keyboard)



@dp.callback_query(F.data.startswith("type_"), F.from_user.id == ADMIN_ID)

async def process_movie_type(call: types.CallbackQuery, state: FSMContext):

    is_prem = int(call.data.split("_")[1])

    await state.update_data(is_premium=is_prem)

    await state.set_state(AddMovie.code)

    await call.message.edit_text("🎬 Kino uchun kod kiriting (masalan: 101):")



@dp.message(AddMovie.code, F.from_user.id == ADMIN_ID)

async def process_code(message: types.Message, state: FSMContext):

    await state.update_data(code=message.text.strip())

    await state.set_state(AddMovie.title)

    await message.answer("Kino nomini kiriting:")



@dp.message(AddMovie.title, F.from_user.id == ADMIN_ID)

async def process_title(message: types.Message, state: FSMContext):

    await state.update_data(title=message.text)

    await state.set_state(AddMovie.file_id)

    await message.answer("Kinoning video faylini (yoki videoxabarni) yuboring:")



@dp.message(AddMovie.file_id, F.video, F.from_user.id == ADMIN_ID)

async def process_file(message: types.Message, state: FSMContext):

    await state.update_data(file_id=message.video.file_id)

    await state.set_state(AddMovie.caption)

    await message.answer("Kino haqida izoh (matn) yuboring:")



@dp.message(AddMovie.caption, F.from_user.id == ADMIN_ID)

async def process_caption(message: types.Message, state: FSMContext):

    data = await state.get_data()

    

    async with db_pool.acquire() as conn:

        await conn.execute(

            """INSERT INTO movies (code, title, file_id, caption, is_premium) 

               VALUES ($1, $2, $3, $4, $5) 

               ON CONFLICT (code) DO UPDATE SET title = $2, file_id = $3, caption = $4, is_premium = $5""",

            data['code'], data['title'], data['file_id'], message.text, data['is_premium']

        )

    

    await state.clear()

    prem_text = "⭐ Premium kino" if data['is_premium'] == 1 else "🟢 Oddiy kino"

    await message.answer(f"✅ {prem_text} muvaffaqiyatli saqlandi! Kod: `{data['code']}`", parse_mode="Markdown")



# --- REKLAMA TARQATISH ---

@dp.callback_query(F.data == "admin_broadcast", F.from_user.id == ADMIN_ID)

async def broadcast_start(call: types.CallbackQuery, state: FSMContext):

    await state.set_state(Broadcast.text)

    await call.message.answer("Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:")



@dp.message(Broadcast.text, F.from_user.id == ADMIN_ID)

async def broadcast_send(message: types.Message, state: FSMContext):

    await state.clear()

    async with db_pool.acquire() as conn:

        users = await conn.fetch("SELECT user_id FROM users")



    sent = 0

    failed = 0

    for user in users:

        try:

            await message.send_copy(chat_id=user['user_id'])

            sent += 1

            await asyncio.sleep(0.05)

        except Exception:

            failed += 1



    await message.answer(f"📢 Reklama tarqatildi:\n\n✅ Yetib bordi: {sent}\n❌ Bloklaganlar: {failed}")



# --- KINO QIDIRISH (ASOSIY QISM) ---

@dp.message(F.text)

async def get_movie(message: types.Message):

    if message.text.startswith("/"):

        return



    user_id = message.from_user.id

    code = message.text.strip()

    

    async with db_pool.acquire() as conn:

        movie = await conn.fetchrow("SELECT title, file_id, caption, is_premium FROM movies WHERE code = $1", code)



    if movie:

        title = movie['title']

        file_id = movie['file_id']

        caption = movie['caption'] or ""

        is_premium = movie['is_premium']

        

        if is_premium == 1 and not await check_user_premium(user_id):

            keyboard = InlineKeyboardMarkup(inline_keyboard=[

                [InlineKeyboardButton(text="⭐ Premium sotib olish", callback_data="buy_premium")]

            ])

            await message.answer(

                "❌ **Bu kino Premium talab qiladi!**\n\n"

                "Ushbu kinoni ko'rish uchun obuna sotib oling.",

                reply_markup=keyboard,

                parse_mode="Markdown"

            )

            return



        text = f"🎬 <b>{title}</b>\n\n{caption}"

        await message.answer_video(video=file_id, caption=text, parse_mode="HTML")

    else:

        await message.answer("❌ Bunday kodli kino topilmadiku brat. Kodni tekshirib qaytadan yubor.")



# --- RENDER WEB SERVER ---

async def handle(request):

    return web.Response(text="Bot is running!")



async def web_server():

    app = web.Application()

    app.router.add_get("/", handle)

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(os.environ.get("PORT", 8080))

    site = web.TCPSite(runner, "0.0.0.0", port)

    await site.start()



# --- MAIN ---

async def main():

    logging.basicConfig(level=logging.INFO)

    await db_start()

    print("Bot ishga tushdi va Supabase bazasiga ulandi...")

    await web_server()

    await dp.start_polling(bot)



if __name__ == "__main__":

    asyncio.run(main())

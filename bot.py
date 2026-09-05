import asyncio
import aiosqlite
import random
import os
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command

# ========== НАСТРОЙКИ ==========
API_TOKEN = '8758331684:AAHzhf0Px-MzVtHk1m6mzCZRPONWbsgdOLc'
BOT_NAME = 'Мой Тап Бот'
COIN_NAME = 'COINS'
WEB_APP_URL = 'https://frolicking-strudel-7063c5.netlify.app/'
REF_BONUS = 1000
PORT = int(os.environ.get('PORT', 10000))

# ========== БАЗА ДАННЫХ ==========
DB_NAME = 'database.db'

async def db_start():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                total_taps INTEGER DEFAULT 0,
                power INTEGER DEFAULT 1,
                ref_count INTEGER DEFAULT 0,
                ref_id INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def add_user(user_id, ref_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id, ref_id) VALUES (?, ?)', (user_id, ref_id or 0))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        await db.commit()

async def update_power(user_id, price):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET balance = balance - ?, power = power + 1 WHERE user_id = ?', (price, user_id))
        await db.commit()

async def update_ref_count(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?', (user_id,))
        await db.commit()

# ========== КЛАВИАТУРА ==========
def get_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎮 ИГРАТЬ', web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text='📊 Статистика', callback_data='stats'),
         InlineKeyboardButton(text='🏆 Топ игроков', callback_data='top')],
        [InlineKeyboardButton(text='👥 Пригласить друга', callback_data='ref'),
         InlineKeyboardButton(text='⚡ Улучшения', callback_data='upgrade_menu')]
    ])
    return keyboard

def get_upgrade_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⚡ +1 к силе клика (100 COINS)', callback_data='up_power')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back')]
    ])
    return keyboard

# ========== КОМАНДА START ==========
async def start_cmd(message: Message):
    args = message.text.split()
    ref_id = None
    if len(args) > 1:
        try:
            ref_id = int(args[1])
        except:
            pass
    
    await add_user(message.from_user.id, ref_id)
    
    if ref_id and ref_id != message.from_user.id:
        ref_user = await get_user(ref_id)
        if ref_user:
            await update_balance(ref_id, REF_BONUS)
            await update_ref_count(ref_id)
            try:
                await bot.send_message(ref_id, f'🎉 По твоей ссылке зарегистрировался новый игрок!\n+{REF_BONUS} {COIN_NAME}')
            except:
                pass
    
    text = f"""
👋 Привет, {message.from_user.first_name}!

Добро пожаловать в <b>{BOT_NAME}</b>!

🎮 Жми <b>ИГРАТЬ</b> и тапай по монете!
💰 Зарабатывай {COIN_NAME}!
👥 Приглашай друзей и получай бонусы!
"""
    await message.answer(text, parse_mode='HTML', reply_markup=get_menu())

# ========== СТАТИСТИКА ==========
async def stats_callback(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if user:
        text = f"""
📊 <b>Твоя статистика</b>

💰 Баланс: <b>{user[1]} {COIN_NAME}</b>
🖱️ Всего тапов: <b>{user[2]}</b>
⚡ Сила клика: <b>{user[3]}</b>
👥 Приглашено: <b>{user[4]}</b>
"""
        await callback.answer()
        await callback.message.answer(text, parse_mode='HTML')

# ========== ТОП ИГРОКОВ ==========
async def top_callback(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10') as cursor:
            top = await cursor.fetchall()
    
    text = "🏆 <b>ТОП-10 ИГРОКОВ</b>\n\n"
    medals = ['🥇', '🥈', '🥉']
    
    for i, (uid, bal) in enumerate(top):
        try:
            user_info = await bot.get_chat(uid)
            name = user_info.first_name
        except:
            name = f"Игрок {uid}"
        
        medal = medals[i] if i < 3 else f'{i+1}.'
        text += f"{medal} <b>{name}</b> — {bal} {COIN_NAME}\n"
    
    await callback.answer()
    await callback.message.answer(text, parse_mode='HTML')

# ========== РЕФЕРАЛЬНАЯ ССЫЛКА ==========
async def ref_callback(callback: CallbackQuery):
    bot_info = await bot.get_me()
    ref_link = f'https://t.me/{bot_info.username}?start={callback.from_user.id}'
    
    text = f"""
👥 <b>Приглашай друзей!</b>

За каждого друга ты получаешь <b>{REF_BONUS} {COIN_NAME}</b>!

🔗 Твоя ссылка:
<code>{ref_link}</code>

Отправь её друзьям!
"""
    await callback.answer()
    await callback.message.answer(text, parse_mode='HTML')

# ========== УЛУЧШЕНИЯ ==========
async def upgrade_menu_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer('⚡ Выбери улучшение:', reply_markup=get_upgrade_menu())

async def up_power_callback(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    price = 100
    
    if user[1] >= price:
        await update_power(user[0], price)
        user = await get_user(callback.from_user.id)
        await callback.answer(f'✅ Улучшено! Сила клика: {user[3]}', show_alert=True)
    else:
        await callback.answer(f'❌ Недостаточно монет! Нужно {price} {COIN_NAME}', show_alert=True)

async def back_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer('Главное меню:', reply_markup=get_menu())

# ========== FLASK СЕРВЕР ==========
app = Flask(__name__)

@app.route('/save', methods=['POST'])
def save_data():
    data = request.get_json()
    user_id = data.get('user_id')
    balance = data.get('balance')
    taps = data.get('taps')
    power = data.get('power')
    
    async def save():
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute('UPDATE users SET balance = ?, total_taps = ?, power = ? WHERE user_id = ?', (balance, taps, power, user_id))
            await db.commit()
    
    asyncio.run(save())
    return jsonify({'status': 'ok'})

@app.route('/load', methods=['GET'])
def load_data():
    user_id = request.args.get('user_id')
    
    async def load():
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute('SELECT balance, total_taps, power FROM users WHERE user_id = ?', (user_id,)) as cursor:
                return await cursor.fetchone()
    
    user = asyncio.run(load())
    if user:
        return jsonify({'balance': user[0], 'taps': user[1], 'power': user[2]})
    return jsonify({'balance': 0, 'taps': 0, 'power': 1})

# ========== ЗАПУСК ==========
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def run_bot():
    await db_start()
    
    dp.message.register(start_cmd, Command('start'))
    dp.callback_query.register(stats_callback, F.data == 'stats')
    dp.callback_query.register(top_callback, F.data == 'top')
    dp.callback_query.register(ref_callback, F.data == 'ref')
    dp.callback_query.register(upgrade_menu_callback, F.data == 'upgrade_menu')
    dp.callback_query.register(up_power_callback, F.data == 'up_power')
    dp.callback_query.register(back_callback, F.data == 'back')
    
    print('✅ Бот запущен!')
    await dp.start_polling(bot)

if __name__ == '__main__':
    # Запускаем бота в том же потоке, где Flask
    import threading
    import time
    
    # Создаем новый event loop для бота
    def run_async_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_bot())
    
    t = threading.Thread(target=run_async_bot, daemon=True)
    t.start()
    
    # Flask в главном потоке
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

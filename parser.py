import asyncio
import logging
import asyncpg
import os
from dotenv import load_dotenv

from aiogram.filters import Command, CommandObject
from telethon import TelegramClient, events
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from telethon.errors import UsernameNotOccupiedError, ChannelInvalidError

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

client = TelegramClient("anon", api_id, api_hash)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = None

logging.basicConfig(level=logging.INFO)

@dp.message(Command('start'))
async def start(message: Message):
    await message.answer("Hello!")

@dp.message(Command('addKeyword'))
async def add_keyword(message: Message, command: CommandObject):
    args = command.args
    if not args:
        await message.answer('You did not write anything!')
        return
    try:
        await db.execute(
            "INSERT INTO keywords(word) VALUES($1)",
            args
        )
        await message.answer('Keyword has been added!')
    except asyncpg.UniqueViolationError:
        await message.answer('this keyword already in list!')

@dp.message(Command("addChannel"))
async def add_channel(message: Message, command: CommandObject):
    args = command.args
    try:
        if args:
            await client.get_entity(args)
            try:
                await db.execute(
                    "INSERT INTO channels(username) VALUES($1)",
                    args
                )
                await message.answer('channel has been added!')
            except asyncpg.UniqueViolationError:
                await message.answer('this channel already in list!')
        else:
            await message.answer('You did not write anything!')
            return
    except(UsernameNotOccupiedError, ChannelInvalidError, ValueError):
        await message.answer("this chat/channel doesn't exist!")
        return

@dp.message(Command('allKeywords'))
async def show_keywords(message: Message, ):
    rows = await db.fetch("SELECT word FROM keywords")

    if rows:
        words = [row['word'] for row in rows]
        await message.answer(", ".join(words))
    else:
        await message.answer("List of keywords is empty!")

@dp.message(Command('allChannels'))
async def show_channels(message: Message, ):
    rows = await db.fetch("SELECT username FROM channels")

    if rows:
        usernames = [row['username'] for row in rows]
        await message.answer(", ".join(usernames))
    else:
        await message.answer("List of channels is empty!")

@dp.message(Command("deleteKeyword"))
async def delete_keyword(message: Message, command: CommandObject):
    args = command.args
    if not args:
        await message.answer("You didn't write anything!")
    else:
        try:
            await db.execute(
                "DELETE FROM keywords WHERE word = $1", args
            )
            await message.answer("Keyword was deleted successfully!")
        except ValueError:
            await message.answer("This keyword does not exist in the list!")
            return

@dp.message(Command("deleteChannel"))
async def delete_channel(message: Message, command: CommandObject):
    args = command.args
    if not args:
        await message.answer("You didn't write anything!")
    else:
        try:
            await db.execute(
                "DELETE FROM channels WHERE username = $1", args
            )
            await message.answer("Channel was deleted successfully!")
        except ValueError:
            await message.answer("This channel does not exist in the list!")
            return

@client.on(events.NewMessage())
async def event_handler(event):
    if not event.raw_text:
        return

    chat = await event.get_chat()
    username = getattr(chat, 'username', None)

    if not username:
        return

    channel_exists = await db.fetchrow(
        "SELECT 1 FROM channels WHERE username=$1",
        username
    )

    if not channel_exists:
        return

    rows = await db.fetch("SELECT word FROM keywords")
    keywords = [row["word"] for row in rows]

    link = f"https://t.me/{username}/{event.message.id}"

    for keyword in keywords:
        if keyword.lower() in event.raw_text.lower():
            await bot.send_message(chat_id=8544667429, text=f"{event.raw_text}\n\n{link}")
            break

async def main():
    global db
    db = await asyncpg.create_pool(DATABASE_URL)

    await client.start()
    await bot.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(
        client.run_until_disconnected(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
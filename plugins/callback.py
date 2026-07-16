from pyrogram import Client
from pyrogram.types import CallbackQuery
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@Client.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):

    data = callback.data

    if data == "suggest_me":

        text = (
            "🎬 **Select what you're looking for**\n\n"
            "Choose one of the options below."
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎬 Movies",
                        callback_data="movies"
                    ),
                    InlineKeyboardButton(
                        "📺 Series",
                        callback_data="series"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Home",
                        callback_data="home"
                    )
                ]
            ]
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard
        )

        await callback.answer()

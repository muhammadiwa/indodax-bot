from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import main_menu_keyboard
from bot.utils.messages import HELP_TEXT, LINK_INSTRUCTION_TEXT, MAIN_MENU_TEXT

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.callback_query(F.data == "menu_home")
async def menu_home(callback: CallbackQuery) -> None:
    await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_api")
async def menu_api(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        LINK_INSTRUCTION_TEXT,
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()

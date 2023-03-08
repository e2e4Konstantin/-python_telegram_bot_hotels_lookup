import asyncio

from bot.define_bot import bot, dp
from bot.settings_bot import set_main_menu, register_all_handlers


async def main():
    """

    Основная функция для запуска бота.
    Вызывается set_main_menu() для создания основного меню бота.
    Регистрируются хэндлеры register_all_handlers()
    Запускаем бота start_polling()
    """
    await set_main_menu(dp)
    register_all_handlers(dp)
    try:
        print('Бот запустился.')
        await dp.start_polling()

    finally:
        await bot.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as err:
        print('Бот остановлен!', err)

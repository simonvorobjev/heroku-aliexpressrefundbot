from telegram import ReplyKeyboardRemove
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram.ext.dispatcher import run_async
import threading, queue
import AliExpress
import sys
import os

updater = Updater(token='600467031:AAGKCCUCFzWMz4DQ2axfqo4Xz76S31yUCLc')

PRODUCT_CHOOSE, BRAND_CHOOSE, PRICE_RANGE_CHOOSE, FILTER_WORDS_CHOOSE, SEARCH_NEXT = range(5)
condition_result_ready_dict = {}
condition_user_ready_dict = {}
link_dict = {}


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Введите /find чтобы начать поиск товара для refund'а")


def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Введите /find чтобы начать поиск товара для refund'а")


@run_async
def iddqd(bot, update):
        bot.send_message(chat_id=update.message.chat_id, text="Secret found! Stopping server!")
        global updater
        updater.stop()
        sys.exit(0)


@run_async
def idfa(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Secret found! Restarting server!")
    global updater
    updater.stop()
    os.execl(sys.executable, 'python3', 'bot.py', *sys.argv[1:])


def text_reply(bot, update, user_data):
    bot.send_message(chat_id=update.message.chat_id, text="Введите /find чтобы начать поиск товара для refund'а")


def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)


def begin(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='Здравствуйте! Для начала необходимо будет ввести что будем '
                                                          'искать и какой бренд имеет продукт. Введите что будем искать:')
    return PRODUCT_CHOOSE


def product_reply(bot, update, user_data):
    text = update.message.text
    user_data['product'] = text
    update.message.reply_text('Поиск сохранен! Введите диапазон цен в формате 10-30 (в долларах) (/skip чтобы пропустить ввод цен):')
    return PRICE_RANGE_CHOOSE


def price_range_reply(bot, update, user_data):
    text = update.message.text
    prices = text.split('-')
    min_price = prices[0]
    if not min_price:
        min_price = ''
    max_price = prices[1]
    if not max_price:
        max_price = ''
    user_data['min_price'] = min_price
    user_data['max_price'] = max_price
    update.message.reply_text('Диапазон цен сохранен! Введите слова для фильтрации через запятую (например case,for,glass) (/skip чтобы пропустить ввод фильтров):')
    return FILTER_WORDS_CHOOSE


def skip_price_range_reply(bot, update, user_data):
    user_data['min_price'] = ''
    user_data['max_price'] = ''
    update.message.reply_text('Диапазон не задан. Введите слова для фильтрации через запятую (например case,for,glass) (/skip чтобы пропустить ввод фильтров):')
    return FILTER_WORDS_CHOOSE


def filter_reply(bot, update, user_data):
    text = update.message.text
    filter_words = text.split(',')
    if not filter_words:
        filter_words = []
    user_data['filter_words'] = filter_words
    update.message.reply_text('Фильтры сохранены! Введите бренд:')
    return BRAND_CHOOSE


def skip_filter_reply(bot, update, user_data):
    user_data['filter_words'] = []
    update.message.reply_text('Фильтры не заданы. Введите бренд:')
    return BRAND_CHOOSE


def brand_reply(bot, update, user_data):
    text = update.message.text
    user_data['brand'] = text
    update.message.reply_text('Бренд сохранен! Начинаем поиск!')
    link_dict[update.message.chat_id] = []
    condition_result_ready_dict[update.message.chat_id] = threading.Condition()
    condition_user_ready_dict[update.message.chat_id] = threading.Condition()
    threading.Thread(name='refund_thread',
                     target=AliExpress.find_refund,
                     args=(user_data, link_dict[update.message.chat_id], condition_result_ready_dict[update.message.chat_id], condition_user_ready_dict[update.message.chat_id])).start()
    with condition_result_ready_dict[update.message.chat_id]:
        if not condition_result_ready_dict[update.message.chat_id].wait(60):
            bot.send_message(chat_id=update.message.chat_id, text="Поиск завершен по таймауту.")
            user_data.clear()
            return ConversationHandler.END
    if link_dict[update.message.chat_id][0] is None:
        bot.send_message(chat_id=update.message.chat_id, text="Больше ничего не найдено, поиск завершен.")
        user_data.clear()
        return ConversationHandler.END
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Ну как тебе вот это? " + link_dict[update.message.chat_id][0])
        bot.send_message(chat_id=update.message.chat_id, text="Искать дальше? Да/Нет")
        return SEARCH_NEXT


@run_async
def search_next(bot, update, user_data):
    text = update.message.text
    if text.lower() == 'да':
        with condition_user_ready_dict[update.message.chat_id]:
            condition_user_ready_dict[update.message.chat_id].notifyAll()
        with condition_result_ready_dict[update.message.chat_id]:
            if not condition_result_ready_dict[update.message.chat_id].wait(60):
                bot.send_message(chat_id=update.message.chat_id, text="Поиск завершен по таймауту.")
                user_data.clear()
                return ConversationHandler.END
        if link_dict[update.message.chat_id][0] is None:
            bot.send_message(chat_id=update.message.chat_id, text="Больше ничего не найдено, поиск завершен.")
            user_data.clear()
            return ConversationHandler.END
        else:
            bot.send_message(chat_id=update.message.chat_id, text="Ну как тебе вот это? " + link_dict[update.message.chat_id][0])
            bot.send_message(chat_id=update.message.chat_id, text="Искать дальше? Да/Нет")
            return SEARCH_NEXT
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Хорошо, поиск завершен.")
        user_data.clear()
        return ConversationHandler.END


def cancel(bot, update, user_data):
    user = update.message.from_user
    update.message.reply_text('Пока! Продолжим в следующий раз!',
                              reply_markup=ReplyKeyboardRemove())
    user_data.clear()
    return ConversationHandler.END


def conversation_timeout(bot, update, user_data):
    user = update.message.from_user
    update.message.reply_text('Ты думаешь слишком долго! Продолжим в следующий раз!',
                              reply_markup=ReplyKeyboardRemove())
    user_data.clear()
    return ConversationHandler.END


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    global updater
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    iddqd_handler = CommandHandler('iddqd', iddqd)
    idfa_handler = CommandHandler('idfa', idfa)
    text_handler = MessageHandler(Filters.text, text_reply, pass_user_data=True)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('find', begin)],
        states={
            PRODUCT_CHOOSE: [MessageHandler(Filters.text,
                                           product_reply,
                                           pass_user_data=True),
                            ],
            BRAND_CHOOSE: [MessageHandler(Filters.text,
                                           brand_reply,
                                           pass_user_data=True),
                            ],
            PRICE_RANGE_CHOOSE: [MessageHandler(Filters.text,
                                          price_range_reply,
                                          pass_user_data=True),
                                 CommandHandler('skip',
                                                skip_price_range_reply,
                                                pass_user_data=True),
                           ],
            FILTER_WORDS_CHOOSE: [MessageHandler(Filters.text,
                                          filter_reply,
                                          pass_user_data=True),
                                 CommandHandler('skip',
                                                skip_filter_reply,
                                                pass_user_data=True),
                           ],
            SEARCH_NEXT: [MessageHandler(Filters.text,
                                         search_next,
                                         pass_user_data=True),
                            ],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text,
                                                         conversation_timeout,
                                         pass_user_data=True),
                                          ]
        },
        fallbacks = [CommandHandler('cancel', cancel, pass_user_data=True)],
        run_async_timeout = 60,
        conversation_timeout = 60
    )
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(iddqd_handler)
    dispatcher.add_handler(idfa_handler)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(text_handler)
    updater.start_polling(poll_interval = 1.0, timeout=20, clean=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit()

from telegram import ReplyKeyboardRemove
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram.ext.dispatcher import run_async
import threading, queue
import AliExpress
import sys
import os
import datetime
import sqlite3

#conn = sqlite3.connect("mydatabase.db")
#cursor = conn.cursor()
#cursor.execute("""CREATE TABLE users
#                  (user_id text primary key, user_name text, last_login text,
#                   total_logins text)
#               """)
#conn.commit()
#conn.close()

updater = Updater(token='600467031:AAGKCCUCFzWMz4DQ2axfqo4Xz76S31yUCLc')

PRODUCT_CHOOSE, BRAND_CHOOSE, PRICE_RANGE_CHOOSE, FILTER_WORDS_CHOOSE, SEARCH_NEXT = range(5)
GET_MESSAGE_TO_POST = range(1)
condition_result_ready_dict = {}
condition_user_ready_dict = {}
link_dict = {}


def update_db(update):
    user_id = str(update.message.chat_id)
    user_name = update.message.from_user.username
    last_login = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
    total_logins = str(1)
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()
    count = cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchall()
    if len(count) > 0:
        total_logins = str(int(count[0][3]) + 1)
    conn.execute("INSERT OR REPLACE INTO users values (?, ?, ?, ?)", (user_id, user_name, last_login, total_logins))
    conn.commit()
    cursor.close()
    conn.close()


def get_all_users_from_db():
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()
    all_users = cursor.execute("SELECT * FROM users").fetchall()
    cursor.close()
    conn.close()
    return all_users


def delete_user_from_db(user_id):
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()


def start(bot, update):
    update_db(update)
    bot.send_message(chat_id=update.message.chat_id, text='Чтобы искать товар, введите поиск, как вы искали бы его на Aliexpress. '
                                                          'Например, вводить просто "телефон" бессмысленно, нужно вводить, например '
                                                          '"телефон Ulefone S7". Искать самые популярные бренды вроде "телефон Xiaomi" '
                                                          'так же бессмысленно, так как их продавцов мало, они авторизованные, '
                                                          'и заполняют поле "бренд" в описании правильно. Идеальный поиск - '
                                                          'ввести что-то содержащее имя бренда, имя модели и тип товара, например '
                                                          '"Meizu EP51 Wireless Bluetooth Earphone".'
                                                          ' По всем вопросам обращайтесь к @simonvorobyov (https://t.me/simonvorobyov)')


def help(bot, update):
    update_db(update)
    bot.send_message(chat_id=update.message.chat_id, text='Чтобы искать товар, введите поиск, как вы искали бы его на Aliexpress. '
                                                          'Например, вводить просто "телефон" бессмысленно, нужно вводить, например '
                                                          '"телефон Ulefone S7". Искать самые популярные бренды вроде "телефон Xiaomi" '
                                                          'так же бессмысленно, так как их продавцов мало, они авторизованные, '
                                                          'и заполняют поле "бренд" в описании правильно. Идеальный поиск - '
                                                          'ввести что-то содержащее имя бренда, имя модели и тип товара, например '
                                                          '"Meizu EP51 Wireless Bluetooth Earphone".'
                                                          ' По всем вопросам обращайтесь к @simonvorobyov (https://t.me/simonvorobyov)')


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
    update_db(update)
    bot.send_message(chat_id=update.message.chat_id, text="Введите /find чтобы начать поиск товара для refund'а."
                                                          " По всем вопросам обращайтесь к @simonvorobyov (https://t.me/simonvorobyov)")


def begin(bot, update):
    update_db(update)
    bot.send_message(chat_id=update.message.chat_id, text='Здравствуйте! Для начала необходимо будет ввести что будем '
                                                          'искать и какой бренд имеет продукт. Введите что будем искать '
                                                          '(например "клавиатура Motospeed"):')
    return PRODUCT_CHOOSE


def product_reply(bot, update, user_data):
    text = update.message.text
    user_data['product'] = text
    update.message.reply_text('Поиск сохранен! Введите диапазон цен в формате 10-30 (в долларах) (/skip чтобы пропустить ввод цен):')
    return PRICE_RANGE_CHOOSE


def price_range_reply(bot, update, user_data):
    text = update.message.text
    prices = text.split('-')
    if len(prices) < 2:
        update.message.reply_text(
            'Вы ввели диапазон цен неправильно, диапазон не сохранен. '
            'Введите слова для фильтрации через запятую (например case,for,glass) (/skip чтобы пропустить ввод фильтров):')
        user_data['min_price'] = ''
        user_data['max_price'] = ''
        return FILTER_WORDS_CHOOSE
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
    update.message.reply_text('Фильтры сохранены! Введите бренд '
                              '(например "Motospeed"):')
    return BRAND_CHOOSE


def skip_filter_reply(bot, update, user_data):
    user_data['filter_words'] = []
    update.message.reply_text('Фильтры не заданы. Введите бренд (например "Motospeed"):')
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
        if not condition_result_ready_dict[update.message.chat_id].wait(120):
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
            if not condition_result_ready_dict[update.message.chat_id].wait(120):
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


def post_message(bot, update):
    users = get_all_users_from_db()
    for user in users:
        try:
            bot.forward_message(int(user[0]), update.message.chat_id, update.message.message_id)
        except:
            delete_user_from_db(user[0])
        #bot.send_message(chat_id=int(user[0]), text=update.message.text, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


def count_users(bot, update):
    users = get_all_users_from_db()
    bot.send_message(chat_id=update.message.chat_id,
                     text=('Количество юзеров в базе: ' + str(len(users))))


def begin_post(bot, update):
    update_db(update)
    bot.send_message(chat_id=update.message.chat_id, text='Форвардни мне сообщение которое нужно опубликовать. /cancel для отмены.')
    return GET_MESSAGE_TO_POST



def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    global updater
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    iddqd_handler = CommandHandler('iddqd', iddqd)
    idfa_handler = CommandHandler('idfa', idfa)
    count_users_handler = CommandHandler('count', count_users)
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
        run_async_timeout = 120,
        conversation_timeout = 120
    )
    conv_post_handler = ConversationHandler(
        entry_points=[CommandHandler('post', begin_post)],
        states={
            GET_MESSAGE_TO_POST: [MessageHandler(Filters.text,
                                                 post_message),
                                  ],
        },
        fallbacks=[CommandHandler('cancel', cancel, pass_user_data=True)],
        conversation_timeout=120
    )
    text_handler = MessageHandler(Filters.text, text_reply, pass_user_data=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(iddqd_handler)
    dispatcher.add_handler(idfa_handler)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(conv_post_handler)
    dispatcher.add_handler(count_users_handler)
    dispatcher.add_handler(text_handler)
    updater.start_polling(poll_interval = 1.0, timeout=20, clean=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit()

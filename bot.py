from telegram import ReplyKeyboardRemove
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler
import threading
import AliExpress
from flask import Flask
import os

app = Flask(__name__, static_folder='static')

PRODUCT_CHOOSE, BRAND_CHOOSE, SEARCH_NEXT = range(3)
condition_result_ready = threading.Condition()
condition_user_ready = threading.Condition()
link_list = []
refund_thread = ''


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Введите /find чтобы начать поиск товара для refund'а")


def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Введите /find чтобы начать поиск товара для refund'а")


def text_reply(bot, update, user_data):
    bot.send_message(chat_id=update.message.chat_id, text="Введите /find чтобы начать поиск товара для refund'а")


def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)


def begin(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='Здравствуйте! Для начала необходимо будет ввести что будем '
                                                          'искать и какой бренд имеет продукт. Введите что будем искать:')
    return PRODUCT_CHOOSE
    #product = update.message.text
    #bot.send_message(chat_id=update.message.chat_id, text='Введи бренд:')
    #brand = update.message.text
    #link_list = []
    #t = threading.Thread(target=AliExpress.find_refund, args=(product, brand, link_list))

    #bot.send_message(chat_id=update.message.chat_id, text=update.message.text)


def product_reply(bot, update, user_data):
    text = update.message.text
    user_data['product'] = text
    update.message.reply_text('Поиск сохранен! Введите бренд:')
    return BRAND_CHOOSE


def brand_reply(bot, update, user_data):
    text = update.message.text
    user_data['brand'] = text
    update.message.reply_text('Бренд сохранен! Начинаем поиск!')
    global refund_thread
    refund_thread = threading.Thread(name='refund_thread',
                                     target=AliExpress.find_refund, args=(user_data['product'],
                                                                          user_data['brand'], link_list, condition_result_ready, condition_user_ready))
    #link = AliExpress.find_refund(user_data['product'], user_data['brand'], link_list, condition_result_ready, condition_user_ready)
    refund_thread.start()
    with condition_result_ready:
        if (not refund_thread.is_alive()) or (not condition_result_ready.wait(20)):
            bot.send_message(chat_id=update.message.chat_id, text=("Поиск завершен по таймауту."))
            user_data.clear()
            return ConversationHandler.END
    if link_list[0] == 'None':
        bot.send_message(chat_id=update.message.chat_id, text=("Больше ничего не найдено, поиск завершен."))
        user_data.clear()
        return ConversationHandler.END
    else:
        bot.send_message(chat_id=update.message.chat_id, text=("Ну как тебе вот это? " + link_list[0]))
        bot.send_message(chat_id=update.message.chat_id, text=("Искать дальше? Да/Нет"))
        return SEARCH_NEXT

def search_next(bot, update, user_data):
    text = update.message.text
    global refund_thread
    if text.lower() == 'да':
        with condition_user_ready:
            condition_user_ready.notifyAll()
        with condition_result_ready:
            if (not refund_thread.is_alive()) or (not condition_result_ready.wait(20)):
                bot.send_message(chat_id=update.message.chat_id, text=("Поиск завершен по таймауту."))
                user_data.clear()
                return ConversationHandler.END
        if link_list[0] == 'None':
            bot.send_message(chat_id=update.message.chat_id, text=("Больше ничего не найдено, поиск завершен."))
            user_data.clear()
            return ConversationHandler.END
        else:
            bot.send_message(chat_id=update.message.chat_id, text=("Ну как тебе вот это? " + link_list[0]))
            bot.send_message(chat_id=update.message.chat_id, text=("Искать дальше? Да/Нет"))
            return SEARCH_NEXT
    else:
        bot.send_message(chat_id=update.message.chat_id, text=("Хорошо, поиск завершен."))
        user_data.clear()
        return ConversationHandler.END


def cancel(bot, update, user_data):
    user = update.message.from_user
    update.message.reply_text('Пока! Продолжим в следующий раз!',
                              reply_markup=ReplyKeyboardRemove())
    user_data.clear()
    return ConversationHandler.END


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    updater = Updater(token='600467031:AAGKCCUCFzWMz4DQ2axfqo4Xz76S31yUCLc')
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    text_handler = MessageHandler(Filters.text, text_reply, pass_user_data=True)
    #echo_handler = MessageHandler(Filters.text, echo)
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
            SEARCH_NEXT: [MessageHandler(Filters.text,
                                         search_next,
                                         pass_user_data=True),
                            ]
        },
        fallbacks = [CommandHandler('cancel', cancel, pass_user_data=True)]
    )
    #find_handler = CommandHandler('find', FindRefund)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(text_handler)
    #dispatcher.add_handler(find_handler)
    #dispatcher.add_handler(echo_handler)
    updater.start_polling()


if __name__ == '__main__':
    try:
        app.debug = True
        port = int(os.environ.get('PORT',5000))
        app.run(host='0.0.0.0', port=port)
        main()
    except KeyboardInterrupt:
        exit()

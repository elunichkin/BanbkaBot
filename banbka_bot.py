import pymorphy2
from datetime import datetime
from pytz import utc, timezone
from BanbkaBot import BanbkaBot

# TODO: tokenize data

banyaBot = BanbkaBot(token_file='token.pkl', db_file='db.pkl')


def main():
    while True:
        last_update = banyaBot.get_last_update()

        if 'message' not in last_update.keys() or 'text' not in last_update['message'].keys():
            continue

        update_id = last_update['update_id']
        msg = last_update['message']
        msg_id = msg['message_id']
        msg_chat = msg['chat']['id']
        msg_text = msg['text']
        msg_time = datetime.fromtimestamp(msg['date'])

        args = msg_text.split()

        if args[0] in ['/settime', '/settime@BanbkaBot']:
            # TODO: method for checking number of arguments
            # TODO: encapsulate everything into methods
            if len(args) < 3:
                banyaBot.send_message(chat_id=msg_chat,
                                      text="Слишком мало аргументов: задайте дату и время",
                                      reply_to_message_id=msg_id)
            else:
                try:
                    banyaBot.set_time(date=args[1], time=args[2],
                                      update_id=update_id,
                                      chat_id=msg_chat, msg_id=msg_id,
                                      msg_time=msg_time)
                    banyaBot.send_message(chat_id=msg_chat,
                                          text="Дата и время следующей банбки успешно установлены",
                                          reply_to_message_id=msg_id)
                except ValueError as e:
                    banyaBot.send_message(chat_id=msg_chat,
                                          text=e)
                    continue

        if args[0] in ['/setloc', '/setloc@BanbkaBot']:
            if len(args) != 3:
                banyaBot.send_message(chat_id=msg_chat,
                                      text="Передайте ровно 2 аргумента: широту и долготу",
                                      reply_to_message_id=msg_id)
            else:
                try:
                    banyaBot.set_loc(lat=float(args[1]), lon=float(args[2]),
                                     update_id=update_id,
                                     chat_id=msg_chat, msg_id=msg_id,
                                     msg_time=msg_time)
                    banyaBot.send_message(chat_id=msg_chat,
                                          text="Место следующей банбки успешно установлено",
                                          reply_to_message_id=msg_id)
                except ValueError as e:
                    banyaBot.send_message(chat_id=msg_chat,
                                          text=e)
                    continue

        if args[0] in ['/countdown', '/countdown@BanbkaBot']:
            morph = pymorphy2.MorphAnalyzer()
            day_w, hour_w, minute_w = morph.parse('день')[0], morph.parse('час')[0], morph.parse('минута')[0]

            try:
                timedelta = banyaBot.get_countdown(chat_id=msg_chat)
                days, hours, minutes = timedelta.days, timedelta.seconds // 3600, (timedelta.seconds % 3600) // 60

                announcement = "⚡️⚡️⚡️БЛИН БЛИНСКИЙ ДО БАНБКИ ОСТАЛОСЬ"
                if days > 0:
                    announcement += " {0} {1}".format(days, day_w.make_agree_with_number(days).word.upper())
                if hours > 0:
                    announcement += " {0} {1}".format(hours, hour_w.make_agree_with_number(hours).word.upper())
                if minutes > 0:
                    announcement += " {0} {1}".format(minutes, minute_w.make_agree_with_number(minutes).word.upper())
                announcement += "."

                banyaBot.send_message(chat_id=msg_chat,
                                      text=announcement)
            except RuntimeError as e:
                banyaBot.send_message(chat_id=msg_chat,
                                      text=e,
                                      reply_to_message_id=msg_id)
                continue

        if args[0] in ['/getloc', '/getloc@BanbkaBot']:
            try:
                lat, lon = banyaBot.get_loc(chat_id=msg_chat)
                text = "Координаты следующей банбки: {lat}, {lon}\n" \
                       "[Яндекс.Карты](https://yandex.ru/maps/?text={lat}%2C%20{lon})"
                banyaBot.send_message(chat_id=msg_chat,
                                      text=text.format(lat=str(lat), lon=str(lon)),
                                      parse_mode='markdown')
            except RuntimeError as e:
                banyaBot.send_message(chat_id=msg_chat,
                                      text=e,
                                      reply_to_message_id=msg_id)
                continue

        if args[0] in ['/getinfo', '/getinfo@BanbkaBot']:
            try:
                dttm = banyaBot.get_datetime(chat_id=msg_chat)
                lat, lon = banyaBot.get_loc(chat_id=msg_chat)
                text = "*Дата и время следующей банбки:* {datetime}\n" \
                       "*Координаты следующей банбки:* {lat}, {lon}\n" \
                       "[Яндекс.Карты](https://yandex.ru/maps/?text={lat}%2C%20{lon})"
                banyaBot.send_message(chat_id=msg_chat,
                                      text=text.format(
                                          datetime=str(dttm.replace(tzinfo=utc).astimezone(timezone('Europe/Moscow'))),
                                          lat=str(lat), lon=str(lon)
                                      ),
                                      parse_mode='markdown')
            except RuntimeError as e:
                banyaBot.send_message(chat_id=msg_chat,
                                      text=e,
                                      reply_to_message_id=msg_id)
                continue

        # TODO: add /start command here
        if args[0] in ['/help', '/help@BanbkaBot', '/start', '/start@BanbkaBot']:
            text = "*Поддерживаемые команды:*\n\n" \
                   "/settime — Установить время следующей банбки.\n" \
                   "/setloc — Установить координаты следующей банбки.\n" \
                   "/countdown — Получить обратный отсчёт до следующей банбки.\n" \
                   "/getloc — Получить координаты следующей банбки и ссылку на Яндекс.Карты.\n" \
                   "/getinfo — Получить полную информацию о следующей банбке.\n" \
                   "/help — Получить это сообщение.\n\n" \
                   "Исходный код: https://github.com/elunichkin/BanbkaBot"
            banyaBot.send_message(chat_id=msg_chat,
                                  text=text,
                                  parse_mode='markdown')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
    except Exception as e:
        banyaBot.send_message(chat_id=1753590,
                              text=e)
        exit(1)

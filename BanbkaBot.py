from BotHandler import BotHandler
from datetime import datetime, timedelta


class BanbkaBot(BotHandler):
    def __init__(self, token=None, token_file=None, timeout=1, db=None, db_file=None):
        super().__init__(token, token_file, timeout, db, db_file)

    def set_time(self, date, time, update_id, chat_id, msg_id, msg_time):
        # TODO: Add pytz timezones here
        try:
            dttm_string = date + '.' + str(datetime.now().year) + ' ' + time
            dttm = datetime.strptime(dttm_string, '%d.%m.%Y %H:%M') - timedelta(seconds=3600*3)
        except ValueError:
            raise ValueError("Дата и время не удовлетворяет формату 'dd.mm HH:MM'")

        if dttm < datetime.utcnow():
            raise ValueError("Дата и время в прошлом")

        self.dbconnector.insert('banya_time',
                                ['update_id', 'chat_id', 'message_id', 'added_dttm', 'banya_dttm'],
                                [str(update_id),
                                 str(chat_id),
                                 str(msg_id),
                                 "to_timestamp('{0}', 'YYYY-MM-DD HH24:MI:SS')".format(str(msg_time)),
                                 "to_timestamp('{0}', 'YYYY-MM-DD HH24:MI:SS')".format(str(dttm))])

    def set_loc(self, lat, lon, update_id, chat_id, msg_id, msg_time):
        if not (-90 < lat < 90) or not (-180 < lon <= 180):
            raise ValueError('Широта или долгота вне допустимых значений')

        self.dbconnector.insert('banya_loc',
                                ['update_id', 'chat_id', 'message_id', 'added_dttm', 'latitude', 'longitude'],
                                [str(update_id),
                                 str(chat_id),
                                 str(msg_id),
                                 "to_timestamp('{0}', 'YYYY-MM-DD HH24:MI:SS')".format(str(msg_time)),
                                 str(lat),
                                 str(lon)])

    def get_datetime(self, chat_id):
        query = """
                    WITH t AS (
                        SELECT
                            *,
                            row_number() over (PARTITION BY chat_id ORDER BY message_id DESC) AS rn
                        FROM {schema}.banya_time
                    )

                    SELECT
                        banya_dttm
                    FROM t
                    WHERE chat_id = {chatid} AND rn = 1
                """.format(schema='{schema}', chatid=str(chat_id))
        try:
            dttm = self.dbconnector.custom_select(query=query)[0][0]
            return dttm
        except IndexError:
            raise RuntimeError('Время банбки ещё не было задано')

    def get_countdown(self, chat_id):
        delta = self.get_datetime(chat_id) - datetime.utcnow()
        if delta.total_seconds() <= 60:
            raise RuntimeError('Время банбки уже прошло!')
        return delta

    def get_loc(self, chat_id):
        query = """
            WITH t AS (
                SELECT
                    *,
                    row_number() over (PARTITION BY chat_id ORDER BY message_id DESC) AS rn
                FROM {schema}.banya_loc
            )
            
            SELECT
                latitude,
                longitude
            FROM t
            WHERE chat_id = {chatid} AND rn = 1
        """.format(schema='{schema}', chatid=chat_id)

        try:
            lat, lon = self.dbconnector.custom_select(query=query)[0]
            return lat, lon
        except IndexError:
            raise RuntimeError('Место банбки ещё не было задано')
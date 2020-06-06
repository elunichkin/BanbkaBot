import requests
import json
import pickle
from collections import deque
from psycopg2 import connect as pg_connect, errors as pg_errors


class BotHandler:
    # TODO: version and method for new features description broadcasting

    def __init__(self, token=None, token_file=None, timeout=10, db=None, db_file=None):
        if token:
            self.token = token
        elif token_file:
            with open(token_file, 'rb') as infile:
                self.token = pickle.load(infile)
        else:
            raise ValueError('No valid token provided')

        self.url = "https://api.telegram.org/bot{}/".format(self.token)
        self.offset = None
        self.timeout = timeout
        self.updates = deque()

        if db:
            conn = tuple(db)
        elif db_file:
            with open(db_file, 'rb') as infile:
                conn = tuple(pickle.load(infile))
        self.db = DBConnector(*conn)

    # API methods:
    def get_updates(self, offset=None, timeout=1):
        method, params = 'getUpdates', {'offset': offset,
                                        'timeout': timeout}

        response = requests.get(self.url + method, params).json()
        try:
            updates = deque(response['result'])
        except KeyError as e:
            print(e)
            updates = []

        return updates

    def get_last_update(self):
        while len(self.updates) == 0:
            self.updates = self.get_updates(offset=self.offset, timeout=self.timeout)

        last_update = self.updates.popleft()
        update_id = last_update['update_id']
        self.offset = update_id + 1

        try:
            with self.db as con:
                con.log_update(update_id=update_id, update=last_update)
        except pg_errors.UniqueViolation:
            pass

        return last_update

    def send_message(self, chat_id, text, reply_to_message_id=None, parse_mode=None):
        method, params = 'sendMessage', {'chat_id': chat_id,
                                         'text': text,
                                         'reply_to_message_id': reply_to_message_id,
                                         'parse_mode': parse_mode}
        response = requests.get(self.url + method, data=params)
        return response

    def get_admins(self, chat_id):
        method, params = 'getChatAdministrators', {'chat_id': chat_id}
        response = json.loads(requests.post(self.url + method, data=params).text)
        admins = [x['user']['id'] for x in response['result']] if response['ok'] else []
        return admins

    def get_member(self, chat_id, user_id):
        method, params = 'getChatMember', {'chat_id': chat_id, 'user_id': user_id}
        response = requests.post(self.url + method, data=params)
        return json.loads(response.text)

    def restrict_member(self, chat_id, user_id, until_date,
                        can_send_messages=None, can_send_media_messages=None,
                        can_send_other_messages=None, can_add_web_page_previews=None):
        method, params = 'restrictChatMember', {'chat_id': chat_id,
                                                'user_id': user_id,
                                                'until_date': until_date,
                                                'can_send_messages': can_send_messages,
                                                'can_send_media_messages': can_send_media_messages,
                                                'can_send_other_messages': can_send_other_messages,
                                                'can_add_web_page_previews': can_add_web_page_previews}
        response = requests.post(self.url + method, data=params)
        return response

    def promote_member(self, chat_id, user_id,
                       can_change_info=False, can_post_messages=False,
                       can_edit_messages=False, can_delete_messages=False,
                       can_invite_users=False, can_restrict_members=False,
                       can_pin_messages=False, can_promote_members=False):
        method, params = 'promoteChatMember', {'chat_id': chat_id,
                                               'user_id': user_id,
                                               'can_change_info': can_change_info,
                                               'can_post_messages': can_post_messages,
                                               'can_edit_messages': can_edit_messages,
                                               'can_delete_messages': can_delete_messages,
                                               'can_invite_users': can_invite_users,
                                               'can_restrict_members': can_restrict_members,
                                               'can_pin_messages': can_pin_messages,
                                               'can_promote_members': can_promote_members}
        response = requests.post(self.url + method, data=params)
        return response


class DBConnector:
    def __init__(self, host, user, password, schema):
        self.schema = schema
        self.connection_params = dict(host=host, port=5432, dbname=user, user=user, password=password)
        self.connection = None

    def connect(self):
        self.connection = pg_connect(**self.connection_params)

    def cursor(self):
        return self.connection.cursor()

    def close(self):
        self.connection.close()

    def insert(self, table, columns, values):
        parameters = ','.join(['%s' for _ in values])
        column_names = ','.join(columns)
        with self.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.schema}.{table} ({column_names}) VALUES ({parameters})",
                values
            )

    def log_update(self, update_id, update):
        self.insert(
            table='updates',
            columns=['update_id', 'update_json'],
            values=(update_id, json.dumps(update))
        )

    def select(self, table, columns):
        column_names = ','.join(columns)
        with self.cursor() as cur:
            cur.execute(
                f"SELECT {column_names} FROM {self.schema}.{table}"
            )
            return cur.fetchall()

    def custom_select(self, query):
        query = query.format(schema=self.schema)
        with self.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.commit()
        self.close()

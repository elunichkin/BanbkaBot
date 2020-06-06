import requests
import json
import pickle
from collections import deque
import postgresql


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
            self.dbconnector = DBConnector(url=db[0], user=db[1], password=db[2], schema=db[3])
        elif db_file:
            with open(db_file, 'rb') as infile:
                self.dbconnector = DBConnector(*pickle.load(infile))

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
            self.dbconnector.log_update(update_id=update_id, update=last_update)
        except postgresql.exceptions.UniqueError:
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
    def __init__(self, url, user, password, schema):
        self.url = url
        self.user = user
        self.password = password
        self.schema = schema
        self.db = postgresql.open('pq://{0}:{1}@{2}:5432/{0}'.format(user, password, url))

    def log_update(self, update_id, update):
        query = """
            INSERT INTO {0}.updates (update_id, update_json) VALUES ({1}, '{2}')
        """.format(self.schema, update_id, json.dumps(update))
        self.db.execute(query)

    def insert(self, table, columns, values):
        query = """
            INSERT INTO {0}.{1} ({2}) VALUES ({3})
        """.format(self.schema, table, ', '.join(columns), ', '.join(values))
        self.db.execute(query)

    def select(self, table, columns):
        query = """
            SELECT {0} FROM {1}.{2}
        """.format(columns, self.schema, table)
        return self.db.query(query)

    def custom_select(self, query):
        query = query.format(schema=self.schema)
        return self.db.query(query)

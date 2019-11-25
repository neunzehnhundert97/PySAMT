from typing import Union

from requests import Session, Response


class LowerBot:
    BASE_URL = "https://api.telegram.org/bot{}/"

    def __init__(self, token: str):
        self.token = token
        self.url = self.BASE_URL.format(token)
        self.session = Session()

    def _make_request(self, method: str, data=None) -> dict:
        req: Response = self.session.post(self.url + method, data=data)
        if req.ok:
            try:
                json = req.json()
                if json['ok']:
                    return json['result']
                else:
                    pass
            except:
                pass
        else:
            pass

    def get_me(self):
        return User(self._make_request("getMe"))

    def send_message(self, chat_id: Union[int, str],
                     text: str, parse_mode: str = None,
                     disable_web_page_preview: bool = None,
                     disable_notification: bool = None,
                     reply_to_message_id: int = None,
                     reply_markup=None):

        data = dict(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            reply_to_message_id=reply_to_message_id,
            reply_markup=reply_markup
        )

        return self._make_request("sendMessage", data)


class User:

    def __init__(self, json: dict):
        self.id = json['id']
        self.is_bot = json['is_bot']
        self.first_name = json['first_name']
        self.last_name = json.get('last_name', "")
        self.username = json.get('username', "")
        self.language_code = json.get('language_code', "")

    def __str__(self):
        return "User[{}:{}]".format(self.first_name, self.id)

import asyncio

from marvin import Marvin, Answer, Context, Mode

marv = Marvin()

#Put here Your Own TelegramID
userID=222371620

@marv.default_answer
def default():
    return 'unknown', Context.get('message').text


@marv.answer("/start")
async def start():
    return Answer('greeting', Context.get('user'))


@marv.before_processing
def auth():
    if Context.get('user').id == userID:
        return True
    elif Context.get('message').text == "/start":
        return True
    else:
        return False



if __name__ == "__main__":
    marv.listen()

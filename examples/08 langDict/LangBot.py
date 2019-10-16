import asyncio

from marvin import Marvin, Answer, Context, Mode

marv = Marvin()


@marv.default_answer
def default():
    return 'unknown', Context.get('message').text


@marv.answer("/start")
async def start():
    return Answer('greeting', Context.get('user'))


@marv.answer("Guten Tag")
def guten_tag():
    a = Answer('greeting', Context.get('user'))
    a.language_feature = False
    return a


if __name__ == "__main__":
    marv.listen()

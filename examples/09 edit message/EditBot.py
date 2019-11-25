import asyncio

from samt import Bot, Answer, Context, Mode

marv = Bot()


@marv.default_answer
def default():
    return 'unknown', Context.get('message').text



@marv.answer("rw")
def rewrite():
    return Answer("newMessage", edit_id=Context.get("history")[0].id)


if __name__ == "__main__":
    marv.listen()

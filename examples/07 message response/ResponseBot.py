import asyncio

from samt import Bot, Answer, Context, Mode

marv = Bot()


@marv.default_answer
def default():
    return 'unknown', Context.get('message').text


@marv.answer("/talk")
async def talk():
    x= yield Answer("Was willst du?\n"
                "/stop zum Abbrechen\n")
    if x == "/stop":
        yield Answer("abgebrochen")
    elif len(x)>0:
        yield Answer(x)



if __name__ == "__main__":
    marv.listen()

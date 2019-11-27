from samt import Bot

bot = Bot()


@bot.default_answer
def default():
    return "Try it with\nGet me!"


@bot.answer("Get me!")
def send_me():
    return "document:MediaBot.py;It's me!"


@bot.answer("Sticker")
def sticker():
    return "sticker:CAADAgADzgEAAqwUnwaWEKfm00_ExAI"


if __name__ == "__main__":
    bot.listen()

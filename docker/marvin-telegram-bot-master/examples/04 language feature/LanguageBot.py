from marvin import Marvin, Context

bot = Marvin()


@bot.default_answer
def default():
    return 'unknown', Context.get('message')


if __name__ == "__main__":
    bot.listen()

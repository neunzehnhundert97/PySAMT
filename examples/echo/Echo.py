from marvin import Marvin, Context

bot = Marvin()


@bot.default_answer
def echo():
    return Context.get('message').text


if __name__ == "__main__":
    bot.listen()

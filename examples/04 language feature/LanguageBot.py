from samt import Bot, Context

bot = Bot()


@bot.default_answer
def default():
    return 'unknown', Context.get('message')


if __name__ == "__main__":
    bot.listen()

import asyncio

from marvin import Marvin, Answer, Context, Mode

marv = Marvin()


@marv.default_answer
def default():
    return 'unknown', Context.get('message').text


@marv.answer("Key")
def key():
    a = Answer("Hier isses", keyboard=[["Ja, Nein"], ["Nööö"], ["..."]])
    return a


@marv.answer("Key2")
def key():
    a = Answer("Hier isses", keyboard=[["Ja"], ["Nein"], ["Nööö"], ["..."]])
    return a


@marv.answer("Key3")
def key():
    a = Answer("Hier isses", keyboard=["Ja", "Nein", "Nööö", "..."])
    return a


@marv.answer("rmKey")
def key():
    a = Answer("keyboard entfernt", keyboard=0)
    return a

if __name__ == "__main__":
    marv.listen()

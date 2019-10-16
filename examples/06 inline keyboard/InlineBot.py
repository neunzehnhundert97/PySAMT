import asyncio

from marvin import Marvin, Answer, Context, Mode

marv = Marvin()




@marv.answer("/Query")
def test():
    def callback(msg):
        a = Answer("Interessiert mich nicht " + msg)
        a.mark_as_answer = False
        return a

    q = Answer("<b>W</b><i>ill</i>ste?", choices=["Ja" "Nein", "Vielleicht", "Möglichweise", "Ein klares womöglich"],
               callback=callback)
    # q.markup = "Markdown"
    return q


if __name__ == "__main__":
    marv.listen()

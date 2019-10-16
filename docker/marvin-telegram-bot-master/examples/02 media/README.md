# Sending media files

This bot will send its main file when sending him the command _Get me!_ and return a sticker upon sending _Sticker_.

## Explanation

To easily send files, photos and so on, the bot analyses the string to return for a range of certain commandos. The syntax is `type:path_to_file[;Caption]`, where the caption may be omitted and will be ignored if not applicable.

The available commands are:

- sticker*
- voice
- audio
- photo
- video
- document

*In the case of sticker you supply the sticker's file id instead of a path.

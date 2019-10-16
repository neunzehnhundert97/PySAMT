#!/bin/bash
#FULLREBUILD="ja"



docker container stop marvinbot
docker container rm marvinbot
if [ "$FULLREBUILD" = "ja" ];  then
    echo You may go to the party.
    rm Marvin.zip
    rm -R marvin-telegram-bot-master/
    curl -o Marvin.zip https://codeload.github.com/neunzehnhundert97/marvin-telegram-bot/zip/master
    unzip Marvin
fi
docker build -t marvinbot1 .
# Use the -d command to start container on background
docker run --restart=always -d --name marvinbot marvinbot1
# Use without the -d command to see the logs
#docker run --name marvinbot marvinbot1

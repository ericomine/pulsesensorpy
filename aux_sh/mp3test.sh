#! /bin/bash

ffmpeg -i drum.mp3 -f alsa "default:CARD=Device" -re -vol 20

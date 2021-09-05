#!/bin/sh
[ ! -d "cache" ] && mkdir cache
cd cache
python ../suzukaze.py
cd ..
rm -r cache

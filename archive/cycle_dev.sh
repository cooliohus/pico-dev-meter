#!/bin/bash
echo "Starting Cycle"

for ((i = 500 ; i < 2600 ; i+=500)); do
     echo  -e "r,2,$i"
     echo -e "r,2,$i" > /dev/ttyACM2
     sleep 4
     echo -e "u" > /dev/ttyACM2
     sleep 1

done

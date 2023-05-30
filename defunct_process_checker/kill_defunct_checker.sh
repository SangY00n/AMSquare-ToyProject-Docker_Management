#!/bin/sh

PROC=`ps -ef | grep "python3.10 -u defunct_checker" | grep -v grep | awk '{print $2}'`
PID=$((PROC))
if [ ${PID} != 0 ];
then
    echo "Kill the process with PID: ${PID}"
    kill -9 ${PID}
else
    echo "defunct_checker is not running"
fi

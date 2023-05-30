#!/bin/sh

# 이미 실행 중이었을 경우 종료 후 재시작
PROC=`ps -ef | grep "python3.10 -u defunct_checker" | grep -v grep | awk '{print $2}'`
PID=$((PROC))
if [ ${PID} != 0 ];
then
    echo "defunct_checker was already running... Kill the process of previous defunc_checker with PID: ${PID}"
    kill -9 ${PID}
fi


# 로그 파일 이름 지정
today=$(date "+%Y%m%d_%H%M%S")
log_file_name="defunct_checker_log_${today}.log"

# defunct_checker.py 실행
echo "Starting defunct_checker.py..."
echo "Logs are written to the ${log_file_name} file."
nohup python3.10 -u defunct_checker.py > ${log_file_name} &
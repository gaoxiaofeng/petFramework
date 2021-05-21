login nbi3gcpm node
pm generate omes file:
# crontab -e
############### PET - START: PM Simulator crons ###############
@hourly cd /home/omc/PET_TOOL/tools/omes/;java -jar qsi-omesGenerator-1.0.jar omes config_raw_60_20K.yml
*/15 * * * *  cd /home/omc/PET_TOOL/tools/omes/;java -jar qsi-omesGenerator-1.0.jar omes config_raw_15_20K.yml
############### PET - END: PM Simulator crons #################


login etl node:
#guard_file.sh 0 1
统计pm处理能力，还有多少omes文件没有被处理


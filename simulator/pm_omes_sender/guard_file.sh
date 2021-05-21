#!/bin/bash

CURDIR=`dirname $0`;
if [ ${CURDIR} == "." ]
then
	CURDIR=`pwd`;
fi

LOGDIR=${CURDIR}/simu_stats
mkdir -p ${LOGDIR}

help()
{
cat << HELP

USAGE: $0 <NBI ONLY> [RTPM]

	<NBI ONLY>:  1, test only NBI. 0, include onePM.
	[RTPM]: 1, send RTPM data. 0, send normal PM data. Default 0.
	
HELP
	exit 0
}

function _kill()
{
    NFSS=`grep 'Name="nfs"' ${SMANAGER_CONF}| sed -n 's/^.*Node="\(.*\)" Priority.*$/\1/ p'`
	ssh $NFSS -C "ps -ef | egrep \"iostat -xt\"|grep -v grep| awk '{print \$2}'|xargs -iGID kill -9 GID 2>/dev/null"
}

if [[ -z $1 ]] || [[ $1 -ne 0 ]] && [[ $1 -ne 1 ]];then
	help
fi
if [[ ! -z $2 ]] && [[ $2 -ne 0 ]] && [[ $2 -ne 1 ]];then
	help
fi

# NBI_ONLY=1: test only NBI. 0, include onePM
NBI_ONLY=$1

#1, send RTPM data. 0, send normal PM data.
RTPM=0
[ ! -z $2 ] && RTPM=$2

if [ $NBI_ONLY -eq 1 ];then
	#IOstat
	TOP_INT=30.00
	GEP_INT="60000"
	IO_INT=5
	SAR_INT=300
	RESULT_DIR="/root"
	SMANAGER_CONF="/var/opt/cpf/ha/smanagerConf.xml"
	NFSS=`grep 'Name="nfs"' ${SMANAGER_CONF}| sed -n 's/^.*Node="\(.*\)" Priority.*$/\1/ p'`
	NODE=$(hostname -s)

	trap "echo 'capture ctrl+c';_kill;trap INT" INT

	ssh $NFSS -C "ps -ef | egrep \"iostat -xt\"|grep -v grep| awk '{print \$2}'|xargs -iGID kill -9 GID 2>/dev/null"
	ssh $NFSS -C "iostat -xt $IO_INT >| ${RESULT_DIR}/${NFSS}_iostat.txt &"
	#ssh $NFSS -C "iostat -xt 60 >| ${RESULT_DIR}/${NFSS}_iostat_1min.txt &"
fi

#PM north export directory monitor
pm3gppDir='/var/opt/nokia/oss/global/mediation/north/pm/export/com.nsn.app.nbm.pm3gpp-1'
ftpDir='/home/ftirpuser/pm'

if [ $NBI_ONLY -eq 0 ];then
	#onepmLoadDir='/d/oss/global/var/mediation/south/pm/import'
	onepmLoadDir='/var/opt/nokia/oss/osscore/iscirp/pmupld_osscore/'
	onepmEtloadWork='/var/opt/nokia/oss/rep*/etload/pg_repetl*/work'
	onepmEtloadWorkLoad='/var/opt/nokia/oss/rep*/etload/pg_repetl*/work/load_*'
	onepmEtloadWorkErr='/var/opt/nokia/oss/rep*/etload/pg_repetl*/work/*_err'
	onepmEtloadWorkExport='/var/opt/nokia/oss/rep*/etload/pg_repetl*/work/export'
	pm3gppDir='/d/oss/global/var/mediation/north/pm/export/com.nsn.app.nbm.pm3gpp-1'
	
	printf "DateTime, LoadDir, EtloadWork, EtloadWorkLoad, EtloadWorkErr, EtloadWorkExport, pm3gpp-1\n" | tee ${LOGDIR}/guard_files_number.csv
else
	printf "DateTime, pm3gpp-1\n" | tee ${LOGDIR}/guard_files_number.csv
fi
while true 
	do
		waitMaxTime=30
		waitMaxTimeWhileFileFound=30
		if [ $RTPM -eq 1 ]; then
			waitMaxTime=10
			waitMaxTimeWhileFileFound=10
		fi
		
		dt=`date +%m-%dT%H:%M:%S`
		beginTime=`date +%s%N`
		printf "$dt, " | tee -a ${LOGDIR}/guard_files_number.csv
		if [ $NBI_ONLY -eq 0 ];then
			filesInOnepmLoadDir=`find $onepmLoadDir -type f -name "*.xml*" 2>/dev/null | wc -l`
			printf "$filesInOnepmLoadDir, " | tee -a  ${LOGDIR}/guard_files_number.csv
			filesInOnepmEtloadWork=`find $onepmEtloadWork -type f -name "*.xml*" 2>/dev/null | wc -l`
			printf "$filesInOnepmEtloadWork, " | tee -a ${LOGDIR}/guard_files_number.csv
			filesInOnepmEtloadWorkLoad=`find $onepmEtloadWorkLoad -type f -name "*.xml*" 2>/dev/null | wc -l`
			printf "$filesInOnepmEtloadWorkLoad, " | tee -a ${LOGDIR}/guard_files_number.csv
			filesInOnepmEtloadWorkErr=`find $onepmEtloadWorkErr -type f -name "*.xml*" 2>/dev/null | wc -l`
			printf "$filesInOnepmEtloadWorkErr, " | tee -a ${LOGDIR}/guard_files_number.csv
			filesInOnepmEtloadWorkExport=`find $onepmEtloadWorkExport -type f -name "*.xml*" 2>/dev/null | wc -l`
			printf "$filesInOnepmEtloadWorkExport, " | tee -a ${LOGDIR}/guard_files_number.csv
			
			#find $onepmEtloadWorkErr -type f -name "*.xml"|xargs rm -f
		fi
		
		filesInPm3gpp=`find $pm3gppDir -type f -name "*.xml" 2>/dev/null | wc -l`
		printf "$filesInPm3gpp" | tee -a ${LOGDIR}/guard_files_number.csv
		#filesInFtp=`find $ftpDir -type f -name "PM*.xml" 2>/dev/null | wc -l`
		#printf "$filesInFtp" | tee -a ${LOGDIR}/guard_files_number.csv
		
		printf "\n" | tee -a ${LOGDIR}/guard_files_number.csv
		
		if [ $NBI_ONLY -eq 0 ];then
			if [ $filesInOnepmEtloadWork -ne 0 ];then
				waitMaxTime=$waitMaxTimeWhileFileFound
			fi
		elif [ $filesInPm3gpp -ne 0 ];then
			waitMaxTime=$waitMaxTimeWhileFileFound
		fi
		endTime=`date +%s%N`
		usedTime=$(expr $endTime - $beginTime)
		let "sleepTime=$waitMaxTime * 1000000000 - $usedTime"	
		#sleepTime=`echo "$waitMaxTime * 1000000000 - $usedTime	"|bc`	
		while [ $sleepTime -lt 0 ]; do
			waitMaxTime=$(expr $waitMaxTime + $waitMaxTime)
			let "sleepTime=$waitMaxTime * 1000000000 - $usedTime"
		done
		sleepTime=`echo "scale=2; $sleepTime / 1000000000"|bc`
		sleep $sleepTime
	done
exit 0


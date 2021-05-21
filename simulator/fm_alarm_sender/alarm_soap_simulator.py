from subprocess import Popen, PIPE
import logging
from os.path import join, dirname, abspath
import re
import time
import random
import datetime
import os
import optparse
import signal
import sys
import requests
from threading import Thread
from queue import Queue


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    handler_file = logging.FileHandler(join(dirname(abspath(__file__)), 'alarm_soap_simulator.log'), mode='w')
    handler_file.setFormatter(formatter)
    logger.addHandler(handler_file)

    @classmethod
    def info(cls, message):
        message = message.strip()
        cls.logger.info(message)

    @classmethod
    def error(cls, message):
        message = message.strip()
        cls.logger.error(message)
        print(message)

    @classmethod
    def debug(cls, message):
        message = message.strip()
        cls.logger.debug(message)

    @classmethod
    def warning(cls, message):
        message = message.strip()
        cls.logger.warning(message)

    @classmethod
    def enable_debug(cls):
        cls.logger.setLevel(logging.DEBUG)


def execute_command(command):
    command = command.strip()
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.strip()
    stderr = stderr.strip()
    rc = process.returncode
    if rc:
        Logger.debug("stdout: {}".format(stdout))
        Logger.debug("stderr: {}".format(stderr))
        Logger.debug("rc: {}".format(rc))
    return stdout.decode('utf-8'), stderr.decode('utf-8'), rc


class SearchService(object):

    def __init__(self):
        super(SearchService, self).__init__()

    @staticmethod
    def _get_service_node_and_status_by_smanager(service):
        stdout, stderr, rc = execute_command("smanager.pl status service ^{}$".format(service))
        if rc:
            Logger.error("smanager failed, error:{}".format(stderr))
            exit(1)
        else:
            host = stdout.split(":")[1]
            status = stdout.split(":")[-1]
            return host, status

    @classmethod
    def get_restda_fm_node(cls):
        host, status = cls._get_service_node_and_status_by_smanager("restda-fm")
        if status == "started":
            return host
        else:
            Logger.error("restda-fm is: {}".format(status))
            exit(1)


def execute_sqlplus_command(sql, user='omc', password='omc'):
    command = 'echo -e "set head off;\\n {sql};" | sqlplus -s {user}/{password}'.format(sql=sql, user=user,
                                                                                        password=password)
    Logger.debug(sql)
    stdout, stderr, rc = execute_command(command)
    Logger.debug(stdout)
    Logger.debug(stderr)
    if rc:
        Logger.error(stderr)
        exit(1)
    if stdout:
        return stdout
    return '?'


class Notification(object):
    def __init__(self, system_dn='PLMN-PLMN/MRBTS-1',
                 lifted_dn='PLMN-PLMN/MRBTS-1',
                 alarm_id=3000000,
                 specific_problem='50000',
                 probable_cause='81',
                 event_type='communication',
                 original_severity='critical',
                 perceived_severity='critical',
                 alarm_text='alarm from alarm_soap_simulator.py',
                 additional_text1='additionalText1',
                 additional_text2='additionalText2',
                 additional_text3='additionalText3',
                 additional_text4='additionalText4',
                 additional_text5='additionalText5',
                 additional_text6='additionalText6',
                 additional_text7='additionalText7',
                 notification_id=1000001,
                 external_correlation_id='00',
                 uploadable='true',
                 alarm_count=1):
        super(Notification, self).__init__()
        self.systemDN = system_dn
        self.liftedDN = lifted_dn
        self.alarmId = alarm_id
        self.specificProblem = specific_problem
        self.probableCause = probable_cause
        self.eventType = event_type
        self.alarmText = alarm_text
        self.originalSeverity = original_severity
        self.perceivedSeverity = perceived_severity
        self.additionalText1 = additional_text1
        self.additionalText2 = additional_text2
        self.additionalText3 = additional_text3
        self.additionalText4 = additional_text4
        self.additionalText5 = additional_text5
        self.additionalText6 = additional_text6
        self.additionalText7 = additional_text7
        self.notificationId = notification_id
        self.externalCorrelationId = external_correlation_id
        self.uploadable = uploadable
        self.alarmCount = alarm_count
        self.soap_template = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Header />
    <soapenv:Body>
    <nd:processNotification xmlns:nd="http://www.nokiasiemens.com/nd-callback" xmlns:dtos="http://dtos.notificationdispatcher.icf.interfaces.oss.nokia.com" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xx="http://xml.apache.org/xml-soap">
         <nd:in0>
            <dtos:QId>43151764:::203991170</dtos:QId>
            {attributeValueMap}
            <dtos:comparatorKey>com.nokia.oss.icf.notificationdispatcher.componentcomparator.OssComponentComparatorImpl</dtos:comparatorKey>
            <dtos:componentType>OES_FM</dtos:componentType>
            {mapMessage}
            <dtos:notificationType>{notificationType}</dtos:notificationType>
            {textMessage}
         </nd:in0>
    </nd:processNotification>         
   </soapenv:Body>
</soapenv:Envelope>   
        """.strip()
        self.attributeValueMap_template = """
            <dtos:attributeValueMap>
               {items}
               <xx:item>
                  <xx:key xsi:type="xs:string">nodeFilterId</xx:key>
                  <xx:value xsi:type="xs:string">9223372036854775806</xx:value>
               </xx:item>
               <xx:item>
                  <xx:key xsi:type="xs:string">FilterId</xx:key>
                  <xx:value xsi:type="xs:string">9223372032559808512</xx:value>
               </xx:item>
            </dtos:attributeValueMap>          
        """

    @property
    def event_time(self):
        return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")

    @property
    def new_alarm(self):
        _attributeValueMap = """
               <xx:item>
                  <xx:key xsi:type="xs:string">alarmCount</xx:key>
                  <xx:value xsi:type="xs:string">{alarmCount}</xx:value>
               </xx:item>
               <xx:item>
                  <xx:key xsi:type="xs:string">CorrelationFilterResult</xx:key>
                  <xx:value xsi:type="xs:string">{CorrelationFilterResult}</xx:value>
               </xx:item>        
        """.format(alarmCount=self.alarmCount, CorrelationFilterResult=self.externalCorrelationId).strip()
        attribute_value_map = self.attributeValueMap_template.format(items=_attributeValueMap)

        map_message = """
            <dtos:mapMessage>
               <dtos:mapData>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originalSeverity</xx:key>
                     <xx:value xsi:type="xs:string">{originalSeverity}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">neGid</xx:key>
                     <xx:value xsi:type="xs:string">46123483</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originalAlarmId</xx:key>
                     <xx:value xsi:type="xs:string">{originalAlarmId}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">liftedDN</xx:key>
                     <xx:value xsi:type="xs:string">{liftedDN}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originEventTime</xx:key>
                     <xx:value xsi:type="xs:string">{originEventTime}</xx:value>
                  </xx:item>
               </dtos:mapData>
            </dtos:mapMessage>        
        """.format(originalSeverity=self.originalSeverity,
                   originalAlarmId=self.notificationId,
                   liftedDN=self.liftedDN,
                   originEventTime=self.event_time).strip()

        text_message = """
<dtos:textMessage>
<dtos:text><![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<notification>
<alarmNew systemDN="{systemDN}">
<alarmId>{alarmId}</alarmId>
<specificProblem>{specificProblem}</specificProblem>
<probableCause>{probableCause}</probableCause>
<eventType>{eventType}</eventType>
<perceivedSeverity>{perceivedSeverity}</perceivedSeverity>
<eventTime>{eventTime}</eventTime>
<additionalText1>{additionalText1}</additionalText1>
<additionalText2>{additionalText2}</additionalText2>
<additionalText3>{additionalText3}</additionalText3>
<additionalText4>{additionalText4}</additionalText4>
<additionalText5>{additionalText5}</additionalText5>
<additionalText6>{additionalText6}</additionalText6>
<additionalText7>{additionalText7}</additionalText7>
<alarmText>{alarmText}</alarmText>
<alarmCount>{alarmCount}</alarmCount>
<uploadable>{uploadable}</uploadable>
</alarmNew>
</notification>]]>
</dtos:text>
</dtos:textMessage>
        """.format(systemDN=self.systemDN,
                   alarmId=self.alarmId,
                   specificProblem=self.specificProblem,
                   probableCause=self.probableCause,
                   eventType=self.eventType,
                   perceivedSeverity=self.perceivedSeverity,
                   eventTime=self.event_time,
                   additionalText1=self.additionalText1,
                   additionalText2=self.additionalText2,
                   additionalText3=self.additionalText3,
                   additionalText4=self.additionalText4,
                   additionalText5=self.additionalText5,
                   additionalText6=self.additionalText6,
                   additionalText7=self.additionalText7,
                   alarmText=self.alarmText,
                   alarmCount=self.alarmCount,
                   uploadable=self.uploadable).strip()
        return self.build_alarm_soap(attribute_value_map, map_message, text_message, "ALARM_NEW")

    @property
    def clear_alarm(self):
        _attributeValueMap = """
               <xx:item>
                  <xx:key xsi:type="xs:string">CorrelationFilterResult</xx:key>
                  <xx:value xsi:type="xs:string">{CorrelationFilterResult}</xx:value>
               </xx:item>        
        """.format(CorrelationFilterResult=self.externalCorrelationId).strip()
        attribute_value_map = self.attributeValueMap_template.format(items=_attributeValueMap)

        map_message = """
            <dtos:mapMessage>
               <dtos:mapData>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originalSeverity</xx:key>
                     <xx:value xsi:type="xs:string">{originalSeverity}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">alarmTime</xx:key>
                     <xx:value xsi:type="xs:string">{alarmTime}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">alarmText</xx:key>
                     <xx:value xsi:type="xs:string">{alarmText}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originalAlarmId</xx:key>
                     <xx:value xsi:type="xs:string">{originalAlarmId}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText2</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText2}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText3</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText3}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originEventTime</xx:key>
                     <xx:value xsi:type="xs:string">{originEventTime}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText1</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText1}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText6</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText6}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText7</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText7}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">neGid</xx:key>
                     <xx:value xsi:type="xs:string">46123483</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText4</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText4}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText5</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText5}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">liftedDN</xx:key>
                     <xx:value xsi:type="xs:string">{liftedDN}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originAlarmTime</xx:key>
                     <xx:value xsi:type="xs:string">{originAlarmTime}</xx:value>
                  </xx:item>
               </dtos:mapData>
            </dtos:mapMessage>        
        """.format(originalSeverity=self.originalSeverity,
                   alarmTime=self.event_time,
                   alarmText=self.alarmText,
                   originalAlarmId=self.notificationId,
                   additionalText1=self.additionalText1,
                   additionalText2=self.additionalText2,
                   additionalText3=self.additionalText3,
                   additionalText4=self.additionalText4,
                   additionalText5=self.additionalText5,
                   additionalText6=self.additionalText6,
                   additionalText7=self.additionalText7,
                   originEventTime=self.event_time,
                   liftedDN=self.liftedDN,
                   originAlarmTime=self.event_time)

        text_message = """
            <dtos:textMessage>
               <dtos:text><![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<notification>
<alarmCleared systemDN="{systemDN}">
<alarmId>{alarmId}</alarmId>
<specificProblem>{specificProblem}</specificProblem>
<probableCause>{probableCause}</probableCause>
<eventType>{eventType}</eventType>
<perceivedSeverity>cleared</perceivedSeverity>
<eventTime>{eventTime}</eventTime>
<clearUser>{clearUser}</clearUser>
</alarmCleared>
</notification>]]></dtos:text>
            </dtos:textMessage>        
        """.format(systemDN=self.systemDN,
                   alarmId=self.alarmId,
                   specificProblem=self.specificProblem,
                   probableCause=self.probableCause,
                   eventType=self.eventType,
                   perceivedSeverity=self.perceivedSeverity,
                   eventTime=self.event_time,
                   clearUser="RMB")
        return self.build_alarm_soap(attribute_value_map, map_message, text_message, "ALARM_CLEAR")

    @property
    def change_alarm(self):
        _attributeValueMap = """
               <xx:item>
                  <xx:key xsi:type="xs:string">alarmCount</xx:key>
                  <xx:value xsi:type="xs:string">{alarmCount}</xx:value>
               </xx:item>
               <xx:item>
                  <xx:key xsi:type="xs:string">CorrelationFilterResult</xx:key>
                  <xx:value xsi:type="xs:string">{CorrelationFilterResult}</xx:value>
               </xx:item>   
        """.format(alarmCount=self.alarmCount,
                   CorrelationFilterResult=self.externalCorrelationId)
        attribute_value_map = self.attributeValueMap_template.format(items=_attributeValueMap)

        map_message = """
            <dtos:mapMessage>
               <dtos:mapData>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originalSeverity</xx:key>
                     <xx:value xsi:type="xs:string">{originalSeverity}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">neGid</xx:key>
                     <xx:value xsi:type="xs:string">46123483</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originalAlarmId</xx:key>
                     <xx:value xsi:type="xs:string">{originalAlarmId}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">liftedDN</xx:key>
                     <xx:value xsi:type="xs:string">{liftedDN}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originEventTime</xx:key>
                     <xx:value xsi:type="xs:string">{originEventTime}</xx:value>
                  </xx:item>
               </dtos:mapData>
            </dtos:mapMessage>        
        """.format(originalSeverity=self.originalSeverity,
                   originalAlarmId=self.notificationId,
                   liftedDN=self.liftedDN,
                   originEventTime=self.event_time)
        text_message = """
            <dtos:textMessage>
               <dtos:text><![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<notification>
<alarmChanged systemDN="{systemDN}">
<alarmId>{alarmId}</alarmId>
<specificProblem>{specificProblem}</specificProblem>
<probableCause>{probableCause}</probableCause>
<eventType>{eventType}</eventType>
<perceivedSeverity>{perceivedSeverity}</perceivedSeverity>
<eventTime>{eventTime}</eventTime>
<additionalText1>{additionalText1}</additionalText1>
<additionalText2>{additionalText2}</additionalText2>
<additionalText3>{additionalText3}</additionalText3>
<additionalText4>{additionalText4}</additionalText4>
<additionalText5>{additionalText5}</additionalText5>
<additionalText6>{additionalText6}</additionalText6>
<additionalText7>{additionalText7}</additionalText7>
<alarmText>{alarmText}</alarmText>
<alarmCount>{alarmCount}</alarmCount>
</alarmChanged>
</notification>]]></dtos:text>
            </dtos:textMessage> 
        """.format(systemDN=self.systemDN,
                   alarmId=self.alarmId,
                   specificProblem=self.specificProblem,
                   probableCause=self.probableCause,
                   eventType=self.eventType,
                   perceivedSeverity=self.perceivedSeverity,
                   eventTime=self.event_time,
                   additionalText1="updated {}".format(self.additionalText1),
                   additionalText2="updated {}".format(self.additionalText2),
                   additionalText3="updated {}".format(self.additionalText3),
                   additionalText4="updated {}".format(self.additionalText4),
                   additionalText5="updated {}".format(self.additionalText5),
                   additionalText6="updated {}".format(self.additionalText6),
                   additionalText7="updated {}".format(self.additionalText7),
                   alarmText="updated {}".format(self.alarmText),
                   alarmCount=self.alarmCount)
        return self.build_alarm_soap(attribute_value_map, map_message, text_message, "ALARM_STATE_CHG")

    @property
    def ack_alarm(self):
        return self._ackalarm("acked")

    @property
    def unack_alarm(self):
        return self._ackalarm("acked")

    def _ackalarm(self, ack_change):
        _attributeValueMap = """
               <xx:item>
                  <xx:key xsi:type="xs:string">CorrelationFilterResult</xx:key>
                  <xx:value xsi:type="xs:string">{CorrelationFilterResult}</xx:value>
               </xx:item>        
        """.format(CorrelationFilterResult=self.externalCorrelationId).strip()
        attribute_value_map = self.attributeValueMap_template.format(items=_attributeValueMap)

        map_message = """
            <dtos:mapMessage>
               <dtos:mapData>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originalSeverity</xx:key>
                     <xx:value xsi:type="xs:string">{originalSeverity}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">alarmTime</xx:key>
                     <xx:value xsi:type="xs:string">{alarmTime}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">alarmText</xx:key>
                     <xx:value xsi:type="xs:string">{alarmText}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originalAlarmId</xx:key>
                     <xx:value xsi:type="xs:string">{originalAlarmId}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText2</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText2}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText3</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText3}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originEventTime</xx:key>
                     <xx:value xsi:type="xs:string">{originEventTime}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText1</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText1}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText6</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText6}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText7</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText7}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">neGid</xx:key>
                     <xx:value xsi:type="xs:string">46123483</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText4</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText4}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">additionalText5</xx:key>
                     <xx:value xsi:type="xs:string">{additionalText5}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">liftedDN</xx:key>
                     <xx:value xsi:type="xs:string">{liftedDN}</xx:value>
                  </xx:item>
                  <xx:item>
                     <xx:key xsi:type="xs:string">originAlarmTime</xx:key>
                     <xx:value xsi:type="xs:string">{originAlarmTime}</xx:value>
                  </xx:item>
               </dtos:mapData>
            </dtos:mapMessage>        
        """.format(originalSeverity=self.originalSeverity,
                   alarmTime=self.event_time,
                   alarmText=self.alarmText,
                   originalAlarmId=self.notificationId,
                   additionalText1=self.additionalText1,
                   additionalText2=self.additionalText2,
                   additionalText3=self.additionalText3,
                   additionalText4=self.additionalText4,
                   additionalText5=self.additionalText5,
                   additionalText6=self.additionalText6,
                   additionalText7=self.additionalText7,
                   originEventTime=self.event_time,
                   liftedDN=self.liftedDN,
                   originAlarmTime=self.event_time)
        if ack_change == "acked":
            text_message = """
            <dtos:textMessage>
               <dtos:text><![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<notification>
<ackStateChanged systemDN="{systemDN}">
<alarmId>{alarmId}</alarmId>
<specificProblem>{specificProblem}</specificProblem>
<probableCause>{probableCause}</probableCause>
<eventType>{eventType}</eventType>
<perceivedSeverity>{perceivedSeverity}</perceivedSeverity>
<eventTime>{eventTime}</eventTime>
<ackStatus>{ackStatus}</ackStatus>
<ackUser>{ackUser}</ackUser>
</ackStateChanged>
</notification>]]></dtos:text>
            </dtos:textMessage>        
            """.format(systemDN=self.systemDN,
                       alarmId=self.alarmId,
                       specificProblem=self.specificProblem,
                       probableCause=self.probableCause,
                       eventType=self.eventType,
                       perceivedSeverity=self.perceivedSeverity,
                       eventTime=self.event_time,
                       ackStatus=ack_change,
                       ackUser="RMB")
        else:
            text_message = """
            <dtos:textMessage>
               <dtos:text><![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<notification>
<ackStateChanged systemDN="{systemDN}">
<alarmId>{alarmId}</alarmId>
<specificProblem>{specificProblem}</specificProblem>
<probableCause>{probableCause}</probableCause>
<eventType>{eventType}</eventType>
<perceivedSeverity>{perceivedSeverity}</perceivedSeverity>
<eventTime>{eventTime}</eventTime>
<ackStatus>{ackStatus}</ackStatus>
</ackStateChanged>
</notification>]]></dtos:text>
            </dtos:textMessage>        
                    """.format(systemDN=self.systemDN,
                               alarmId=self.alarmId,
                               specificProblem=self.specificProblem,
                               probableCause=self.probableCause,
                               eventType=self.eventType,
                               perceivedSeverity=self.perceivedSeverity,
                               eventTime=self.event_time,
                               ackStatus=ack_change)
        return self.build_alarm_soap(attribute_value_map, map_message, text_message, "ACK_STATE_CHG")

    def build_alarm_soap(self, attribute_value_map, map_message, text_message, notification_type):
        return self.soap_template.format(attributeValueMap=attribute_value_map.strip(), mapMessage=map_message.strip(),
                                         textMessage=text_message.strip(), notificationType=notification_type.strip())


class HTTP(Thread):

    def __init__(self, identify):
        super(HTTP, self).__init__()
        self._running = True
        self.id = identify
        self.node = None
        self.soap_list = []

    def run(self):
        global SOAP_QUEUE
        process_count = 0
        start_time = time.time()
        while self._running:
            try:
                soap = SOAP_QUEUE.get(timeout=1)
                self.soap_list.append(soap)
            except Exception as err:
                continue
            else:
                if len(self.soap_list) > 200:
                    process_count += len(self.soap_list)
                    success_count = self.post_soap(self.soap_list)
                    self.soap_list = []
                    Logger.debug(
                        "POSTER-{}, send success: {}".format(self.id, success_count))
                if time.time() - start_time > 30:
                    start_time = time.time()
                    process_count = 0
        Logger.error("POSTER-{} exit".format(self.id))

    @property
    def restda_fm_node(self):
        if not self.node:
            self.node = SearchService.get_restda_fm_node()
        return self.node

    def post_soap(self, soap_list):
        success_count = 0
        url = "http://{node}.netact.nsn-rdnet.net:9529/nd-callback/NotificationWSCallbackInterfaceService".format(
            node=self.restda_fm_node)
        s = requests.Session()
        for soap in soap_list:
            Logger.debug(soap)
            try:
                r = s.post(url, data=soap)
                Logger.debug(r.text)
            except Exception as err:
                Logger.error("post error, reason: {}".format(err))
                time.sleep(2)
            else:
                if r.status_code == 200:
                    success_count += 1
                else:
                    Logger.error("response error: {}".format(r.text))
        s.close()
        return success_count

    def post(self, soap_list):
        self.soap_list += soap_list

    def stop(self):
        self._running = False


class Alarms(object):
    def __init__(self):
        super(Alarms, self).__init__()
        self._dn_list = []
        self.http_threader = []

    @property
    def dn_list(self):
        if not self._dn_list:
            self._dn_list = self._extract_dns()
        return self._dn_list

    @staticmethod
    def _extract_dns():
        # only read nasda table
        sql = "select co_dn from nasda_objects"
        out = execute_sqlplus_command(sql)
        nasdas = out.split('\n')
        pattern = re.compile(r'^PLMN-[a-zA-Z0-9-]+/[a-zA-Z0-9-]+')
        nasdas = filter(lambda nasda: pattern.match(nasda), nasdas)
        dn_list = list(map(lambda nasda: pattern.match(nasda).group(), nasdas))
        if 'PLMN-PLMN/NETACT-12345678' in dn_list:
            dn_list.remove('PLMN-PLMN/NETACT-12345678')
        if not dn_list:
            Logger.error('nasda has 0 objects.')
            exit(1)
        else:
            Logger.info('extract {} mo from nasda table'.format(len(dn_list)))
            return dn_list

    def send_alarms(self, count=4):
        global SOAP_QUEUE
        start_time = time.time()
        warning_ratio = 0.57
        critical_ratio = 0.43
        warning_count = int(warning_ratio * count / 3)
        critical_count = int(critical_ratio * count / 4)
        for i in range(critical_count):
            notifier = Notification(system_dn=random.choice(self.dn_list), lifted_dn='PLMN-PLMN', alarm_id=30000001)
            SOAP_QUEUE.put(notifier.new_alarm)
            SOAP_QUEUE.put(notifier.ack_alarm)
            SOAP_QUEUE.put(notifier.change_alarm)
            SOAP_QUEUE.put(notifier.clear_alarm)
        for i in range(warning_count):
            notifier = Notification(system_dn=random.choice(self.dn_list), lifted_dn='PLMN-PLMN', alarm_id=30000002,
                                    perceived_severity="warning")
            SOAP_QUEUE.put(notifier.new_alarm)
            SOAP_QUEUE.put(notifier.ack_alarm)
            SOAP_QUEUE.put(notifier.clear_alarm)
        while not SOAP_QUEUE.empty():
            time.sleep(0.2)
        return time.time() - start_time

    def _is_burst(self):
        current_time = datetime.datetime.now()
        for _burst_time_range in self._burst_time_range_list:
            if _burst_time_range[0] < current_time < _burst_time_range[1]:
                return True
        return False

    def _is_peak(self):
        current_time = datetime.datetime.now()
        for _peak_time_range in self._peak_time_range_list:
            if _peak_time_range[0] < current_time < _peak_time_range[1]:
                return True
        return False

    @property
    def _burst_time_range_list(self):
        return [(self._get_today_timestamp(_date='16:00'), self._get_today_timestamp(_date='17:00'))]

    @property
    def _peak_time_range_list(self):
        return [(self._get_today_timestamp(_date='04:00'), self._get_today_timestamp(_date='04:05')),
                (self._get_today_timestamp(_date='12:00'), self._get_today_timestamp(_date='12:05')),
                (self._get_today_timestamp(_date='20:00'), self._get_today_timestamp(_date='20:05'))]

    @staticmethod
    def _get_today_timestamp(_date="00:00"):
        return datetime.datetime.strptime(str(datetime.datetime.now().date()) + _date, '%Y-%m-%d%H:%M')

    def get_batch_size(self, constant, burst, peak, forceburst, forcepeak):
        if forceburst:
            return burst
        elif forcepeak:
            return peak
        elif self._is_burst():
            return burst
        elif self._is_peak():
            return burst
        else:
            return constant


def init_poster(thread_count):
    http_threader_list = [HTTP(i) for i in range(thread_count)]
    for t in http_threader_list:
        t.start()
    return http_threader_list


def batched_create_alarms(constant, burst, peak, interval, forceburst, forcepeak, dn, thread_count):
    global SOAP_QUEUE
    SOAP_QUEUE = Queue()
    http_threader_list = init_poster(thread_count)
    o = Alarms()
    previous_timestamp = time.time()
    while 1:
        http_status = [1 if http.is_alive() else 0 for http in http_threader_list]
        current_timestamp = time.time()
        cost_time = current_timestamp - previous_timestamp
        if cost_time > interval:
            alarm_count = o.get_batch_size(constant, burst, peak, forceburst, forcepeak)
            cost = o.send_alarms(alarm_count * interval)
            Logger.info("send event count: {}, total cost: {}, throughput: {}/s, dn: {}, Poster: {}".format(
                alarm_count * interval, cost, int(alarm_count * interval / cost_time),
                dn if dn else '@auto', sum(http_status)))
            previous_timestamp = current_timestamp
        else:
            time.sleep(0.1)


def exit_tool(sig, frame):
    Logger.debug('Press Ctrl+C, exit.')
    exit(0)


def args_parser():
    opt = optparse.OptionParser(version=1)
    opt.add_option("--constant", action='store', help="constant count of FM events, default is 150.", type=int,
                   dest="constant", default=150)
    opt.add_option("--burst", action='store', help="burst count of FM events, default is 470. duration: 16:00~17:00",
                   type=int,
                   dest="burst", default=470)
    opt.add_option("--peak", action='store',
                   help="peak count of FM events, default is 1170. duration: 4:00~4:05, 12:00~12:05, 20:00~20:05",
                   type=int, dest="peak",
                   default=1170)
    opt.add_option("--interval", action='store', help="interval of FM events sent, default is 10.", type=int,
                   dest="interval", default=10)
    opt.add_option("--forceburst", action='store_true', help="force burst scenario", dest="forceburst", default=False)
    opt.add_option("--forcepeak", action='store_true', help="force peak scenario", dest="forcepeak", default=False)
    opt.add_option("--dn", action='store', help="specified dn", dest="dn")
    opt.add_option("--thread", action='store', help="thread count, default is 1", dest="thread", default=1, type=int)
    opt.add_option("--debug", action='store_true', help="debug level", dest="debug", default=False)
    _options, args = opt.parse_args()
    return _options


class Deamon(object):
    def __init__(self, constant, burst, peak, interval, forceburst, forcepeak, dn, thread_count):
        super(Deamon, self).__init__()
        self.running = True
        self.constant = constant
        self.burst = burst
        self.peak = peak
        self.interval = interval
        self.forceburst = forceburst
        self.forcepeak = forcepeak
        self.dn = dn
        self.thread_count = thread_count

    def stop(self):
        self.running = False

    def fork(self):
        try:
            pid = os.fork()
        except OSError as err:
            print('fork failed: {}'.format(err))
            sys.exit(1)
        if pid == 0:
            # this is child process
            os.chdir("/")
            os.setsid()
            os.umask(0)
            # fork a Grandson process, and child process exit
            try:
                pid = os.fork()
                if pid > 0:
                    # exit child process
                    sys.exit(0)
            except OSError as err:
                print('fork failed: {}'.format(err))
                sys.exit(1)
            # this is Grandson process
            self.run()
            # exit Grandson process
            sys.exit(0)
        else:
            # this is parent process . nothing to do.
            pass

    def run(self):
        batched_create_alarms(self.constant, self.burst, self.peak, self.interval, self.forceburst, self.forcepeak,
                              self.dn, self.thread_count)
        Logger.info("main process exit")


if __name__ == '__main__':
    signal.signal(signal.SIGINT, exit_tool)
    options = args_parser()
    if options.debug:
        Logger.enable_debug()
    Logger.info("*********************Simulator*****************************")
    Logger.info("specified dn is: {}".format(options.dn))
    Logger.info("constant count of event is: {}".format(options.constant))
    Logger.info("burst count of event is: {}".format(options.burst))
    Logger.info("peak count of event is: {}".format(options.peak))
    Logger.info("interval is: {}".format(options.interval))
    Logger.info("force burst is: {}".format(options.forceburst))
    Logger.info("force peak is: {}".format(options.forcepeak))
    Logger.info("debug is: {}".format(options.debug))
    if options.forceburst and options.forcepeak:
        Logger.info("Conflict with --forceburst and --forcepeak, only one can be specified")
        exit(1)
    d = Deamon(options.constant, options.burst, options.peak, options.interval, options.forceburst, options.forcepeak,
               options.dn, options.thread)
    d.fork()

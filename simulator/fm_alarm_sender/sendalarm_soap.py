#!/usr/bin/env python
# coding=utf-8
from subprocess import Popen, PIPE
import datetime
import random
import optparse
import logging
from os.path import exists, isfile
from os import remove
import sys

VERSION = '1.0'


def convert_to_str(content):
    if sys.version_info.major == 3:
        content = content.decode('utf-8') if isinstance(content, (bytes, bytearray)) else content
    return content


def convert_to_system_format(content):
    if sys.version_info.major == 3:
        content = bytes(content, 'utf-8') if isinstance(content, str) else content
    return content


class Logger(object):
    logger = logging.getLogger("Logger")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    @classmethod
    def info(cls, message):
        message = message.strip()
        cls.logger.info(message)

    @classmethod
    def error(cls, message):
        message = message.strip()
        cls.logger.error(message)

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
        Logger.debug("stdout: {}".format(convert_to_str(stdout)))
        Logger.debug("stderr: {}".format(convert_to_str(stderr)))
        Logger.debug("rc: {}".format(rc))
    return stdout, stderr, rc


class SearchService(object):
    def __init__(self):
        super(SearchService, self).__init__()

    @staticmethod
    def _get_service_node_and_status_by_smanager(service):
        stdout, stderr, rc = execute_command("smanager.pl status service ^{}$".format(service))
        if rc:
            Logger.error("smanager failed, error:{}".format(convert_to_str(stderr)))
            exit(1)
        else:

            host = stdout.split(convert_to_system_format(":"))[1]
            status = stdout.split(convert_to_system_format(":"))[-1]
            return host, status

    @classmethod
    def get_restda_fm_node(cls):
        host, status = cls._get_service_node_and_status_by_smanager("restda-fm")
        if status == convert_to_system_format(convert_to_system_format("started")):
            return host
        else:
            Logger.error("restda-fm is: {}".format(convert_to_str(status)))
            exit(1)


class Notification(object):
    def __init__(self, kw):
        super(Notification, self).__init__()
        self.systemDN = kw.systemDN
        self.liftedDN = kw.liftedDN
        self.alarmId = kw.alarmId
        self.eventTime = kw.eventTime
        self.specificProblem = kw.specificProblem
        self.probableCause = kw.probableCause
        self.eventType = kw.eventType
        self.alarmText = kw.alarmText
        self.originalSeverity = kw.originalSeverity
        self.perceivedSeverity = kw.perceivedSeverity
        self.additionalText1 = kw.additionalText1
        self.additionalText2 = kw.additionalText2
        self.additionalText3 = kw.additionalText3
        self.additionalText4 = kw.additionalText4
        self.additionalText5 = kw.additionalText5
        self.additionalText6 = kw.additionalText6
        self.additionalText7 = kw.additionalText7
        self.notificationId = kw.notificationId
        self.externalCorrelationId = kw.externalCorrelationId
        self.uploadable = kw.uploadable
        self.alarmCount = kw.alarmCount
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

    def newalarm(self):
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
        attributeValueMap = self.attributeValueMap_template.format(items=_attributeValueMap)
        mapMessage = """
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
                   originEventTime=self.eventTime).strip()

        textMessage = """
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
                   eventTime=self.eventTime,
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
        self.send_alarm(attributeValueMap, mapMessage, textMessage, "ALARM_NEW")

    def clear(self):
        _attributeValueMap = """
               <xx:item>
                  <xx:key xsi:type="xs:string">CorrelationFilterResult</xx:key>
                  <xx:value xsi:type="xs:string">{CorrelationFilterResult}</xx:value>
               </xx:item>        
        """.format(CorrelationFilterResult=self.externalCorrelationId).strip()
        attributeValueMap = self.attributeValueMap_template.format(items=_attributeValueMap)

        mapMessage = """
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
                   alarmTime=self.eventTime,
                   alarmText=self.alarmText,
                   originalAlarmId=self.notificationId,
                   additionalText1=self.additionalText1,
                   additionalText2=self.additionalText2,
                   additionalText3=self.additionalText3,
                   additionalText4=self.additionalText4,
                   additionalText5=self.additionalText5,
                   additionalText6=self.additionalText6,
                   additionalText7=self.additionalText7,
                   originEventTime=self.eventTime,
                   liftedDN=self.liftedDN,
                   originAlarmTime=self.eventTime)

        textMessage = """
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
                   eventTime=self.eventTime,
                   clearUser="RMB")
        self.send_alarm(attributeValueMap, mapMessage, textMessage, "ALARM_CLEAR")

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
        attributeValueMap = self.attributeValueMap_template.format(items=_attributeValueMap)

        mapMessage = """
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
                   originEventTime=self.eventTime)
        textMessage = """
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
                   eventTime=self.eventTime,
                   additionalText1=self.additionalText1,
                   additionalText2=self.additionalText2,
                   additionalText3=self.additionalText3,
                   additionalText4=self.additionalText4,
                   additionalText5=self.additionalText5,
                   additionalText6=self.additionalText6,
                   additionalText7=self.additionalText7,
                   alarmText=self.alarmText,
                   alarmCount=self.alarmCount)
        self.send_alarm(attributeValueMap, mapMessage, textMessage, "ALARM_STATE_CHG")

    def ackalarm(self, ack_change):
        _attributeValueMap = """
               <xx:item>
                  <xx:key xsi:type="xs:string">CorrelationFilterResult</xx:key>
                  <xx:value xsi:type="xs:string">{CorrelationFilterResult}</xx:value>
               </xx:item>        
        """.format(CorrelationFilterResult=self.externalCorrelationId).strip()
        attributeValueMap = self.attributeValueMap_template.format(items=_attributeValueMap)

        mapMessage = """
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
                   alarmTime=self.eventTime,
                   alarmText=self.alarmText,
                   originalAlarmId=self.notificationId,
                   additionalText1=self.additionalText1,
                   additionalText2=self.additionalText2,
                   additionalText3=self.additionalText3,
                   additionalText4=self.additionalText4,
                   additionalText5=self.additionalText5,
                   additionalText6=self.additionalText6,
                   additionalText7=self.additionalText7,
                   originEventTime=self.eventTime,
                   liftedDN=self.liftedDN,
                   originAlarmTime=self.eventTime)
        if ack_change == "acked":
            textMessage = """
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
                       eventTime=self.eventTime,
                       ackStatus=ack_change,
                       ackUser="RMB")
        else:
            textMessage = """
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
                               eventTime=self.eventTime,
                               ackStatus=ack_change)
        self.send_alarm(attributeValueMap, mapMessage, textMessage, "ACK_STATE_CHG")

    def send_alarm(self, attributeValueMap, mapMessage, textMessage, notificationType):
        self.send(self.soap_template.format(attributeValueMap=attributeValueMap.strip(), mapMessage=mapMessage.strip(),
                                            textMessage=textMessage.strip(), notificationType=notificationType.strip()))

    def send(self, soap):
        Logger.debug(soap)
        with open("alarm.soap", 'w') as f:
            f.write(soap)
        command = """wget --post-file=alarm.soap --header=content-type:"text/xml; charset=UTF-8" http://{node}.netact.nsn-rdnet.net:9529/nd-callback/NotificationWSCallbackInterfaceService""".format(
            node=convert_to_str(self.restda_fm_node))
        stdout, stderr, rc = execute_command(command)
        if rc:
            Logger.error("send soap failed, error: {}".format(convert_to_str(stderr)))
            exit(1)
        else:
            Logger.info("alarmId: {}".format(convert_to_str(self.alarmId)))
            Logger.info("send soap successful.")
            self.remove_response_file()
            exit(0)

    @staticmethod
    def remove_response_file():
        response_file = "NotificationWSCallbackInterfaceService"
        if exists(response_file) and isfile(response_file):
            remove(response_file)

    @property
    def restda_fm_node(self):
        return SearchService.get_restda_fm_node()


def args_parser():
    operation_choice = ['new', 'ack', 'unack', 'change', 'clear']
    severity_choice = ['critical', 'major', 'minor', 'minor', 'warning', 'indeterminate']
    event_type_choice = ['communication', 'processingError', 'environmental', 'qualityOfService', 'equipment']
    event_time_default = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    alarm_id_default = random.randint(1, 2 ** 31 - 1)
    notification_id_default = random.randint(1, 10000)
    uploadable_choice = ['true', 'false']
    external_correlation_id_choice = ['00', '01', '10']
    opt = optparse.OptionParser(version=VERSION)
    opt.add_option("-o", action='store', help="Mandatory, operation allow: {}".format(operation_choice),
                   dest="operation", choices=operation_choice)
    opt.add_option("--systemDN", action='store', help="System Distinguished name of the alarming object",
                   dest="systemDN",
                   default="PLMN-PLMN/MRBTS-1")
    opt.add_option("--liftedDN", action='store', help="lifted Distinguished name of the alarming object",
                   dest="liftedDN",
                   default="PLMN-PLMN/MRBTS-1")
    opt.add_option("--alarmId", action='store', help="Alarm identifier", dest="alarmId", default=alarm_id_default)
    opt.add_option("--eventTime", action='store', help="Time the event was generated", dest="eventTime",
                   default=event_time_default)
    opt.add_option("--specificProblem", action='store', help="Qualification of the fault", dest="specificProblem",
                   default="50000")
    opt.add_option("--probableCause", action='store', help="Probable cause of the event", dest="probableCause",
                   default="81")
    opt.add_option("--eventType", action='store', help="Type of the event.", dest="eventType",
                   default=event_type_choice[0],
                   choices=event_type_choice)
    opt.add_option("--alarmText", action='store', help="Textual description of the fault", dest="alarmText",
                   default="send by sendalarm_soap.py")
    opt.add_option("--originalSeverity", action='store', help="Original severity of the alarm", dest="originalSeverity",
                   default=severity_choice[-1], choices=severity_choice)
    opt.add_option("--perceivedSeverity", action='store', help="Severity of the alarm", dest="perceivedSeverity",
                   default=severity_choice[0], choices=severity_choice)
    opt.add_option("--additionalText1", action='store', help="Additional information on the fault",
                   dest="additionalText1",
                   default="this is additionalText1")
    opt.add_option("--additionalText2", action='store', help="Further additional information on the fault",
                   dest="additionalText2",
                   default="this is additionalText2")
    opt.add_option("--additionalText3", action='store', help="Further additional information on the fault",
                   dest="additionalText3",
                   default="this is additionalText3")
    opt.add_option("--additionalText4", action='store', help="Further additional information on the fault",
                   dest="additionalText4",
                   default="this is additionalText4")
    opt.add_option("--additionalText5", action='store', help="Further additional information on the fault",
                   dest="additionalText5",
                   default="this is additionalText5")
    opt.add_option("--additionalText6", action='store', help="Further additional information on the fault",
                   dest="additionalText6",
                   default="this is additionalText6")
    opt.add_option("--additionalText7", action='store', help="Further additional information on the fault",
                   dest="additionalText7",
                   default="this is additionalText7")
    opt.add_option("--notificationId", action='store', help="Notification Identifier", dest="notificationId",
                   default=notification_id_default)
    opt.add_option("--externalCorrelationId", action='store',
                   help="For a correlated (child) alarm this should be equal to the externalNotificationId of correlating alarm",
                   dest="externalCorrelationId", default=external_correlation_id_choice[0],
                   choices=external_correlation_id_choice)
    opt.add_option("--uploadable", action='store', help="Indicates if an alarm is uploadable or not",
                   dest="uploadable",
                   default=uploadable_choice[0], choices=uploadable_choice)
    opt.add_option("--alarmCount", action='store', help="Indicates the bucketed alarm count at the NE side",
                   dest="alarmCount",
                   default=1, type=int)
    opt.add_option("--debug", action='store_true', help="enable debug log", dest="debug")
    _options, args = opt.parse_args()
    return _options


def check_args(_options):
    if not _options.operation:
        Logger.error("please specific argument -o")
        exit(1)


if __name__ == '__main__':
    options = args_parser()
    check_args(options)
    if options.debug:
        Logger.enable_debug()
    if options.operation == "new":
        notify = Notification(options)
        notify.newalarm()
    elif options.operation == "ack":
        notify = Notification(options)
        notify.ackalarm("acked")
    elif options.operation == "unack":
        notify = Notification(options)
        notify.ackalarm("unacked")
    elif options.operation == "change":
        notify = Notification(options)
        notify.change_alarm()
    elif options.operation == "clear":
        notify = Notification(options)
        notify.clear()

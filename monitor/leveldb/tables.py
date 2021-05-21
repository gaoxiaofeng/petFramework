#!/usr/bin/env python
# coding=utf-8
class Topology(object):
    column_name = ["DN",
                   "NAME",
                   "ADAP_ID",
                   "MOCLASS",
                   "ADAP_VERSION",
                   "HOST_ADDRESS",
                   "LATITUDE",
                   "LONGITUDE",
                   "MCC",
                   "MNC",
                   "LAC",
                   "CELL_ID",
                   "lastupdate"]


class FmAlarm(object):
    column_name = ["alarm_id",
                   "dn",
                   "lifted_dn",
                   "alarm_number",
                   "notification_id",
                   "original_severity",
                   "severity",
                   "alarm_time",
                   "ack_status",
                   "ack_time",
                   "acked_by",
                   "event_type",
                   "probable_cause",
                   "alarm_text",
                   "additionaltext1",
                   "additionaltext2",
                   "additionaltext3",
                   "additionaltext4",
                   "additionaltext5",
                   "additionaltext6",
                   "additionaltext7",
                   "alarm_count",
                   "root_cause_alarm",
                   "lastupdate"]

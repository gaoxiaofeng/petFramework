import datetime

from Cases._BaseCase import _BaseCase


class _RestdaCase(_BaseCase):
    def __init__(self):
        super(_RestdaCase, self).__init__()
        self.workingSets = ['GSM',
                            'WCDMA',
                            'SBTS',
                            'SBTS_CM',
                            "5G",
                            "CSCF"]
        # self.measurements_sbts = [
        #     ["noklte", "LMAC,LMAC1,LMAC2"],
        #     ["noklte","LCELLD,LCELLD1,LCELLD2"],
        #     ["noklte", "LENBLD,LENBLD1,LENBLD2"],
        #     ["noklte", "LRRC,LRRC1,LRRC2"],
        #     ["noklte", "LIENBHO,LIENBHO1,LIENBHO2"],
        #     ["noklte", "LCELLR,LCELLR1,LCELLR2"],
        #     ["noklte", "LCELAV,LCELAV1,LCELAV2"],
        #     ["noklte", "LCELLT,LCELLT1,LCELLT2"],
        #     ["noklte", "LX2AP,LX2AP1,LX2AP2"],
        #     ["noklte", "LIANBHO,LIANBHO1,LIANBHO2"],
        #     ["noklte", "LS1AP,LS1AP1,LS1AP2"],
        #     ["noklte", "LEPSB,LEPSB1,LEPSB2"],
        #     ["noklte", "LHO,LHO1,LHO2"],
        #     ["noklte", "LRDB,LRDB1,LRDB2"],
        #     ["noklte", "LUESD,LUESD1,LUESD2"],
        #     ["noklte", "LTRLD,LTRLD1,LTRLD2"],
        #     ["noklte", "LHORLF,LHORLF1,LHORLF2"],
        #     ["noklte", "LUEST,LUEST1,LUEST2"],
        #     ["noklte", "LQOS,LQOS1,LQOS2"]
        # ]
        self.measurements_sbts = [
            ["noklte", "LTE_Cell_Load"],
            ["noklte", "LTE_Pwr_and_Qual_UL"],
            ["noklte", "LTE_Cell_Resource"],
            ["noklte", "LTE_Cell_Throughput"],
            ["noklte", "LTE_EPS_Bearer"],
            ["noklte", "LTE_MAC"],
            ["noklte", "LTE_Pwr_and_Qual_DL"],
            ["noklte", "LTE_UE_State"],
            ["noklte", "LTE_QoS"],
            ["noklte", "LTE_Inter_eNB_HO"],
            ["noklte", "LTE_Handover"],
            ["noklte", "LTE_RRC"],
            ["noklte", "LTE_UE_and_ServDiff"],
            ["noklte", "LTE_Radio_Bearer"],
            ["noklte", "LTE_Intra_eNB_HO"],
            ["noklte", "LTE_Cell_Avail"],
            ["noklte", "LTE_HO_RLF_trigger"],
            ["noklte", "LTE_S1AP"],
            ["noklte", "LTE_eNB_Load"],
            ["noklte", "LTE_Transport_Load"],
            ["noklte", "LTE_X2AP"],
        ]

    def the_day_before(self, days=0, hours=0, minutes=0, seconds=0):
        return (datetime.datetime.now() - datetime.timedelta(days=days, hours=hours, minutes=minutes,
                                                             seconds=seconds)).strftime(self.DateFormat)

    def the_day_after(self, days=0, hours=0, minutes=0, seconds=0):
        return (datetime.datetime.now() + datetime.timedelta(days=days, hours=hours, minutes=minutes,
                                                             seconds=seconds)).strftime(self.DateFormat)

    def the_day_now(self):
        return datetime.datetime.now().strftime(self.DateFormat)

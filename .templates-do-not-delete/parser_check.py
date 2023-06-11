"""
Copyright 2022 Maen Artimy

"""

import os
import pyparsing as pp
import pandas as pd
from rich.console import Console


console = Console(color_system="truecolor")

# This code verifies if a Cisco device configuration includes lines
# similar to the following:
#
# clock timezone AST -4 0
# clock summer-time ADT recurring
#
# snmp-server community public RO
# snmp-server community private RW
# snmp-server location my_location
# snmp-server contact admin@domain
#
# logging host 10.1.155.100

SNMP_END_MARKER = pp.LineEnd().suppress()
REMAINDER = pp.SkipTo(pp.LineEnd())

NUM = 5
PATH = "lab/configs"
READ_COL = "Read"
SERVER_COL = "Host"
HRS_COL = "HRS"
ref_string = set(["dcread"])
ref_log_server = set(["10.1.155.100"])
TIME_SHIFT = "-4"
SUMR_COL = "Summer"
ADT = "ADT"


class ConfigValues:
    """
    Collects values from configuration
    """

    def __init__(self, cfg_list):
        self.cfg_list = cfg_list
        self.results = []
        self.header = {"Node": ""}
        self.repeated = []

    def a_parser(self, text):
        """Parse configuration"""
        return []

    def parse(self, device, cfg_lines):
        """
        Parse configuration lines and return dict

        """

        # parse text and return a list of dict
        log_lines = self.a_parser(cfg_lines)
        log_list = [p.asDict() for p in log_lines if p]

        # merge all dictionaries but there may be
        # multiple read and readwrite communities
        merged = self.header.copy()
        # merged.update(self.header)
        merged["Node"] = device
        for col in self.repeated:
            merged[col] = []
        for lines in log_list:
            for key, value in lines.items():
                if key in self.repeated:
                    merged[key].append(value)
                else:
                    merged[key] = value
        return merged

    def answer(self):
        """
        returns a list if parsed values

        """

        for filename in self.cfg_list:
            with open(filename, "r") as fgfile:
                cfg = fgfile.read()
                device = os.path.basename(filename)
                self.results.append(self.parse(device, cfg))
        return self

    def frame(self):
        """
        Format as pandas frame
        """

        return pd.DataFrame(self.results)


class ClockValues(ConfigValues):
    """
    Collects Clock values from configuration
    """

    def __init__(self, cfg_list):
        super().__init__(cfg_list)

        self.header = {
            "Node": "",
            "Zone": "",
            "HRS": "",
            "MIN": "",
            "Summer": "",
            "Recurring": "",
        }
        self.repeated = []

    def a_parser(self, text):
        """
        Parse SysLog configuration.
        """

        CLK_START_MARKER = pp.LineStart() + pp.Keyword("clock").suppress()
        CLK_TIMEZONE = pp.Keyword("timezone").suppress()
        CLK_ZONE = pp.Word(pp.printables, asKeyword=True)
        CLK_HRS = pp.Combine(pp.Optional("+") + pp.Optional("-") + pp.Word(pp.nums))(
            "HRS"
        )
        CLK_MIN = pp.Word(pp.nums)("MIN")
        CLK_SUMMER = pp.Keyword("summer-time").suppress()
        CLK_REC = pp.Keyword("recurring").setParseAction(pp.replaceWith("enabled"))

        clock_timezone = (
            CLK_START_MARKER + CLK_TIMEZONE + CLK_ZONE("Zone") + CLK_HRS + CLK_MIN
        )
        clock_summertime = (
            CLK_START_MARKER + CLK_SUMMER + CLK_ZONE("Summer") + CLK_REC("Recurring")
        )

        command_def = clock_timezone ^ clock_summertime
        return command_def.searchString(text)


class LoggerValues(ConfigValues):
    """
    Collects SysLog values from configuration
    """

    def __init__(self, cfg_list):
        super().__init__(cfg_list)

        self.header = {"Node": "", "Host": []}
        self.repeated = ["Host"]

    def a_parser(self, text):
        """
        Parse SysLog configuration.
        """

        LOG_START_MARKER = pp.LineStart() + pp.Keyword("logging").suppress()
        LOG_HOST = pp.Keyword("host").suppress()

        log_host = LOG_START_MARKER + LOG_HOST + REMAINDER("Host")

        command_def = log_host
        return command_def.searchString(text)


class SNMPValues(ConfigValues):
    """
    Collects SNMP values from configuration
    """

    def __init__(self, cfg_list):
        super().__init__(cfg_list)
        self.header = {
            "Node": "",
            "Read": [],
            "Write": [],
            "Location": "",
            "Contact": "",
        }
        self.repeated = ["Read", "Write"]

    def a_parser(self, text):
        """
        Parse SNMP configuration.
        """

        SNMP_START_MARKER = pp.LineStart() + pp.Keyword("snmp-server").suppress()
        SNMP_COMMUNITY = pp.Keyword("community").suppress()
        SNMP_LOCATION = pp.Keyword("location").suppress()
        SNMP_CONTACT = pp.Keyword("contact").suppress()
        SNMP_STRING = pp.Word(pp.alphanums, asKeyword=True)

        snmp_ro = (
            SNMP_START_MARKER
            + SNMP_COMMUNITY
            + SNMP_STRING("Read")
            + pp.Keyword("RO").suppress()
        )
        snmp_rw = (
            SNMP_START_MARKER
            + SNMP_COMMUNITY
            + SNMP_STRING("Write")
            + pp.Keyword("RW").suppress()
        )
        snmp_location = SNMP_START_MARKER + SNMP_LOCATION + REMAINDER("Location")
        snmp_contact = SNMP_START_MARKER + SNMP_CONTACT + REMAINDER("Contact")

        command_def = snmp_ro ^ snmp_rw ^ snmp_location ^ snmp_contact
        return command_def.searchString(text)


def test_snmp_properties(cfg_files):
    """
    Testing correct snmp configuration

    Test fails if snmp configuration is missing or incomplete
    """

    # Ask SNMP questions
    console.rule("[bold yellow]Checking SNMP configuration")
    snmp_parameters = SNMPValues(cfg_files).answer().frame()

    # check if all nodes are present
    assert (
        len(snmp_parameters.index) == NUM
    ), f"Expecting {NUM} lines, \
           found {len(snmp_parameters.index)}:\n{snmp_parameters}"

    # Find nodes that have no SNMP servers configured
    snmp_violators = snmp_parameters[
        snmp_parameters[READ_COL].apply(lambda x: len(x) == 0)
    ]
    assert (
        snmp_violators.empty
    ), f"Missing SNMP configuration:\
        \n{snmp_violators}"

    # Find nodes with misconfigured read community string
    community_violators = snmp_parameters[
        snmp_parameters[READ_COL].apply(
            lambda x: len(ref_string.intersection(set(x))) == 0
        )
    ]
    assert (
        community_violators.empty
    ), f"Missing or incorrect community string:\
        \n{community_violators}"


def test_logger_properties(cfg_files):
    """
    Testing correct SysLog configuration

    Test fails if SysLog configuration is missing or incomplete
    """

    log_parameters = LoggerValues(cfg_files).answer().frame()

    # check Syslog configuration
    console.rule("[bold yellow]Checking Syslog configuration")
    assert (
        len(log_parameters.index) == NUM
    ), f"Expecting {NUM} lines, \
           found {len(log_parameters.index)}:\n{log_parameters}"

    # Find nodes that have no SysLog servers configured
    log_violators = log_parameters[
        log_parameters[SERVER_COL].apply(lambda x: len(x) == 0)
    ]
    assert (
        log_violators.empty
    ), f"Missing SysLog configuration:\
        \n{log_violators}"

    # Find nodes with misconfigured server address
    server_violators = log_parameters[
        log_parameters[SERVER_COL].apply(
            lambda x: len(ref_log_server.intersection(set(x))) == 0
        )
    ]
    assert (
        server_violators.empty
    ), f"Missing or incorrect server address:\
        \n{server_violators}"


def test_clock_properties(cfg_files):
    """
    Testing correct SysLog configuration

    Test fails if Clock configuration is missing or incomplete
    """

    clk_parameters = ClockValues(cfg_files).answer().frame()

    # check NTP configuration
    console.rule("[bold yellow]Checking NTP configuration")
    assert (
        len(clk_parameters.index) == NUM
    ), f"Expecting {NUM} lines, \
           found {len(clk_parameters.index)}:\n{clk_parameters}"

    # Find nodes with misconfiguration
    clk_violators = clk_parameters.loc[clk_parameters[HRS_COL] != TIME_SHIFT]
    assert clk_violators.empty, f"Missing or incorrect time zone:\n{clk_violators}"

    # Find nodes with misconfiguration
    clk_violators = clk_parameters.loc[clk_parameters[SUMR_COL] != ADT]
    assert clk_violators.empty, f"Missing or incorrect Summer time:\n{clk_violators}"


if __name__ == "__main__":

    # Get all files in the given path
    files_list = [
        os.path.join(PATH, path)
        for path in os.listdir(PATH)
        if os.path.isfile(os.path.join(PATH, path))
    ]

    console.rule("[bold yellow]Checking presence of configuration files")
    assert files_list, "No configuration files"

    test_snmp_properties(files_list)
    test_logger_properties(files_list)
    test_clock_properties(files_list)
    
    console.rule("[bold green]:heavy_check_mark: All checks passed :heavy_check_mark:")


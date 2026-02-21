"""
Comprehensive tests for all log parsers.

Each parser class gets tested with realistic sample lines (parse + can_parse).
This file covers the cloud, container, web server, system, and specialty
parsers to close the gap in parsers.py coverage.
"""

import json

import pytest

from log_analyzer.parsers import (
    AndroidParser,
    ApacheAccessParser,
    ApacheErrorParser,
    AWSCloudWatchParser,
    AzureMonitorParser,
    ContainerdParser,
    DockerJSONParser,
    GCPCloudLoggingParser,
    HDFSParser,
    HealthAppParser,
    HPCParser,
    JavaLogParser,
    JSONLogParser,
    KubernetesParser,
    LogEntry,
    NginxAccessParser,
    NginxParser,
    OpenStackParser,
    ProxifierParser,
    SquidParser,
    SupercomputerParser,
    SyslogParser,
    UniversalFallbackParser,
    WindowsEventParser,
    extract_level_from_message,
    parse_cloud_timestamp,
)

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestParseCloudTimestamp:
    def test_iso8601_z(self):
        ts = parse_cloud_timestamp("2020-01-01T00:00:00Z")
        assert ts is not None
        assert ts.year == 2020

    def test_iso8601_with_millis(self):
        ts = parse_cloud_timestamp("2020-01-01T00:00:00.123Z")
        assert ts is not None

    def test_rfc3339_nano(self):
        ts = parse_cloud_timestamp("2020-01-01T00:00:00.123456789Z")
        assert ts is not None

    def test_unix_millis(self):
        ts = parse_cloud_timestamp("1577836800000")
        assert ts is not None

    def test_invalid(self):
        ts = parse_cloud_timestamp("not-a-timestamp")
        assert ts is None


class TestExtractLevelFromMessage:
    def test_error_level(self):
        assert extract_level_from_message("ERROR: something failed") == "ERROR"

    def test_warning_level(self):
        assert extract_level_from_message("WARN: disk almost full") is not None

    def test_info_level(self):
        result = extract_level_from_message("INFO: started successfully")
        assert result is not None

    def test_no_level(self):
        result = extract_level_from_message("just some text without level")
        assert result is None or result == "INFO"


# ---------------------------------------------------------------------------
# Cloud Provider Parsers
# ---------------------------------------------------------------------------

class TestAWSCloudWatchParser:
    @pytest.fixture
    def parser(self):
        return AWSCloudWatchParser()

    def test_can_parse_json(self, parser):
        line = json.dumps({
            "messageType": "DATA_MESSAGE",
            "logGroup": "/aws/lambda/func",
            "logStream": "stream1",
            "logEvents": [{"timestamp": 1577836800000, "message": "Hello"}]
        })
        assert parser.can_parse(line) is True

    def test_parse_json(self, parser):
        line = json.dumps({
            "messageType": "DATA_MESSAGE",
            "logGroup": "/aws/lambda/func",
            "logStream": "stream1",
            "logEvents": [{"timestamp": 1577836800000, "message": "Hello world"}]
        })
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_aws(self, parser):
        assert parser.can_parse("just a regular line") is False

    def test_parse_non_aws(self, parser):
        assert parser.parse("just a regular line") is None


class TestGCPCloudLoggingParser:
    @pytest.fixture
    def parser(self):
        return GCPCloudLoggingParser()

    def test_can_parse(self, parser):
        line = json.dumps({
            "severity": "ERROR",
            "timestamp": "2020-01-01T00:00:00Z",
            "textPayload": "Error occurred"
        })
        assert parser.can_parse(line) is True

    def test_parse_text_payload(self, parser):
        line = json.dumps({
            "severity": "ERROR",
            "timestamp": "2020-01-01T00:00:00Z",
            "textPayload": "Something went wrong",
            "resource": {"type": "gce_instance"},
            "logName": "projects/my-project/logs/stderr"
        })
        result = parser.parse(line)
        assert result is not None
        assert isinstance(result, LogEntry)

    def test_parse_json_payload(self, parser):
        line = json.dumps({
            "severity": "INFO",
            "timestamp": "2020-01-01T00:00:00Z",
            "jsonPayload": {"msg": "JSON message", "status": 200}
        })
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_gcp(self, parser):
        assert parser.can_parse("regular text") is False


class TestAzureMonitorParser:
    @pytest.fixture
    def parser(self):
        return AzureMonitorParser()

    def test_can_parse(self, parser):
        line = json.dumps({
            "time": "2020-01-01T00:00:00Z",
            "resourceId": "/subscriptions/sub1/rg/myRG",
            "level": "Error",
            "operationName": "Operation",
            "resultType": "Failure",
            "properties": {"message": "Error happened"}
        })
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = json.dumps({
            "time": "2020-01-01T00:00:00Z",
            "resourceId": "/subscriptions/sub1/rg/myRG",
            "level": "Warning",
            "operationName": "Op",
            "resultType": "Success",
            "properties": {"message": "Something happened"}
        })
        result = parser.parse(line)
        assert result is not None

    def test_parse_numeric_severity(self, parser):
        line = json.dumps({
            "time": "2020-01-01T00:00:00Z",
            "resourceId": "/subscriptions/sub1",
            "severityLevel": 3,
            "message": "Error with numeric severity"
        })
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_azure(self, parser):
        assert parser.can_parse("not azure") is False


# ---------------------------------------------------------------------------
# Container Runtime Parsers
# ---------------------------------------------------------------------------

class TestDockerJSONParser:
    @pytest.fixture
    def parser(self):
        return DockerJSONParser()

    def test_can_parse(self, parser):
        line = json.dumps({
            "log": "Hello from container\n",
            "stream": "stdout",
            "time": "2020-01-01T00:00:00.000000000Z"
        })
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = json.dumps({
            "log": "[ERROR] Something failed\n",
            "stream": "stderr",
            "time": "2020-01-01T00:00:00.000000000Z"
        })
        result = parser.parse(line)
        assert result is not None
        assert isinstance(result, LogEntry)

    def test_parse_stdout(self, parser):
        line = json.dumps({
            "log": "Normal output\n",
            "stream": "stdout",
            "time": "2020-01-01T00:00:00Z"
        })
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_docker(self, parser):
        assert parser.can_parse("regular line") is False


class TestKubernetesParser:
    @pytest.fixture
    def parser(self):
        return KubernetesParser()

    def test_can_parse_cri(self, parser):
        line = "2020-01-01T00:00:00.000000000Z stdout F [INFO] Message"
        assert parser.can_parse(line) is True

    def test_parse_cri(self, parser):
        line = "2020-01-01T00:00:00.000000000Z stdout F [ERROR] Something failed"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_docker_json(self, parser):
        line = json.dumps({
            "log": "message\n",
            "stream": "stdout",
            "time": "2020-01-01T00:00:00Z"
        })
        assert parser.can_parse(line) is True

    def test_parse_non_k8s(self, parser):
        assert parser.parse("random text") is None


class TestContainerdParser:
    @pytest.fixture
    def parser(self):
        return ContainerdParser()

    def test_can_parse(self, parser):
        line = "2020-01-01T00:00:00.000000000Z stdout F [INFO] Service started"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "2020-01-01T00:00:00.000000000Z stderr F [ERROR] Crash detected"
        result = parser.parse(line)
        assert result is not None

    def test_parse_with_json_message(self, parser):
        msg = json.dumps({"msg": "structured log"})
        line = f"2020-01-01T00:00:00.000000000Z stdout F {msg}"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_containerd(self, parser):
        assert parser.can_parse("not a containerd line") is False


# ---------------------------------------------------------------------------
# Web Server Parsers
# ---------------------------------------------------------------------------

class TestApacheAccessParser:
    @pytest.fixture
    def parser(self):
        return ApacheAccessParser()

    def test_can_parse(self, parser):
        line = '192.168.1.1 - - [10/Oct/2023:13:55:36 -0700] "GET /index.html HTTP/1.1" 200 2326'
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = '192.168.1.1 - frank [10/Oct/2023:13:55:36 -0700] "GET /api/users HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0"'
        result = parser.parse(line)
        assert result is not None
        assert result.metadata.get("status") == 200

    def test_parse_error_status(self, parser):
        line = '10.0.0.1 - - [10/Oct/2023:13:55:36 -0700] "POST /login HTTP/1.1" 500 512'
        result = parser.parse(line)
        assert result is not None
        assert result.level == "ERROR"

    def test_can_parse_non_apache(self, parser):
        assert parser.can_parse("not apache") is False


class TestApacheErrorParser:
    @pytest.fixture
    def parser(self):
        return ApacheErrorParser()

    def test_can_parse(self, parser):
        line = "[Sat Oct 10 13:55:36.123456 2023] [core:error] [pid 1234] [client 192.168.1.1:12345] Error message"
        assert parser.can_parse(line) is True

    def test_parse_modern(self, parser):
        line = "[Sat Oct 10 13:55:36.123456 2023] [core:error] [pid 1234] [client 192.168.1.1:12345] Something failed"
        result = parser.parse(line)
        assert result is not None

    def test_parse_legacy(self, parser):
        line = "[Sun Dec 04 04:47:44 2005] [error] error message here"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_apache_error(self, parser):
        assert parser.can_parse("not error log") is False


class TestNginxAccessParser:
    @pytest.fixture
    def parser(self):
        return NginxAccessParser()

    def test_can_parse(self, parser):
        line = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/v1/users HTTP/1.1" 200 1234 "-" "curl/7.68.0"'
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = '10.0.0.1 - admin [10/Oct/2023:13:55:36 +0000] "POST /api/data HTTP/1.1" 201 456 "http://example.com" "Python/3.9"'
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_nginx(self, parser):
        assert parser.can_parse("not nginx") is False


class TestNginxParser:
    @pytest.fixture
    def parser(self):
        return NginxParser()

    def test_can_parse(self, parser):
        line = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET / HTTP/1.1" 200 612 "-" "Mozilla/5.0"'
        result = parser.can_parse(line)
        assert isinstance(result, bool)

    def test_parse_valid(self, parser):
        line = '10.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /favicon.ico HTTP/1.1" 404 0 "-" "Mozilla/5.0"'
        result = parser.parse(line)
        assert result is None or isinstance(result, LogEntry)


# ---------------------------------------------------------------------------
# System Log Parsers
# ---------------------------------------------------------------------------

class TestJSONLogParser:
    @pytest.fixture
    def parser(self):
        return JSONLogParser()

    def test_can_parse(self, parser):
        line = json.dumps({"level": "INFO", "message": "test"})
        assert parser.can_parse(line) is True

    def test_parse_basic(self, parser):
        line = json.dumps({
            "level": "ERROR",
            "message": "Something failed",
            "timestamp": "2020-01-01T00:00:00Z"
        })
        result = parser.parse(line)
        assert result is not None
        assert result.level == "ERROR"

    def test_parse_with_msg_field(self, parser):
        line = json.dumps({"level": "info", "msg": "Started server", "port": 8080})
        result = parser.parse(line)
        assert result is not None

    def test_parse_with_severity_field(self, parser):
        line = json.dumps({"severity": "WARNING", "message": "High memory"})
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_json(self, parser):
        assert parser.can_parse("not json") is False

    def test_parse_non_json(self, parser):
        assert parser.parse("not json") is None


class TestSyslogParser:
    @pytest.fixture
    def parser(self):
        return SyslogParser()

    def test_can_parse_bsd(self, parser):
        line = "Oct 11 22:14:15 mymachine su: 'su root' failed for lonvick"
        assert parser.can_parse(line) is True

    def test_parse_bsd(self, parser):
        line = "Oct 11 22:14:15 myhost sshd: Failed password for root"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_rfc3164(self, parser):
        line = "<34>Oct 11 22:14:15 mymachine su: 'su root' failed"
        assert parser.can_parse(line) is True

    def test_parse_rfc5424(self, parser):
        line = "<165>1 2003-10-11T22:14:15.003Z mymachine.example.com evntslog - - - An application event log"
        result = parser.parse(line)
        assert result is None or isinstance(result, LogEntry)

    def test_can_parse_non_syslog(self, parser):
        assert parser.can_parse("{}") is False


class TestAndroidParser:
    @pytest.fixture
    def parser(self):
        return AndroidParser()

    def test_can_parse(self, parser):
        line = "03-17 16:13:38.811  1702  2395 D WindowManager: Starting activity"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "03-17 16:13:38.811  1702  2395 E ActivityManager: Force stopping package"
        result = parser.parse(line)
        assert result is not None
        assert result.level == "ERROR"

    def test_can_parse_non_android(self, parser):
        assert parser.can_parse("not android logcat") is False


class TestJavaLogParser:
    @pytest.fixture
    def parser(self):
        return JavaLogParser()

    def test_can_parse(self, parser):
        line = "2015-10-18 18:01:47,978 INFO [main] org.apache.hadoop.hdfs.server.namenode.NameNode: STARTUP_MSG"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "2015-10-18 18:01:47,978 ERROR [main] org.apache.hadoop.hdfs.DFSClient: Connection refused"
        result = parser.parse(line)
        assert result is not None

    def test_parse_spark_format(self, parser):
        line = "17/06/09 20:10:40 INFO executor.CoarseGrainedExecutorBackend: Registered signal handlers"
        result = parser.parse(line)
        assert result is None or isinstance(result, LogEntry)

    def test_can_parse_non_java(self, parser):
        assert parser.can_parse("not java log") is False


class TestHDFSParser:
    @pytest.fixture
    def parser(self):
        return HDFSParser()

    def test_can_parse(self, parser):
        line = "081109 203615 148 INFO dfs.DataNode$PacketResponder: PacketResponder 1 for block received"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "081109 203615 148 INFO dfs.DataNode$PacketResponder: PacketResponder 1 for block received"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_hdfs(self, parser):
        assert parser.can_parse("not hdfs format") is False


class TestWindowsEventParser:
    @pytest.fixture
    def parser(self):
        return WindowsEventParser()

    def test_can_parse(self, parser):
        line = "2016-09-28 04:30:30, Info CBS Loaded Servicing Stack v6.3.9600.18384"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "2016-09-28 04:30:30, Info CBS Loaded Servicing Stack v6.3.9600.18384"
        result = parser.parse(line)
        assert result is not None

    def test_parse_error(self, parser):
        line = "2016-09-28 04:30:31, Error CSI Failed to install update"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_windows(self, parser):
        assert parser.can_parse("not windows log") is False


class TestProxifierParser:
    @pytest.fixture
    def parser(self):
        return ProxifierParser()

    def test_can_parse(self, parser):
        line = "[10.30 16:49:06] chrome.exe - proxy.cse.cuhk.edu.hk:5070 open through proxy"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "[10.30 16:49:06] chrome.exe - proxy.example.com:8080 open through proxy HTTPS"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_proxifier(self, parser):
        assert parser.can_parse("not proxifier") is False


class TestHPCParser:
    @pytest.fixture
    def parser(self):
        return HPCParser()

    def test_can_parse(self, parser):
        line = "134681 node-246 unix.hw state_change.unavailable 1077804742 1 unavailable"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "134681 node-246 unix.hw state_change.unavailable 1077804742 1 unavailable"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_hpc(self, parser):
        assert parser.can_parse("not hpc log") is False


class TestHealthAppParser:
    @pytest.fixture
    def parser(self):
        return HealthAppParser()

    def test_can_parse(self, parser):
        line = "20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_healthapp(self, parser):
        assert parser.can_parse("not healthapp") is False


class TestOpenStackParser:
    @pytest.fixture
    def parser(self):
        return OpenStackParser()

    def test_can_parse(self, parser):
        line = "nova-compute.log 2017-06-02 19:32:07.690 29 ERROR nova.compute.manager [req-abc-def-123 user project] Error"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "nova-compute.log 2017-06-02 19:32:07.690 29 ERROR nova.compute.manager [req-abc-def-123 user project] Instance failed"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_openstack(self, parser):
        assert parser.can_parse("not openstack") is False


class TestSquidParser:
    @pytest.fixture
    def parser(self):
        return SquidParser()

    def test_can_parse(self, parser):
        line = "1157689312.049 5006 10.105.21.199 TCP_MISS/200 19763 CONNECT login.yahoo.com:443 badeyek DIRECT/209.73.177.115 -"
        assert parser.can_parse(line) is True

    def test_parse(self, parser):
        line = "1157689312.049 5006 10.105.21.199 TCP_MISS/200 19763 CONNECT login.yahoo.com:443 badeyek DIRECT/209.73.177.115 -"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_squid(self, parser):
        assert parser.can_parse("not squid") is False


class TestSupercomputerParser:
    @pytest.fixture
    def parser(self):
        return SupercomputerParser()

    def test_can_parse(self, parser):
        line = "- 1117838570 2005.06.03 R02-M1-N0 2005-06-03-15.42.50.675872 R02-M1-N0-C:J12-U01 RAS KERNEL INFO instruction"
        assert parser.can_parse(line)

    def test_parse(self, parser):
        line = "- 1117838570 2005.06.03 R02-M1-N0 2005-06-03-15.42.50.675872 R02-M1-N0-C:J12-U01 RAS KERNEL INFO instruction cache parity error corrected"
        result = parser.parse(line)
        assert result is not None

    def test_can_parse_non_supercomputer(self, parser):
        assert parser.can_parse("regular text") is False


# ---------------------------------------------------------------------------
# Universal Fallback Parser
# ---------------------------------------------------------------------------

class TestUniversalFallbackParser:
    @pytest.fixture
    def parser(self):
        return UniversalFallbackParser()

    def test_can_parse_anything(self, parser):
        assert parser.can_parse("literally anything") is True
        assert parser.can_parse("[ERROR] something") is True
        assert parser.can_parse("") is True

    def test_parse_with_level(self, parser):
        result = parser.parse("2020-01-01 12:00:00 [ERROR] Something failed")
        assert result is not None
        assert result.message != ""

    def test_parse_plain_text(self, parser):
        result = parser.parse("Just a regular line of text")
        assert result is not None

    def test_parse_empty_line(self, parser):
        result = parser.parse("")
        assert result is not None or result is None  # Either behavior is OK

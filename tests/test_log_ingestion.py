import os
import sys
import unittest
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from log_parser import (
    parse_log_line,
    detect_log_source_format,
    normalize_log_level,
    parse_hdfs_timestamp,
    parse_openstack_timestamp,
    parse_bgl_timestamp,
    parse_apache_timestamp
)
from ingest_logs import ingest_log_file

class TestLogIngestionPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_log_level_normalization(self):
        self.assertEqual(normalize_log_level("FATAL"), "CRITICAL")
        self.assertEqual(normalize_log_level("emerg"), "CRITICAL")
        self.assertEqual(normalize_log_level("ERROR"), "ERROR")
        self.assertEqual(normalize_log_level("SEVERE"), "ERROR")
        self.assertEqual(normalize_log_level("WARN"), "WARNING")
        self.assertEqual(normalize_log_level("NOTICE"), "INFO")
        self.assertEqual(normalize_log_level("DEBUG"), "DEBUG")
        self.assertEqual(normalize_log_level(None), "INFO")

    def test_hdfs_log_parsing(self):
        line = "081109 203522 147 ERROR dfs.DataNode$DataXceiver: Connection to 10.250.19.102:50010 closed by client with exception: java.io.IOException"
        event = parse_log_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["source_format"], "HDFS")
        self.assertEqual(event["level"], "ERROR")
        self.assertEqual(event["component"], "dfs.DataNode$DataXceiver")
        self.assertEqual(event["timestamp"], "2008-11-09T20:35:22Z")
        self.assertTrue(event["is_anomaly"])

    def test_openstack_log_parsing(self):
        line = '2026-03-24 10:14:10.890 1030 ERROR nova.compute.claims [req-89e0b12a-81be-4d1d-91b7-b8eb20786cf7] [instance: c03c0c1b-252a-43cf-bf29-d5c2be660a1e] Failed to claim resources on host compute-node-08: Insufficient free memory'
        event = parse_log_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["source_format"], "OPENSTACK")
        self.assertEqual(event["level"], "ERROR")
        self.assertEqual(event["component"], "nova.compute.claims")
        self.assertTrue(event["is_anomaly"])
        self.assertIn("Insufficient free memory", event["message"])

    def test_bgl_log_parsing(self):
        line = "- 1117838572 2005.06.03 R02-M1-N0-C:J12-U11 2005-06-03-15.42.52.456123 R02-M1-N0-C:J12-U11 RAS KERNEL FATAL data TLB error interrupt: unrecoverable hardware fault"
        event = parse_log_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["source_format"], "BGL")
        self.assertEqual(event["level"], "CRITICAL")
        self.assertEqual(event["timestamp"], "2005-06-03T15:42:52Z")
        self.assertTrue(event["is_anomaly"])

    def test_apache_log_parsing(self):
        line = "[Sun Mar 22 06:28:45 2026] [error] [client 192.168.1.108:54322] Script timed out before returning headers: process_payment.cgi"
        event = parse_log_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["source_format"], "APACHE")
        self.assertEqual(event["level"], "ERROR")
        self.assertEqual(event["component"], "apache-httpd")
        self.assertTrue(event["is_anomaly"])

    def test_generic_fallback_log_parsing(self):
        line = "2026-03-24T12:00:00Z [WARN] cache-cluster: memory eviction limit warning"
        event = parse_log_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["level"], "WARNING")
        self.assertEqual(event["component"], "cache-cluster")
        self.assertEqual(event["timestamp"], "2026-03-24T12:00:00Z")

    def test_log_source_format_detection(self):
        hdfs_lines = [
            "081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_-16089",
            "081109 203520 145 INFO dfs.DataNode$DataXceiver: Receiving block blk_-16089"
        ]
        self.assertEqual(detect_log_source_format(hdfs_lines), "HDFS")

        openstack_lines = [
            '2026-03-24 10:14:02.124 1024 INFO nova.osapi_compute [req-123] GET /v2.1'
        ]
        self.assertEqual(detect_log_source_format(openstack_lines), "OPENSTACK")

    def test_ingest_log_file_end_to_end(self):
        sample_log = os.path.join(self.temp_dir.name, "app.log")
        with open(sample_log, "w", encoding="utf-8") as f:
            f.write("2026-03-24 10:14:02.124 1024 INFO nova.osapi_compute [req-1] Server started\n")
            f.write("2026-03-24 10:14:05.340 1024 WARNING nova.compute [req-1] High load\n")
            f.write("2026-03-24 10:14:10.890 1030 ERROR nova.compute [req-2] Out of memory crash\n")

        output_json = os.path.join(self.temp_dir.name, "app_events.json")
        result = ingest_log_file(sample_log, output_path=output_json)

        self.assertEqual(result["summary"]["total_lines"], 3)
        self.assertEqual(result["summary"]["parsed_events_count"], 3)
        self.assertEqual(result["summary"]["anomalies_detected"], 1)
        self.assertEqual(result["summary"]["level_breakdown"]["INFO"], 1)
        self.assertEqual(result["summary"]["level_breakdown"]["WARNING"], 1)
        self.assertEqual(result["summary"]["level_breakdown"]["ERROR"], 1)
        self.assertTrue(os.path.exists(output_json))

if __name__ == "__main__":
    unittest.main()

"""API boundary: validation, process isolation, real model output. Needs requirements-dev.txt.

Drafted with AI assistance (Claude, Anthropic); reviewed by Team AniNow.
"""
import json
import subprocess
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from threading import Event
from unittest.mock import patch

from fastapi.testclient import TestClient

import api


PAYLOAD = dict(place="Science City of Muñoz, Nueva Ecija", harvest="2026-11-15",
               next_planting="2027-05-31", drainage="well_drained")
FAKE_RESULTS = {"fields": {"rain": {"rankings": {"balanced": ["rice"]}}}}


class HttpBoundary(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.create_app(["https://frontend.example"]))
        self.addCleanup(self.client.close)

    def test_health_and_catalog_do_not_run_the_model(self):
        with patch.object(api, "run_comparison") as calculate:
            response = self.client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")
            catalog = self.client.get("/api/v1/catalog").json()
            self.assertEqual(len(catalog["places"]), 22)
            self.assertEqual(len(catalog["crops"]), 29)
            self.assertEqual(catalog["capabilities"], ["fallow", "whole_schedule"])
            self.assertIn(PAYLOAD["place"], [p["id"] for p in catalog["places"]])
            self.assertIn("da_guide_range", [c["limits_basis"] for c in catalog["crops"]])
            self.assertEqual(catalog["model_version"], response.json()["model_version"])
            calculate.assert_not_called()

    def test_invalid_inputs_never_reach_the_model(self):
        cases = [
            {"place": "Unknown town"}, {"main_crop": "durian"},
            {"harvest": "not-a-date"}, {"harvest": "2026-02-30"},
            {"harvest": "2028-02-29", "next_planting": "2028-06-01"},
            {"next_planting": "2026-11-14"}, {"next_planting": "2028-05-31"},
            {"next_planting": "2026-11-15"}, {"harvest": 1794700800},
            {"soil_ph": 14}, {"soil_ph": "NaN"}, {"soil_ph": "Infinity"},
            {"soil_texture": "clayloam"}, {"water": "irrig"},
            {"drainage": "maybe"}, {"priority": "invented"},
            {"prep_days": -1}, {"prep_days": 181}, {"prep_days": 0.5}, {"prep_days": True},
            {"picking_days": -1}, {"picking_days": 181}, {"picking_days": 0.5}, {"picking_days": True},
            {"turnaround_days": -1}, {"turnaround_days": 91},
            {"turnaround_days": 2.5}, {"turnaround_days": True},
            {"pass_mark": 1.1}, {"pass_mark": "NaN"}, {"pass_mark": True},
            {"out": "another-file.json"}, {"model_version": "client-selected"},
        ]
        with patch.object(api, "run_comparison") as calculate:
            for change in cases:
                with self.subTest(change=change):
                    response = self.client.post("/api/v1/compare", json=PAYLOAD | change)
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertEqual(response.json()["error"]["code"], "invalid_inputs")
                    self.assertTrue(response.json()["error"]["field_errors"])
            calculate.assert_not_called()

    def test_schedule_and_fallow_are_validated_and_forwarded(self):
        with patch.object(api, "run_comparison", return_value=FAKE_RESULTS) as calculate:
            response = self.client.post("/api/v1/compare", json=PAYLOAD | dict(
                main_crop="fallow", prep_days=14, picking_days=21, turnaround_days=7))
        self.assertEqual(response.status_code, 200, response.text)
        payload = calculate.call_args.args[0]
        args = payload.cli_args()
        for flag, expected in (("--main-crop", "fallow"), ("--prep-days", "14"),
                               ("--picking-days", "21"), ("--turnaround-days", "7")):
            self.assertEqual(args[args.index(flag) + 1], expected)
        defaults = api.ComparisonRequest.model_validate(PAYLOAD)
        self.assertEqual((defaults.prep_days, defaults.picking_days, defaults.turnaround_days), (0, 0, 0))

    def test_required_field_and_malformed_json_errors_have_request_ids(self):
        for options in ({"json": {}}, {"content": "{", "headers": {"Content-Type": "application/json"}}):
            response = self.client.post("/api/v1/compare", **options)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["request_id"], response.headers["x-request-id"])
            self.assertEqual(response.headers["cache-control"], "no-store")

    def test_browser_access_requires_an_allowed_origin(self):
        headers = {"Origin": "https://frontend.example", "Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Headers": "content-type"}
        allowed = self.client.options("/api/v1/compare", headers=headers)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.headers["access-control-allow-origin"], headers["Origin"])
        denied = self.client.options("/api/v1/compare", headers=headers | {"Origin": "https://other.example"})
        self.assertEqual(denied.status_code, 400)
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_deployed_frontend_is_allowed_by_default(self):
        with patch.dict(api.os.environ, {}, clear=True):
            with TestClient(api.create_app()) as client:
                response = client.options("/api/v1/compare", headers={
                    "Origin": "https://aninow-klima.vercel.app", "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "https://aninow-klima.vercel.app")

    def test_concurrent_request_is_refused_but_health_remains_available(self):
        entered, release = Event(), Event()

        def slow_model(_payload):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("Test did not release model.")
            return FAKE_RESULTS

        with patch.object(api, "run_comparison", side_effect=slow_model):
            with ThreadPoolExecutor(max_workers=1) as executor:
                first = executor.submit(self.client.post, "/api/v1/compare", json=PAYLOAD)
                try:
                    self.assertTrue(entered.wait(5))
                    second = self.client.post("/api/v1/compare", json=PAYLOAD)
                    self.assertEqual(second.status_code, 503)
                    self.assertEqual(second.headers["retry-after"], "5")
                    self.assertEqual(self.client.get("/health").status_code, 200)
                finally:
                    release.set()
                self.assertEqual(first.result(timeout=5).status_code, 200)

    def test_failure_and_timeout_do_not_leak_details_or_keep_the_slot(self):
        for failure, status, code in (
            (RuntimeError("private filesystem path"), 503, "model_unavailable"),
            (subprocess.TimeoutExpired("model", 120), 504, "model_timeout"),
        ):
            with self.subTest(status=status):
                with patch.object(api, "run_comparison", side_effect=failure):
                    logs = self.assertLogs(api.LOGGER, level="ERROR") if status == 503 else nullcontext()
                    with logs:
                        response = self.client.post("/api/v1/compare", json=PAYLOAD)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["error"]["code"], code)
                self.assertNotIn("private filesystem", response.text)
                with patch.object(api, "run_comparison", return_value=FAKE_RESULTS):
                    self.assertEqual(self.client.post("/api/v1/compare", json=PAYLOAD).status_code, 200)

    def test_unknown_routes_use_the_error_envelope(self):
        response = self.client.get("/missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_openapi_documents_the_actual_error_shape(self):
        schema = self.client.get("/openapi.json").json()
        responses = schema["paths"]["/api/v1/compare"]["post"]["responses"]
        for status in ("422", "503", "504"):
            self.assertEqual(responses[status]["content"]["application/json"]["schema"]["$ref"],
                             "#/components/schemas/ErrorResponse")


class ProcessIsolation(unittest.TestCase):
    def test_temporary_result_is_removed_after_process_timeout(self):
        output_files = []

        def timeout(args, **_kwargs):
            output = Path(args[args.index("--out") + 1])
            output_files.append(output)
            output.write_text("partial output", encoding="utf-8")
            raise subprocess.TimeoutExpired(args, 120)

        payload = api.ComparisonRequest.model_validate(PAYLOAD)
        with patch.object(api.subprocess, "run", side_effect=timeout):
            with self.assertRaises(subprocess.TimeoutExpired):
                api.run_comparison(payload)
        self.assertEqual(len(output_files), 1)
        self.assertFalse(output_files[0].parent.exists())


class RealComparisons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_actual_model_results_not_sample_fixture_counts(self):
        response = self.client.post("/api/v1/compare", json=PAYLOAD)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["mode"], "rules_model")
        self.assertEqual(body["contract_version"], "klima-comparison.v1")
        self.assertEqual(body["request_id"], response.headers["x-request-id"])
        results = body["results"]
        self.assertEqual(results["meta"]["main_crop"], "rice")
        rain = results["fields"]["rain"]
        count = rain["crops"]["mungbean"]["counts"]["balanced"]["all"]["short"]
        self.assertEqual((count["pass"], count["of"]), (22, 41))
        self.assertEqual(body["ranking"], rain["rankings"]["balanced"])
        self.assertIn("cabbage", rain["excluded"])
        self.assertIn("suitability", results["method"])
        self.assertIn("crop_coefficients", results)
        self.assertEqual(len(results["seasons"]), 44)
        # both water scenarios returned
        self.assertIn("irrigation", results["fields"])
        json.dumps(body, allow_nan=False)

    def test_real_fallow_and_whole_schedule(self):
        response = self.client.post("/api/v1/compare", json=PAYLOAD | dict(
            main_crop="fallow", prep_days=14, picking_days=21, turnaround_days=7))
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        meta = body["results"]["meta"]
        self.assertEqual((meta["main_crop"], meta["prep_days"], meta["picking_days"], meta["turnaround_days"]),
                         ("fallow", 14, 21, 7))
        for field in body["results"]["fields"].values():
            self.assertEqual(field["same_family_as_main"], [])
            for plan in field["schedule"].values():
                self.assertEqual(plan["total_days"], 14 + plan["growing_days"] + 21 + 7)
                self.assertEqual(plan["spare_days"], plan["window_days"] - plan["total_days"])
            for crop in field["recommendation"]["suitable"]:
                self.assertFalse(field["crops"][crop]["not_scored"])
                self.assertTrue(field["schedule"][crop]["fits"])
        self.assertEqual(body["results"]["planting_dates"]["mungbean"][0]["offset_days"], 14)

    def test_overrides_another_place_and_then_a_fresh_pilot_request(self):
        custom = PAYLOAD | dict(place="Batac, Ilocos Norte", main_crop="tomato",
                                soil_ph=6.8, soil_texture="light", water="irrigation",
                                priority="finishing_early", drainage="unknown", turnaround_days=12,
                                pass_mark=0.8)
        response = self.client.post("/api/v1/compare", json=custom)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        result = body["results"]
        self.assertEqual(result["meta"]["location_name"], custom["place"])
        self.assertEqual(result["meta"]["main_crop"], "tomato")
        self.assertEqual(result["meta"]["turnaround_days"], 12)
        self.assertEqual(result["soil"]["ph"], 6.8)
        self.assertEqual(result["soil"]["texture"], "light")
        self.assertEqual(result["meta"]["pass_mark"], 0.8)
        self.assertEqual(body["ranking"], result["fields"]["irrigation"]["rankings"]["finishing_early"])
        self.assertTrue(any("assumes sufficient water" in text for text in body["warnings"]))
        self.assertTrue(any("Drainage is unknown" in text for text in body["warnings"]))
        fresh = self.client.post("/api/v1/compare", json=PAYLOAD).json()["results"]
        self.assertEqual(fresh["meta"]["main_crop"], "rice")
        self.assertEqual(fresh["meta"]["location_name"], PAYLOAD["place"])
        self.assertEqual(fresh["meta"]["turnaround_days"], 0)
        self.assertEqual(fresh["meta"]["pass_mark"], 0.6)
        self.assertEqual(fresh["soil"]["ph"], 6.3)
        self.assertEqual(fresh["soil"]["texture"], "medium")


if __name__ == "__main__":
    unittest.main()

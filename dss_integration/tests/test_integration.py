"""
dss_integration/tests/test_integration.py
Web Step 1 — DSS Engine Integration Layer 통합 테스트

Run: python -B -m unittest dss_integration.tests.test_integration -v
"""
from __future__ import annotations
import sys, os, math, unittest

# Path setup
_HERE    = os.path.dirname(os.path.abspath(__file__))
_INTEG   = os.path.dirname(_HERE)
_OUTPUTS = os.path.dirname(_INTEG)
for p in [_OUTPUTS, _INTEG]:
    if p not in sys.path:
        sys.path.insert(0, p)

from dss_integration.monitor.monitor_models  import EngineStatus, EngineMonitorResult, DSSMonitorResult
from dss_integration.monitor.engine_monitor  import EngineMonitor
from dss_integration.data.base_loader        import RawMarketData, AbstractDataLoader
from dss_integration.data.synthetic_loader   import SyntheticDataLoader
from dss_integration.core.dss_result         import DSSResult
from dss_integration.core.json_serializer    import JSONSerializer
from dss_integration.core.dss_pipeline       import DSSPipeline
from dss_integration.config.settings         import SECTOR_TICKERS, ENGINE_ORDER


# ═══════════════════════════════════════════════════════════════════════════
# 1. EngineMonitor Tests (14 tests)
# ═══════════════════════════════════════════════════════════════════════════
class TestEngineMonitor(unittest.TestCase):

    def _monitor(self):
        return EngineMonitor(run_id="test")

    def test_successful_track(self):
        m = self._monitor()
        with m.track("Test Engine"):
            x = 1 + 1
        self.assertEqual(len(m.results), 1)
        self.assertEqual(m.results[0].status, EngineStatus.SUCCESS)

    def test_failed_track(self):
        m = self._monitor()
        with self.assertRaises(ValueError):
            with m.track("Fail Engine"):
                raise ValueError("test error")
        self.assertEqual(m.results[0].status, EngineStatus.FAILED)

    def test_failed_track_records_error_message(self):
        m = self._monitor()
        try:
            with m.track("Fail Engine"):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        self.assertIn("boom", m.results[0].error_message)

    def test_elapsed_ms_positive(self):
        m = self._monitor()
        with m.track("Timed Engine"):
            import time; time.sleep(0.01)
        self.assertGreater(m.results[0].elapsed_ms, 0.0)

    def test_elapsed_sec_property(self):
        m = self._monitor()
        with m.track("Sec Engine"):
            pass
        r = m.results[0]
        self.assertAlmostEqual(r.elapsed_sec, r.elapsed_ms / 1000, places=3)

    def test_multiple_engines(self):
        m = self._monitor()
        for name in ["A", "B", "C"]:
            with m.track(name):
                pass
        self.assertEqual(len(m.results), 3)

    def test_skip(self):
        m = self._monitor()
        m.skip("Skipped Engine", "no data")
        self.assertEqual(m.results[0].status, EngineStatus.SKIPPED)

    def test_to_result_all_success(self):
        m = self._monitor()
        with m.track("E1"): pass
        with m.track("E2"): pass
        r = m.to_result()
        self.assertIsInstance(r, DSSMonitorResult)
        self.assertTrue(r.all_success)

    def test_to_result_failure_recorded(self):
        m = self._monitor()
        try:
            with m.track("Bad"):
                raise Exception("err")
        except Exception:
            pass
        r = m.to_result()
        self.assertFalse(r.all_success)
        self.assertIn("Bad", r.failed_engines)

    def test_to_result_total_elapsed_positive(self):
        m = self._monitor()
        with m.track("E"): pass
        r = m.to_result()
        self.assertGreater(r.total_elapsed_ms, 0.0)

    def test_engine_monitor_result_to_dict(self):
        r = EngineMonitorResult(
            engine_name="Test", status=EngineStatus.SUCCESS,
            start_time="2026-01-01T00:00:00", end_time="2026-01-01T00:00:01",
            elapsed_ms=1000.0,
        )
        d = r.to_dict()
        self.assertEqual(d["status"], "SUCCESS")
        self.assertEqual(d["elapsed_sec"], 1.0)

    def test_dss_monitor_result_to_dict(self):
        mr = DSSMonitorResult(
            engines=[EngineMonitorResult(
                engine_name="E", status=EngineStatus.SUCCESS,
                start_time="t", end_time="t", elapsed_ms=100.0)],
            total_elapsed_ms=100.0, all_success=True,
        )
        d = mr.to_dict()
        self.assertIn("engines", d)
        self.assertTrue(d["all_success"])

    def test_success_count(self):
        m = self._monitor()
        with m.track("E1"): pass
        try:
            with m.track("E2"): raise Exception()
        except Exception: pass
        r = m.to_result()
        self.assertEqual(r.success_count, 1)
        self.assertEqual(r.failure_count, 1)

    def test_print_report_no_crash(self):
        """print_report() 실행 시 예외가 없어야 한다."""
        import io, contextlib
        m = self._monitor()
        with m.track("Engine A"): pass
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            m.print_report()
        output = buf.getvalue()
        self.assertIn("Engine A", output)
        self.assertIn("Total", output)


# ═══════════════════════════════════════════════════════════════════════════
# 2. SyntheticDataLoader Tests (8 tests)
# ═══════════════════════════════════════════════════════════════════════════
class TestSyntheticDataLoader(unittest.TestCase):

    def setUp(self):
        self.loader = SyntheticDataLoader(seed=42)
        self.data   = self.loader.load()

    def test_returns_raw_market_data(self):
        self.assertIsInstance(self.data, RawMarketData)

    def test_is_available(self):
        self.assertTrue(self.loader.is_available())

    def test_tickers_not_empty(self):
        self.assertTrue(len(self.data.tickers) > 0)

    def test_sector_prices_all_tickers(self):
        for t in self.data.tickers:
            self.assertIn(t, self.data.sector_prices)

    def test_prices_monotone_positive(self):
        for prices in self.data.sector_prices.values():
            self.assertTrue(all(p > 0 for p in prices))

    def test_vix_positive(self):
        self.assertGreater(self.data.vix, 0.0)

    def test_macro_indicators_in_range(self):
        for v in self.data.macro_indicators.values():
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 100.0)

    def test_reproducible_with_same_seed(self):
        l1 = SyntheticDataLoader(seed=99).load()
        l2 = SyntheticDataLoader(seed=99).load()
        self.assertEqual(l1.vix, l2.vix)
        self.assertEqual(l1.tickers, l2.tickers)


# ═══════════════════════════════════════════════════════════════════════════
# 3. JSONSerializer Tests (8 tests)
# ═══════════════════════════════════════════════════════════════════════════
class TestJSONSerializer(unittest.TestCase):

    def setUp(self):
        self.ser = JSONSerializer()

    def test_serialize_simple_dict(self):
        d = {"a": 1, "b": "hello"}
        r = self.ser.serialize(d)
        self.assertEqual(r, d)

    def test_serialize_enum(self):
        r = self.ser.serialize(EngineStatus.SUCCESS)
        self.assertEqual(r, "SUCCESS")

    def test_serialize_none(self):
        self.assertIsNone(self.ser.serialize(None))

    def test_serialize_float_nan(self):
        r = self.ser.serialize(float("nan"))
        self.assertIsNone(r)

    def test_serialize_float_inf(self):
        r = self.ser.serialize(float("inf"))
        self.assertIsNone(r)

    def test_serialize_nested_dict(self):
        from types import SimpleNamespace
        obj = SimpleNamespace(x=1, y=SimpleNamespace(z=2))
        r = self.ser.serialize(obj)
        self.assertEqual(r["x"], 1)
        self.assertEqual(r["y"]["z"], 2)

    def test_to_json_returns_string(self):
        s = self.ser.to_json({"key": "value"})
        self.assertIsInstance(s, str)
        self.assertIn("key", s)

    def test_save_and_load(self):
        import json, tempfile
        data = {"engine": "test", "score": 72.5}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            path = f.name
        self.ser.save(data, path)
        loaded = json.load(open(path))
        self.assertEqual(loaded["score"], 72.5)
        os.unlink(path)


# ═══════════════════════════════════════════════════════════════════════════
# 4. DSSResult Tests (8 tests)
# ═══════════════════════════════════════════════════════════════════════════
class TestDSSResult(unittest.TestCase):

    def _make_result(self, **kwargs) -> DSSResult:
        return DSSResult(**kwargs)

    def test_default_system_health_unknown(self):
        r = self._make_result()
        self.assertEqual(r.system_health, "UNKNOWN")

    def test_healthy_when_all_success(self):
        m = EngineMonitor(run_id="t")
        with m.track("E"): pass
        mr = m.to_result()
        r = self._make_result(monitor_result=mr)
        self.assertEqual(r.system_health, "HEALTHY")

    def test_degraded_when_one_failure(self):
        m = EngineMonitor(run_id="t")
        try:
            with m.track("Fail"): raise Exception()
        except Exception: pass
        mr = m.to_result()
        r = self._make_result(monitor_result=mr)
        self.assertIn(r.system_health, ("DEGRADED", "CRITICAL"))

    def test_overall_confidence_default_zero(self):
        r = self._make_result()
        self.assertEqual(r.overall_confidence, 0.0)

    def test_recommended_action_fallback_wait(self):
        r = self._make_result()
        self.assertEqual(r.recommended_action, "WAIT")

    def test_macro_state_unknown_when_none(self):
        r = self._make_result()
        self.assertEqual(r.macro_state, "Unknown")

    def test_validation_grade_na_when_none(self):
        r = self._make_result()
        self.assertEqual(r.validation_grade, "N/A")

    def test_top_opportunities_empty_by_default(self):
        r = self._make_result()
        self.assertEqual(r.top_opportunities, [])


# ═══════════════════════════════════════════════════════════════════════════
# 5. DSSPipeline Integration Tests (10 tests)
# ═══════════════════════════════════════════════════════════════════════════
class TestDSSPipeline(unittest.TestCase):

    def setUp(self):
        self.raw = SyntheticDataLoader(seed=42).load()
        self.pipeline = DSSPipeline(run_id="unit_test")

    def test_returns_dss_result(self):
        r = self.pipeline.run(self.raw)
        self.assertIsInstance(r, DSSResult)

    def test_macro_result_not_none(self):
        r = self.pipeline.run(self.raw)
        self.assertIsNotNone(r.macro_result)

    def test_breadth_result_not_none(self):
        r = self.pipeline.run(self.raw)
        self.assertIsNotNone(r.breadth_result)

    def test_rs_result_not_none(self):
        r = self.pipeline.run(self.raw)
        self.assertIsNotNone(r.rs_result)

    def test_rotation_result_not_none(self):
        r = self.pipeline.run(self.raw)
        self.assertIsNotNone(r.rotation_result)

    def test_portfolio_decision_not_none(self):
        r = self.pipeline.run(self.raw)
        self.assertIsNotNone(r.portfolio_decision_result)

    def test_portfolio_optimizer_not_none(self):
        r = self.pipeline.run(self.raw)
        self.assertIsNotNone(r.portfolio_optimization_result)

    def test_monitor_result_attached(self):
        r = self.pipeline.run(self.raw)
        self.assertIsNotNone(r.monitor_result)

    def test_monitor_has_engine_records(self):
        r = self.pipeline.run(self.raw)
        self.assertGreater(len(r.monitor_result.engines), 0)

    def test_run_date_set(self):
        r = self.pipeline.run(self.raw)
        self.assertTrue(len(r.run_date) > 0)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Config Tests (4 tests)
# ═══════════════════════════════════════════════════════════════════════════
class TestConfig(unittest.TestCase):

    def test_engine_order_has_8_engines(self):
        self.assertEqual(len(ENGINE_ORDER), 8)

    def test_sector_tickers_not_empty(self):
        self.assertTrue(len(SECTOR_TICKERS) > 0)

    def test_engine_order_starts_with_macro(self):
        self.assertIn("Macro", ENGINE_ORDER[0])

    def test_engine_order_ends_with_dashboard(self):
        self.assertIn("Dashboard", ENGINE_ORDER[-1])


# ═══════════════════════════════════════════════════════════════════════════
# 7. Adapter Tests (6 tests)
# ═══════════════════════════════════════════════════════════════════════════
class TestAdapters(unittest.TestCase):

    def setUp(self):
        self.raw = SyntheticDataLoader(seed=42).load()

    def test_macro_synthetic_result(self):
        from dss_integration.adapters.macro_adapter import MacroAdapter
        r = MacroAdapter.synthetic_result(self.raw)
        self.assertTrue(0 <= r.macro_score <= 100)

    def test_breadth_synthetic_result(self):
        from dss_integration.adapters.breadth_adapter import BreadthAdapter
        r = BreadthAdapter.synthetic_result(self.raw)
        self.assertTrue(0 <= r.breadth_score <= 100)

    def test_rs_synthetic_result(self):
        from dss_integration.adapters.rs_adapter import RSAdapter
        r = RSAdapter.synthetic_result(self.raw)
        self.assertIn(self.raw.tickers[0], r.sector_results)

    def test_rotation_synthetic_result(self):
        from dss_integration.adapters.rs_adapter import RSAdapter
        from dss_integration.adapters.rotation_adapter import RotationAdapter
        rs = RSAdapter.synthetic_result(self.raw)
        r  = RotationAdapter.synthetic_result(self.raw, rs)
        self.assertIsNotNone(r.dominant_rotation)

    def test_portfolio_synthetic_result(self):
        from dss_integration.adapters.macro_adapter import MacroAdapter
        from dss_integration.adapters.portfolio_adapter import PortfolioAdapter
        macro = MacroAdapter.synthetic_result(self.raw)
        r = PortfolioAdapter.synthetic_result(self.raw, {"macro_result": macro})
        self.assertIn(r.action, ("BUY","SELL","HOLD","WAIT"))

    def test_optimizer_synthetic_result(self):
        from dss_integration.adapters.optimizer_adapter import OptimizerAdapter
        r = OptimizerAdapter.synthetic_result(self.raw, {})
        self.assertIsNotNone(r)


if __name__ == "__main__":
    unittest.main(verbosity=2)

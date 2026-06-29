#!/usr/bin/env python3
"""
dss_integration/app.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DSS (Decision Support System) — Integration Layer
Entry Point

실행:  python app.py
       python app.py --json        (JSON 저장)
       python app.py --no-monitor  (모니터 출력 생략)

⭐⭐⭐⭐⭐ 이 파일에는 Business Logic이 없다.
         오직 Engine을 순서대로 호출할 뿐이다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations
import argparse
import sys
import os

# ── Path Setup ─────────────────────────────────────────────────────────
_HERE        = os.path.dirname(os.path.abspath(__file__))
_OUTPUTS     = os.path.dirname(_HERE)
_PROJECT     = os.path.dirname(_OUTPUTS)

for p in [_OUTPUTS, _HERE]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── DSS Integration Layer Imports ──────────────────────────────────────
from dss_integration.utils.logger            import get_logger
from dss_integration.monitor.engine_monitor  import EngineMonitor
from dss_integration.data.synthetic_loader   import SyntheticDataLoader
from dss_integration.core.dss_pipeline       import DSSPipeline
from dss_integration.core.json_serializer    import JSONSerializer
from dss_integration.config.settings         import RESULT_JSON

log = get_logger("app")


def parse_args():
    parser = argparse.ArgumentParser(description="DSS Pipeline")
    parser.add_argument("--json",       action="store_true",
                        help="JSON 결과 저장 (dss_result.json)")
    parser.add_argument("--no-monitor", action="store_true",
                        help="Engine Monitor 출력 생략")
    parser.add_argument("--run-id",     default="",
                        help="실행 ID (기본: 타임스탬프)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # [1] Logger 초기화 (get_logger 호출 시 자동 설정됨)
    log.info("DSS Decision Support System — Integration Layer")

    # [2] Engine Monitor 초기화
    monitor = EngineMonitor(run_id=args.run_id)

    # [3] Data 로드
    log.info("Loading market data (Synthetic Mode)...")
    loader   = SyntheticDataLoader()
    raw_data = loader.load()
    log.info(f"Data loaded: {raw_data.market_date} | "
             f"{len(raw_data.tickers)} tickers | VIX={raw_data.vix}")

    # [4] Pipeline 실행
    pipeline = DSSPipeline(monitor=monitor, run_id=args.run_id)
    try:
        result = pipeline.run(raw_data)
    except Exception as exc:
        log.critical(f"Pipeline fatal error: {exc}", exc_info=True)
        monitor.print_report()
        return 1

    # [5] Engine Monitor 출력
    if not args.no_monitor:
        monitor.print_report()

    # [6] 결과 요약 출력
    _print_summary(result)

    # [7] JSON 저장 (옵션)
    if args.json:
        serializer = JSONSerializer()
        serializer.save(result, RESULT_JSON)
        log.info(f"JSON 저장 완료: {RESULT_JSON}")
        print(f"\n  💾 JSON 저장: {RESULT_JSON}")

    return 0 if result.pipeline_success else 1


def _print_summary(result) -> None:
    """DSSResult 핵심 요약을 콘솔에 출력."""
    print("\n" + "━" * 55)
    print("  📊 DSS Result Summary")
    print("━" * 55)
    print(f"  Run ID         : {result.run_id}")
    print(f"  Date           : {result.run_date[:19]}")
    print(f"  System Health  : {result.system_health}")
    print(f"  Pipeline       : {'✅ SUCCESS' if result.pipeline_success else '❌ FAILED'}")
    print()
    print(f"  Macro State    : {result.macro_state}")
    print(f"  Recommended    : {result.recommended_action}")
    print(f"  Confidence     : {result.overall_confidence:.1f}/100")
    print(f"  Validation     : {result.validation_grade}")
    if result.top_opportunities:
        print(f"  Top ETF        : {', '.join(result.top_opportunities)}")
    if result.monitor_result:
        m = result.monitor_result
        print(f"\n  Engines        : {m.success_count}/{len(m.engines)} OK "
              f"({m.total_elapsed_sec:.2f}초)")
    print("━" * 55 + "\n")


if __name__ == "__main__":
    sys.exit(main())

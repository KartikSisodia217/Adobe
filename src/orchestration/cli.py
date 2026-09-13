import sys
import json
import asyncio
from src.orchestration.orchestrator import execute_audit
from src.reporting.report_builder import build_minimal_error_report

async def main():
    input_data = sys.stdin.read()
    try:
        data = json.loads(input_data)
        input_url = data.get("input_url")
        if not input_url or not isinstance(input_url, str):
            report = build_minimal_error_report("unknown", "Invalid input_url in JSON").model_dump(mode='json')
        else:
            # 270s hard stop
            external_sources = data.get("external_sources", [])
            if not isinstance(external_sources, list):
                external_sources = []
            report = await asyncio.wait_for(execute_audit(input_url, external_sources), timeout=270.0)
    except asyncio.TimeoutError:
        url = input_url if 'input_url' in locals() and isinstance(input_url, str) else "unknown"
        report = build_minimal_error_report(url, "Audit hit 270s hard stop").model_dump(mode='json')
    except Exception as e:
        url = input_url if 'input_url' in locals() and isinstance(input_url, str) else "unknown"
        report = build_minimal_error_report(url, f"Unexpected error: {str(e)}").model_dump(mode='json')
        
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())

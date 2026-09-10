import sys
import json
from src.schemas.v1.context import AuditContext
from src.access_content.auditor import run_access_content_audit

def main():
    # Read from stdin
    input_data = sys.stdin.read()
    if not input_data:
        return
        
    try:
        context_dict = json.loads(input_data)
        context = AuditContext(**context_dict)
    except Exception as e:
        print(json.dumps({
            "skill": "access-content-auditor",
            "status": "error",
            "error": str(e),
            "findings": [],
            "coverage": {}
        }))
        return
        
    try:
        facts, findings = run_access_content_audit(context)
        
        # Serialize findings
        findings_dicts = [f.model_dump(mode='json') for f in findings]
        facts_dicts = [f.model_dump(mode='json') for f in facts]
        
        output = {
            "skill": "access-content-auditor",
            "status": "ok",
            "findings": findings_dicts,
            "structured_facts": facts_dicts, # Passing facts to orchestrator/M3
            "coverage": {}
        }
        print(json.dumps(output))
    except Exception as e:
        print(json.dumps({
            "skill": "access-content-auditor",
            "status": "error",
            "error": str(e),
            "findings": [],
            "coverage": {}
        }))

if __name__ == "__main__":
    main()

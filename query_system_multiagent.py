from __future__ import annotations

from typing import Any

from agents.a5_template import build_template_pipeline


PIPELINE = build_template_pipeline()


def answer_question(question: str) -> dict[str, Any]:
    """
    Student template entry.
    Keep output contract for auto_test_a5.py:
    {
      "answer": str,
      "safety_decision": "ALLOW"|"REJECT",
      "diagnosis": "SUCCESS"|"QUERY_ERROR"|"SCHEMA_MISMATCH"|"NO_DATA",
      "repair_attempted": bool,
      "repair_changed": bool,
      "explanation": str
    }
    """
    nlu = PIPELINE["nlu"]
    security_agent = PIPELINE["security"]
    planner = PIPELINE["planner"]
    executor = PIPELINE["executor"]
    diagnosis_agent = PIPELINE["diagnosis"]
    repair_agent = PIPELINE["repair"]
    explanation_agent = PIPELINE["explanation"]

    intent = nlu.run(question)
    security = security_agent.run(question, intent)

    if security["decision"] == "REJECT":
        diagnosis = {"label": "QUERY_ERROR", "reason": "Blocked by policy."}
        answer = "Request rejected by security policy."
        explanation = explanation_agent.run(question, intent, security, diagnosis, answer, False)
        return {
            "answer": answer,
            "safety_decision": "REJECT",
            "diagnosis": diagnosis["label"],
            "repair_attempted": False,
            "repair_changed": False,
            "explanation": explanation,
        }

    plan = planner.run(intent)
    execution = executor.run(plan)
    diagnosis = diagnosis_agent.run(execution)

    repair_attempted = False
    repair_changed = False
    if diagnosis["label"] in {"QUERY_ERROR", "SCHEMA_MISMATCH", "NO_DATA"}:
        repair_attempted = True
        repaired_plan = repair_agent.run(diagnosis, plan, intent)
        repair_changed = repaired_plan != plan
        
        # Re-execute if repaired
        if repair_changed:
            execution = executor.run(repaired_plan)
            diagnosis = diagnosis_agent.run(execution)

    # Explanation agent generates the final string answer and explanation
    final_output = explanation_agent.run(question, intent, security, diagnosis, execution, repair_attempted)
    answer = final_output.get("answer", "")
    explanation = final_output.get("explanation", "")
    
    # Check failure cases for missing data
    if diagnosis["label"] != "SUCCESS" and not answer:
        answer = "I don't have enough information to answer this."

    return {
        "answer": answer,
        "safety_decision": "ALLOW",
        "diagnosis": diagnosis["label"],
        "repair_attempted": repair_attempted,
        "repair_changed": repair_changed,
        "explanation": explanation,
    }


def run_multiagent_qa(question: str) -> dict[str, Any]:
    return answer_question(question)

def run_qa(question: str) -> dict[str, Any]:
    return answer_question(question)

if __name__ == "__main__":
    while True:
        q = input("Question (type exit): ").strip()
        if not q or q.lower() in {"exit", "quit"}:
            break
        print(answer_question(q))

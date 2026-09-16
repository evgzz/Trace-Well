from pathlib import Path

from tracewell.comparator import compare_pair, required_constructs
from tracewell.evaluator import evaluate_case
from tracewell.loader import load_case_pair
from tracewell.models import Verdict
from tracewell.reference_agent import ReferenceAgent

FIXTURE = Path(__file__).resolve().parents[1] / "cases" / "fixtures" / "po7-spec-inconsistent.yaml"


def test_po7_fixture_forces_global_review_before_behavioral_judgment():
    pair = load_case_pair(FIXTURE)
    agent = ReferenceAgent()
    constructs = required_constructs(pair)

    canonical_trace = agent.run(pair.canonical_case, run_id="po7:canonical", mode="respect_context")
    perturbed_trace = agent.run(pair.perturbed_case, run_id="po7:perturbed", mode="respect_context")

    canonical_results = evaluate_case(pair.canonical_case, canonical_trace, constructs)
    perturbed_results = evaluate_case(pair.perturbed_case, perturbed_trace, constructs)
    result = compare_pair(pair, canonical_results, perturbed_results)

    # Observable behavior follows the pair expectation: continue -> request_human_review.
    assert canonical_results[0].observed_value == "continue"
    assert perturbed_results[0].observed_value == "request_human_review"

    # But the perturbed EvaluationContract requires execute_action, making the
    # expectation itself materially inconsistent. Global REVIEW therefore wins.
    assert result.metadata["specification_inconsistency"] is True
    assert result.pair_result == Verdict.REVIEW

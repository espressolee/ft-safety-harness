import unittest

from ft_safety_harness.result import (
    count_outcomes,
    expectation_status,
    observed_status,
    qualification_status,
)


class ResultLogicTests(unittest.TestCase):
    def trials(self, *outcomes: str):
        return [{"outcome": outcome} for outcome in outcomes]

    def test_mixed_is_not_nominal(self):
        counts = count_outcomes(self.trials("CLEAN", "CRASH"))
        self.assertEqual(observed_status(counts), "MIXED")

    def test_crash_expectation_requires_no_underdetermined_trial(self):
        counts = count_outcomes(self.trials("CRASH", "UNDERDETERMINED"))
        self.assertEqual(
            expectation_status("at_least_one_crash", counts, 2), "VIOLATED"
        )

    def test_crash_expectation_requires_no_timeout_trial(self):
        counts = count_outcomes(self.trials("CRASH", "TIMEOUT"))
        self.assertEqual(
            expectation_status("at_least_one_crash", counts, 2), "VIOLATED"
        )

    def test_undeclared_arm_makes_run_unassessed(self):
        arms = [
            {"expectation_status": "SATISFIED"},
            {"expectation_status": "NOT_DECLARED"},
        ]
        self.assertEqual(qualification_status(arms), "UNASSESSED")

    def test_violation_has_precedence(self):
        arms = [
            {"expectation_status": "NOT_DECLARED"},
            {"expectation_status": "VIOLATED"},
        ]
        self.assertEqual(qualification_status(arms), "FAIL")


if __name__ == "__main__":
    unittest.main()

import unittest
from fractions import Fraction as F

from audit.design.v03_tau_rule_study import ALPHAS, feasible4, four_metrics, jaccard_stability, rule_taus
from audit.exact import ExactTaus, feasible


def m(f, d, c, u):
    return {"fidelity": F(f), "deviation": F(d), "consistency": F(c), "uncertainty": F(u)}


class TauRuleHelperTests(unittest.TestCase):
    def test_order_statistics_count_duplicates(self):
        ms = [m("4/5", "0", "1", "1/2"), m("4/5", "1/10", "9/10", "3/5"), m("9/10", "1/5", "1", "2/5"),
              m("1", "1/10", "7/10", "1/2")]
        t = rule_taus(ms, 4, 0)
        self.assertEqual((t.tau_s, t.tau_d, t.tau_t, t.tau_b), (F(4, 5), F(1, 5), F(7, 10), F(3, 5)))
        t = rule_taus(ms, 4, 1)  # 2nd smallest / 2nd largest, a duplicate counts
        self.assertEqual((t.tau_s, t.tau_d, t.tau_t, t.tau_b), (F(4, 5), F(1, 10), F(9, 10), F(1, 2)))
        t = rule_taus(ms, 2, 0)  # prefix of the first two worlds
        self.assertEqual((t.tau_s, t.tau_d, t.tau_t, t.tau_b), (F(4, 5), F(1, 10), F(9, 10), F(3, 5)))

    def test_feasible4_matches_exact_feasible(self):
        taus = ExactTaus(F(4, 5), F(1, 10), F(9, 10), F(3, 5))
        for mm in (m("4/5", "1/10", "9/10", "3/5"), m("79/100", "0", "1", "0"), m("1", "11/100", "1", "0"),
                   m("1", "0", "89/100", "0"), m("1", "0", "1", "61/100")):
            self.assertEqual(feasible4(mm, taus), feasible({**mm, "new_true": F(1)}, taus))

    def test_four_metrics_drops_everything_else(self):
        ex = {**m("1", "0", "1", "0"), "new_true": F(1, 2), "new_false": F(1, 3), "hyp_count": 3}
        self.assertEqual(set(four_metrics(ex)), {"fidelity", "deviation", "consistency", "uncertainty"})

    def test_jaccard_stability(self):
        a, b = ["0.95", "0.90"], ["0.90", "0.85"]
        self.assertEqual(jaccard_stability([[a, [], a], [b, [], a]]), [F(1, 3), F(1), F(1)])
        self.assertEqual(len(ALPHAS), 10)


if __name__ == "__main__":
    unittest.main()

import unittest

from tesaron.criterion import (
    DEFAULT_GRID,
    PLACEHOLDER_TAUS,
    Metrics,
    Point,
    T1Result,
    hypervolume,
    is_feasible,
    make_point,
    pareto_front,
    point_score,
    t1_world,
)


def metrics(**kw):
    base = dict(
        fidelity=0.9, deviation=0.0, consistency=0.95, uncertainty=0.3, new_true=0.5, new_false=0.2,
        hyp_count=0, hyp_correct=0, validation_agreement=None, boundary_share=None,
        size_E=10, size_I=5, size_H=4, size_K=14,
    )
    base.update(kw)
    return Metrics(**base)


class FeasibilityTests(unittest.TestCase):
    def test_placeholder_values(self):
        self.assertEqual(
            (PLACEHOLDER_TAUS.tau_s, PLACEHOLDER_TAUS.tau_d, PLACEHOLDER_TAUS.tau_t, PLACEHOLDER_TAUS.tau_b),
            (0.8, 0.05, 0.9, 0.5),
        )

    def test_each_constraint(self):
        t = PLACEHOLDER_TAUS
        self.assertTrue(is_feasible(metrics(), t))
        self.assertTrue(is_feasible(metrics(fidelity=0.8, deviation=0.05, consistency=0.9, uncertainty=0.5), t))
        self.assertFalse(is_feasible(metrics(fidelity=0.79), t))
        self.assertFalse(is_feasible(metrics(deviation=0.06), t))
        self.assertFalse(is_feasible(metrics(consistency=0.89), t))
        self.assertFalse(is_feasible(metrics(uncertainty=0.51), t))

    def test_none_makes_infeasible(self):
        self.assertFalse(is_feasible(metrics(fidelity=None), PLACEHOLDER_TAUS))
        self.assertFalse(is_feasible(metrics(new_true=None), PLACEHOLDER_TAUS))

    def test_default_grid(self):
        self.assertEqual(len(DEFAULT_GRID), 15)
        self.assertEqual({a for a, _ in DEFAULT_GRID}, {0.9, 0.8, 0.7, 0.6, 0.5})
        self.assertEqual({k for _, k in DEFAULT_GRID}, {0, 5, 10})

    def test_make_point(self):
        p = make_point((0.7, 5), metrics(new_false=0.25, new_true=0.4), PLACEHOLDER_TAUS)
        self.assertEqual((p.x, p.y, p.feasible, p.config), (0.75, 0.4, True, (0.7, 5)))
        self.assertEqual((p.uncertainty, p.new_false), (0.3, 0.25))


class ParetoTests(unittest.TestCase):
    def test_front_example(self):
        pts = [
            Point(0.9, 0.2), Point(0.8, 0.5), Point(0.5, 0.6), Point(0.6, 0.4),  # last one is dominated
            Point(0.95, 0.9, feasible=False),  # would dominate everything but is infeasible
        ]
        front = pareto_front(pts)
        self.assertEqual([(p.x, p.y) for p in front], [(0.9, 0.2), (0.8, 0.5), (0.5, 0.6)])

    def test_domination_rule(self):
        # equal in one coordinate and greater in the other dominates
        front = pareto_front([Point(0.5, 0.5), Point(0.5, 0.7), Point(0.7, 0.5)])
        self.assertEqual([(p.x, p.y) for p in front], [(0.7, 0.5), (0.5, 0.7)])
        # identical points do not dominate each other
        front = pareto_front([Point(0.5, 0.5, config=(0.7, 5)), Point(0.5, 0.5, config=(0.6, 0))])
        self.assertEqual([p.config for p in front], [(0.6, 0), (0.7, 5)])

    def test_order_is_deterministic(self):
        pts = [Point(0.3, 0.9), Point(0.9, 0.1), Point(0.6, 0.5)]
        a = pareto_front(pts)
        b = pareto_front(list(reversed(pts)))
        self.assertEqual(a, b)
        self.assertEqual([p.x for p in a], [0.9, 0.6, 0.3])

    def test_empty_and_all_infeasible(self):
        self.assertEqual(pareto_front([]), [])
        self.assertEqual(pareto_front([Point(0.5, 0.5, feasible=False)]), [])
        self.assertEqual(pareto_front([Point(0.5, None, feasible=True)]), [])


class HypervolumeTests(unittest.TestCase):
    def test_single_point_is_x_times_y(self):
        self.assertAlmostEqual(hypervolume([Point(0.6, 0.5)]), 0.3)
        self.assertAlmostEqual(hypervolume([(0.6, 0.5)]), 0.3)

    def test_union_of_rectangles(self):
        front = [Point(0.9, 0.2), Point(0.8, 0.5), Point(0.5, 0.6)]
        # strips: [0,.5] x .6, [.5,.8] x .5, [.8,.9] x .2
        self.assertAlmostEqual(hypervolume(front), 0.5 * 0.6 + 0.3 * 0.5 + 0.1 * 0.2)
        # a dominated point adds nothing
        self.assertAlmostEqual(hypervolume(front + [Point(0.6, 0.4)]), hypervolume(front))
        # order does not matter
        self.assertAlmostEqual(hypervolume(list(reversed(front))), hypervolume(front))

    def test_infeasible_scores_zero_and_empty(self):
        self.assertEqual(hypervolume([]), 0.0)
        self.assertEqual(hypervolume([Point(0.9, 0.9, feasible=False)]), 0.0)
        self.assertEqual(point_score(Point(0.9, 0.9, feasible=False)), 0.0)
        self.assertAlmostEqual(point_score(Point(0.5, 0.5)), 0.25)
        self.assertEqual(hypervolume([Point(0.0, 0.7), Point(0.7, 0.0)]), 0.0)

    def test_reference_point(self):
        self.assertAlmostEqual(hypervolume([(0.6, 0.5)], ref=(0.1, 0.1)), 0.5 * 0.4)


class T1Tests(unittest.TestCase):
    @staticmethod
    def P(u, nf, feasible=True):
        return Point(x=1 - nf, y=0.5, feasible=feasible, uncertainty=u, new_false=nf)

    def test_pass(self):
        # lower uncertainty with new_false higher by at most delta = 0.05
        pts = [self.P(0.4, 0.30), self.P(0.2, 0.34), self.P(0.1, 0.25)]
        self.assertIs(t1_world(pts), T1Result.PASS)

    def test_fail(self):
        pts = [self.P(0.4, 0.30), self.P(0.2, 0.34), self.P(0.1, 0.40)]  # 0.40 - 0.30 = 0.10 > 0.05
        self.assertIs(t1_world(pts), T1Result.FAIL)
        self.assertIs(t1_world(pts, delta=0.2), T1Result.PASS)  # delta is a parameter

    def test_boundary_delta_is_inclusive(self):
        pts = [self.P(0.5, 0.25), self.P(0.25, 0.5)]
        self.assertIs(t1_world(pts, delta=0.25), T1Result.PASS)
        self.assertIs(t1_world(pts, delta=0.125), T1Result.FAIL)

    def test_undefined(self):
        self.assertIs(t1_world([]), T1Result.UNDEFINED)
        self.assertIs(t1_world([self.P(0.3, 0.1)]), T1Result.UNDEFINED)
        # equal uncertainty values only
        self.assertIs(t1_world([self.P(0.3, 0.1), self.P(0.3, 0.9)]), T1Result.UNDEFINED)
        # only one feasible point
        self.assertIs(t1_world([self.P(0.3, 0.1), self.P(0.1, 0.9, feasible=False)]), T1Result.UNDEFINED)

    def test_infeasible_points_are_ignored(self):
        pts = [self.P(0.4, 0.30), self.P(0.2, 0.31), self.P(0.1, 0.99, feasible=False)]
        self.assertIs(t1_world(pts), T1Result.PASS)

    def test_result_values(self):
        self.assertEqual({r.value for r in T1Result}, {"pass", "fail", "undefined"})


if __name__ == "__main__":
    unittest.main()

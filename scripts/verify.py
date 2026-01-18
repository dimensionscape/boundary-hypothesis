"""Finite checks accompanying the boundary hypothesis manuscript."""
import json
import math
from fractions import Fraction as F
import numpy as np


def creations(modes):
    size = 1 << modes
    result = []
    for j in range(modes):
        matrix = np.zeros((size, size), dtype=np.int64)
        for mask in range(size):
            if not mask & (1 << j):
                lower = (mask & ((1 << j) - 1)).bit_count()
                matrix[mask | (1 << j), mask] = (-1) ** lower
        result.append(matrix)
    return result


def count_law(vacancies, time):
    unfilled = math.exp(-time)
    filled = -math.expm1(-time)
    return np.array([
        math.comb(vacancies, j) * filled ** j
        * unfilled ** (vacancies - j)
        for j in range(vacancies + 1)
    ])


def transitions(capacity, exposure):
    result = np.zeros((capacity, capacity))
    for initial in range(1, capacity + 1):
        result[initial - 1:, initial - 1] = count_law(
            capacity - initial, exposure)
    return result


def ordered_moment(powers):
    """Normalized monomial integral on 0 < u_1 < ... < u_m < 1."""
    value = F(math.factorial(len(powers)))
    degree = 0
    for index, power in enumerate(powers, 1):
        degree += power
        value /= index + degree
    return value


def packing_integral(n, delta, xi, chi):
    """Integrate each possible insertion's two sampling weights exactly."""
    m = n + 1
    width = 1 - n * delta
    if width <= 0:
        return F(0)
    volume_ratio = (width ** m / math.factorial(m)) / (
        (1 - (n - 1) * delta) ** n / math.factorial(n))
    constants = [2 * i * delta - 1 for i in range(m)]
    first = []
    for i in range(m):
        powers = [0] * m
        powers[i] = 1
        first.append(ordered_moment(powers))
    means = [c + 2 * width * u for c, u in zip(constants, first)]
    integrated = F(0)
    for inserted in range(m):
        others = [j for j in range(m) if j != inserted]
        cross = F(0)
        for j in others:
            powers = [0] * m
            powers[inserted] = powers[j] = 1
            cross += (constants[inserted] * constants[j]
                      + 2 * width * (constants[inserted] * first[j]
                                     + constants[j] * first[inserted])
                      + 4 * width ** 2 * ordered_moment(powers))
        integrated += (1 + chi * means[inserted]
                       + xi * sum(means[j] for j in others) / n
                       + xi * chi * cross / n)
    return volume_ratio * integrated


def run():
    report = {}
    operator_cases = 0
    for modes in range(1, 6):
        channels = creations(modes)
        size = 1 << modes
        identity = np.eye(size, dtype=np.int64)
        number = np.diag([b.bit_count() for b in range(size)])
        available = np.zeros_like(identity)
        adjoint = np.zeros_like(identity)
        for j, creation in enumerate(channels):
            annihilation = creation.T
            for k, other in enumerate(channels):
                target = identity if j == k else 0 * identity
                assert np.array_equal(
                    annihilation @ other + other @ annihilation,
                    target)
                assert not np.any(creation @ other + other @ creation)
            product = annihilation @ creation
            available += product
            adjoint += (2 * annihilation @ number @ creation
                        - product @ number - number @ product)
        assert np.array_equal(available, modes * identity - number)
        assert np.array_equal(adjoint, 2 * available)
        full = np.zeros((size, size), dtype=np.int64)
        full[-1, -1] = 1
        for creation in channels:
            product = creation.T @ creation
            dissipator = (2 * creation @ full @ creation.T
                          - product @ full - full @ product)
            assert not np.any(dissipator)
        operator_cases += 1
    report['operator_cases'] = operator_cases

    count_cases = 0
    max_forward_error = 0.0
    for vacancies in range(9):
        generator = np.zeros((vacancies + 1, vacancies + 1))
        for j in range(vacancies):
            generator[j, j] = -(vacancies - j)
            generator[j + 1, j] = vacancies - j
        for time in (0.0, 0.01, 0.1, 1.0, 2.0, 5.0, 20.0):
            probabilities = count_law(vacancies, time)
            derivative = np.array([
                math.comb(vacancies, j) * sum(
                    (-1) ** k * math.comb(j, k)
                    * -(vacancies - j + k)
                    * math.exp(-time * (vacancies - j + k))
                    for k in range(j + 1))
                for j in range(vacancies + 1)
            ])
            error = np.max(np.abs(
                derivative - generator @ probabilities))
            max_forward_error = max(max_forward_error, float(error))
            assert error < 2e-9
            assert abs(probabilities.sum() - 1) < 2e-12
            assert np.all(probabilities >= 0)
            expected = vacancies * -math.expm1(-time)
            assert abs(probabilities @ np.arange(vacancies + 1)
                       - expected) < 2e-12
            expected_variance = expected * math.exp(-time)
            variance = probabilities @ (
                np.arange(vacancies + 1) - expected) ** 2
            assert abs(variance - expected_variance) < 2e-12
            assert abs(probabilities[-1]
                       - (-math.expm1(-time)) ** vacancies) < 2e-12
            count_cases += 1
    report['count_cases'] = count_cases
    report['max_forward_error'] = max_forward_error

    for v in range(1, 17):
        integral = sum((F((-1) ** (j + 1) * math.comb(v, j), j)
                        for j in range(1, v + 1)), F(0))
        harmonic = sum((F(1, j) for j in range(1, v + 1)), F(0))
        assert integral == harmonic
    report['exact_harmonic_cases'] = 16

    delta, xi, chi = F(3, 10), F(1, 2), F(3, 4)
    expected = [F(35819, 80000), F(148, 1225), F(749, 512000)]
    biased = []
    for n in range(1, 4):
        fraction = (1 - n * delta) ** (n + 1)
        fraction /= (1 - (n - 1) * delta) ** n
        bias = (2 * delta - (n - 2) * delta ** 2) / 3
        biased.append(fraction * (1 - xi * chi * bias))
    assert biased == expected
    report['packing_fractions'] = [str(x) for x in biased]
    report['mean_opportunities'] = float(sum(F(1) / x for x in biased))

    packing_cases = 0
    for gap in (F(2, 3), F(1, 2), F(1, 3), F(3, 10), F(1, 4), F(1, 5)):
        capacity = math.ceil(1 / gap)
        for n in range(1, capacity):
            uniform = (1 - n * gap) ** (n + 1)
            uniform /= (1 - (n - 1) * gap) ** n
            coefficient = (2 * gap - (n - 2) * gap ** 2) / 3
            for x_bias, c_bias in ((F(0), F(0)), (F(1, 2), F(3, 4)),
                                    (F(-1, 2), F(3, 4)),
                                    (F(9, 10), F(-9, 10)),
                                    (F(9, 10), F(9, 10))):
                direct = packing_integral(n, gap, x_bias, c_bias)
                formula = uniform * (1 - x_bias * c_bias * coefficient)
                assert direct == formula
                assert 0 < direct <= 1
                packing_cases += 1
        assert packing_integral(capacity, gap, F(1, 2), F(3, 4)) == 0
    report['packing_integral_cases'] = packing_cases

    composition_cases = 0
    for capacity in range(1, 13):
        for first, second in ((0, 0), (0, 1), (0.1, 0.4),
                              (1, 2), (4, 0.05), (5, 7)):
            direct = transitions(capacity, first + second)
            composed = (transitions(capacity, second)
                        @ transitions(capacity, first))
            assert np.max(np.abs(direct - composed)) < 3e-12
            composition_cases += 1
    report['composition_cases'] = composition_cases

    thresholds = np.linspace(0.0001, 8.0, 20001)
    kappa, tau = 0.7, 1.3
    exposure = kappa * tau
    r_birth = -tau + thresholds / kappa
    b_birth = np.where(thresholds < exposure,
                       tau * np.log(thresholds / exposure),
                       (thresholds - exposure) / kappa)
    future = thresholds >= exposure
    assert np.max(np.abs(r_birth[future] - b_birth[future])) < 3e-12
    for time in (0, 0.2, 1, 3, 10):
        assert np.array_equal(r_birth <= time, b_birth <= time)
    report['matched_future_thresholds'] = len(thresholds)
    report['checks_passed'] = True
    return report


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))

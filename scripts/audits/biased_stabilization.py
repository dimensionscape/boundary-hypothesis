"""Exact rates and independent integration checks for biased structural exploration."""

from fractions import Fraction as F
from math import ceil
from pathlib import Path
import json
import numpy as np


def volume(count, delta):
    remaining = max(F(0), 1 - (count - 1) * delta)
    factorial = 1
    for k in range(2, count + 1):
        factorial *= k
    return remaining ** count / factorial


def uniform_acceptance(count, delta):
    return (count + 1) * volume(count + 1, delta) / volume(count, delta)


def bias_penalty(count, delta):
    return (2 * delta - (count - 2) * delta ** 2) / 3


def biased_acceptance(count, delta, config_bias, candidate_bias):
    return uniform_acceptance(count, delta) * (1 - config_bias * candidate_bias * bias_penalty(count, delta))


def weighted_available_length(positions, delta, candidate_bias):
    """Integrate a linear candidate density over actual available intervals."""
    def integral(left, right):
        admitted = right > left
        return np.where(admitted, right - left + candidate_bias * (right ** 2 - right - left ** 2 + left), 0.0)

    length = integral(np.zeros(len(positions)), positions[:, 0] - delta)
    length += integral(positions[:, -1] + delta, np.ones(len(positions)))
    if positions.shape[1] > 1:
        length += integral(positions[:, :-1] + delta, positions[:, 1:] - delta).sum(axis=1)
    return length


delta = F(3, 10)
config_bound, candidate_bound = F(1, 2), F(3, 4)
capacity = ceil(1 / delta)
base_rates = [uniform_acceptance(n, delta) for n in range(1, capacity + 1)]
lower_rates = [biased_acceptance(n, delta, config_bound, candidate_bound) for n in range(1, capacity + 1)]
assert lower_rates == [F(35819, 80000), F(148, 1225), F(749, 512000), F(0)]
mean_attempt_bound = sum((1 / chance for chance in lower_rates[:-1]), F(0))
general_density_bound = sum((8 / chance for chance in base_rates[:-1]), F(0))

# Check exact positivity and minimum bounds over many structural parameters.
exact_cases = 0
for denominator in range(2, 13):
    for numerator in range(1, denominator + 1):
        spacing = F(numerator, denominator)
        maximum = ceil(1 / spacing)
        for count in range(1, maximum):
            penalty = bias_penalty(count, spacing)
            assert 0 < penalty < 1
            for config_bias in (-config_bound, F(0), config_bound):
                for candidate_bias in (-candidate_bound, F(0), candidate_bound):
                    chance = biased_acceptance(count, spacing, config_bias, candidate_bias)
                    lower = biased_acceptance(count, spacing, config_bound, candidate_bound)
                    assert F(0) < lower <= chance <= 1
                    assert chance >= (1 - abs(config_bias)) * (1 - abs(candidate_bias)) * uniform_acceptance(count, spacing)
                    exact_cases += 1

# Uniform configurations provide an independent importance-sampling integral.
# No biased-rate formula is used to construct the measured available intervals.
rng = np.random.default_rng(20261013)
samples = 400_000
integration = []
for count in range(1, capacity + 1):
    remaining = float(1 - (count - 1) * delta)
    positions = np.sort(rng.uniform(0, remaining, (samples, count)), axis=1)
    positions += float(delta) * np.arange(count)
    candidate_marks = rng.uniform(0, 1, samples)
    admitted = np.all(np.abs(positions - candidate_marks[:, None]) > float(delta), axis=1)
    for config_bias, candidate_bias in ((config_bound, candidate_bound), (config_bound, -candidate_bound)):
        c, d = float(config_bias), float(candidate_bias)
        config_weight = 1 + c * (2 * positions.mean(axis=1) - 1)
        integrated_values = config_weight * weighted_available_length(positions, float(delta), d)
        exact = biased_acceptance(count, delta, config_bias, candidate_bias)
        measured = float(integrated_values.mean())
        standard_error = float(integrated_values.std(ddof=1) / np.sqrt(samples))
        assert abs(measured - float(exact)) <= 6 * standard_error + 1e-12
        direct_values = config_weight * (1 + d * (2 * candidate_marks - 1)) * admitted
        direct_mean = float(direct_values.mean())
        direct_error = float(direct_values.std(ddof=1) / np.sqrt(samples))
        assert abs(direct_mean - float(exact)) <= 6 * direct_error + 1e-12
        integration.append({
            'count': count,
            'configuration_bias': str(config_bias),
            'candidate_bias': str(candidate_bias),
            'exact_acceptance': str(exact),
            'measured_integrated_acceptance': measured,
            'integration_standard_error': standard_error,
            'measured_direct_mark_acceptance': direct_mean,
            'direct_mark_standard_error': direct_error,
        })

# A strictly positive but summable exploration schedule can leave a trap forever.
finite_product = F(1)
partial_sum = F(0)
for k in range(1, 21):
    chance = F(1, 2 ** (k + 1))
    partial_sum += chance
    finite_product *= 1 - chance
assert partial_sum < F(1, 2)
assert float(finite_product) > np.exp(-1)

report = {
    'scope': 'Conditional post-first stabilization with biased configuration and candidate densities; no physical origin validation.',
    'seed': 20261013,
    'delta': str(delta),
    'capacity': capacity,
    'configuration_bias_bound': str(config_bound),
    'candidate_bias_bound': str(candidate_bound),
    'worst_case_linear_bias_acceptance': [str(chance) for chance in lower_rates],
    'expected_attempts_upper_bound': str(mean_attempt_bound),
    'expected_attempts_upper_bound_decimal': float(mean_attempt_bound),
    'broader_density_floor_expected_attempts_upper_bound': str(general_density_bound),
    'broader_density_floor_expected_attempts_upper_bound_decimal': float(general_density_bound),
    'exact_parameter_cases_checked': exact_cases,
    'uniform_configuration_samples_per_count': samples,
    'independent_integration_checks': integration,
    'summable_exploration_counterexample_checked': True,
    'checks_passed': True,
}
target = Path(__file__).resolve().parents[2] / 'results' / 'audits' / 'biased-stabilization-audit.json'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'checks_passed': True, 'exact_parameter_cases': exact_cases, 'configuration_samples': capacity * samples, 'expected_attempts_upper_bound': float(mean_attempt_bound), 'output': target.relative_to(Path(__file__).resolve().parents[2]).as_posix()}))

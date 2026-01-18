"""Audit conditional past persistence and matched-future countermodels.

No sampled quantity is a probability that source-free genesis is true.
Infinite-past statements require the written proofs, not finite samples.
"""

from fractions import Fraction
from pathlib import Path
import json
import math
import numpy as np


def transition(capacity, minimum, exposure):
    dimension = capacity - minimum + 1
    result = np.zeros((dimension, dimension))
    survival = math.exp(-exposure)
    filled = -math.expm1(-exposure)
    for start in range(minimum, capacity + 1):
        vacancies = capacity - start
        for added in range(vacancies + 1):
            result[start + added - minimum, start - minimum] = math.comb(vacancies, added) * filled ** added * survival ** (vacancies - added)
    return result


semigroup_cases = 0
survival_cases = 0
maximum_semigroup_error = 0.0
for capacity in range(1, 13):
    for minimum in (0, 1):
        for first, second in ((0, 0), (0, 1), (0.1, 0.4), (1, 2), (4, 0.05), (5, 7)):
            direct = transition(capacity, minimum, first + second)
            composed = transition(capacity, minimum, second) @ transition(capacity, minimum, first)
            error = float(np.max(np.abs(direct - composed)))
            assert error < 3e-12
            maximum_semigroup_error = max(maximum_semigroup_error, error)
            assert np.max(np.abs(direct.sum(axis=0) - 1)) < 3e-12
            semigroup_cases += 1
        maximum_vacancies = capacity - minimum
        for exposure in (0, 0.01, 0.5, 1, 2, 5, 10, 20):
            matrix = transition(capacity, minimum, exposure)
            upper = -math.expm1(maximum_vacancies * math.log(-math.expm1(-exposure))) if exposure > 0 and maximum_vacancies > 0 else (1.0 if maximum_vacancies > 0 else 0.0)
            for start in range(minimum, capacity + 1):
                survival = float(matrix[:-1, start - minimum].sum())
                assert survival <= upper + 3e-12
                if start == minimum:
                    assert abs(survival - upper) < 3e-12
                survival_cases += 1

# An exact positivity obstruction: deficit d(0)=1 in capacity four with
# minimum one would grow beyond its permitted maximum by backward exposure 2.
earlier_deficit = math.exp(2)
assert earlier_deficit > 3
mean_past_exposure_bound = math.log(3)

threshold_cases = []
for vacancies in range(1, 13):
    for significance in (0.05, 0.01, 0.001):
        cutoff_survival = -math.expm1(math.log1p(-significance) / vacancies)
        exposure = -math.log(cutoff_survival)
        unsaturated_probability = -math.expm1(vacancies * math.log1p(-math.exp(-exposure)))
        assert abs(unsaturated_probability - significance) < 5e-13
        threshold_cases.append({'maximum_vacancies': vacancies, 'significance': significance, 'past_exposure_cutoff': exposure})


seed = 20261013
rng = np.random.default_rng(seed)
matched_histories = 0
maximum_future_birth_time_error = 0.0
prehistory_differences = 0
countermodel_cases = []
for capacity in range(2, 9):
    vacancies = capacity - 1
    kappa = 0.25 + capacity / 10
    tau = 0.3 + capacity / 7
    initial_exposure = kappa * tau
    exponentials = rng.exponential(size=(20000, vacancies))
    rooted_births = -tau + exponentials / kappa
    beginningless_births = np.empty_like(exponentials)
    earlier = exponentials < initial_exposure
    beginningless_births[earlier] = tau * np.log(exponentials[earlier] / initial_exposure)
    beginningless_births[~earlier] = (exponentials[~earlier] - initial_exposure) / kappa
    after_observation = ~earlier
    if np.any(after_observation):
        error = float(np.max(np.abs(rooted_births[after_observation] - beginningless_births[after_observation])))
        assert error < 3e-12
        maximum_future_birth_time_error = max(maximum_future_birth_time_error, error)
    # The entire occupied subset, not just its cardinality, agrees at every
    # sampled future time. The written coupling covers all future times.
    for future in (0, 0.1, 1, 3, 10):
        assert np.array_equal(rooted_births <= future, beginningless_births <= future)
    differences = int(np.sum(np.any(beginningless_births < -tau, axis=1)))
    assert differences > 0
    prehistory_differences += differences
    for past in (-3 * tau, -tau, -tau / 2, 0):
        exposure = kappa * tau * math.exp(past / tau)
        expected_mean = 1 + vacancies * -math.expm1(-exposure)
        assert 1 <= expected_mean <= capacity
        if past < 0:
            assert 0 < kappa * math.exp(past / tau) < kappa
    matched_histories += len(exponentials)
    countermodel_cases.append({'capacity': capacity, 'kappa': kappa, 'tau': tau, 'matched_future_histories': len(exponentials), 'histories_with_a_direct_birth_before_the_rooted_boundary': differences})


# Every ordered addition sequence from a specified initial singleton is
# compared as an exact signed basis vector at saturation. Fermionic signs
# become global phases; no singleton label survives in the final density.
import itertools
record_erasure_cases = 0
for capacity in range(1, 7):
    full_mask = (1 << capacity) - 1
    for first in range(capacity):
        for order in itertools.permutations([mode for mode in range(capacity) if mode != first]):
            mask, sign = 1 << first, 1
            for mode in order:
                assert not mask & (1 << mode)
                sign *= (-1) ** ((mask & ((1 << mode) - 1)).bit_count())
                mask |= 1 << mode
            assert mask == full_mask
            assert sign * sign == 1
            record_erasure_cases += 1

report = {
    'scope': 'Past validity limits under specified finite filling laws; matched-future beginningless countermodels when past rates vary; saturation record loss. No proof of absolute absence or concrete genesis.',
    'seed': seed,
    'transition_semigroup_cases': semigroup_cases,
    'maximum_transition_semigroup_error': maximum_semigroup_error,
    'survival_bound_cases': survival_cases,
    'ensemble_deficit_example': {'capacity': 4, 'minimum': 1, 'present_mean_deficit': 1, 'maximum_valid_past_exposure': mean_past_exposure_bound, 'deficit_at_backward_exposure_two': earlier_deficit},
    'significance_cutoffs': threshold_cases,
    'countermodel_cases': countermodel_cases,
    'matched_future_histories': matched_histories,
    'maximum_future_birth_time_error': maximum_future_birth_time_error,
    'countermodel_histories_with_different_prehistory': prehistory_differences,
    'exact_saturated_record_erasure_cases': record_erasure_cases,
    'checks_passed': True,
}
target = Path(__file__).resolve().parents[2] / 'results' / 'audits' / 'past-persistence-audit.json'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'checks_passed': True, 'transition_cases': semigroup_cases, 'survival_cases': survival_cases, 'matched_future_histories': matched_histories, 'record_erasure_cases': record_erasure_cases, 'output': target.relative_to(Path(__file__).resolve().parents[2]).as_posix()}))

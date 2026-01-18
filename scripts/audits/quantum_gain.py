"""Independent finite checks for a conditional gain response and count law."""

from fractions import Fraction
from pathlib import Path
import json
import math
import numpy as np


operator_cases = []
for modes in range(1, 6):
    fock_dimension = 1 << modes
    dimension = 2 * fock_dimension
    identity = np.eye(dimension, dtype=np.int64)
    number = np.diag([mask.bit_count() for mask in range(fock_dimension) for _ in range(2)])
    twice_adjoint_number = np.zeros_like(identity)
    creations = []
    for mode in range(modes):
        creation = np.zeros((fock_dimension, fock_dimension), dtype=np.int64)
        for mask in range(fock_dimension):
            if not (mask & (1 << mode)):
                creation[mask | (1 << mode), mask] = (-1) ** ((mask & ((1 << mode) - 1)).bit_count())
        creation = np.kron(creation, np.eye(2, dtype=np.int64))
        creations.append(creation)
        available = creation.T @ creation
        twice_adjoint_number += 2 * creation.T @ number @ creation - available @ number - number @ available
    assert np.array_equal(twice_adjoint_number, 2 * (modes * identity - number))
    full_fock = np.zeros((fock_dimension, fock_dimension), dtype=np.int64)
    full_fock[-1, -1] = 1
    # Matrix units span every density matrix and observable in the full sector.
    for j in range(2):
        for k in range(2):
            internal_unit = np.zeros((2, 2), dtype=np.int64)
            internal_unit[j, k] = 1
            full_operator = np.kron(full_fock, internal_unit)
            twice_dissipation = np.zeros_like(identity)
            for creation in creations:
                available = creation.T @ creation
                twice_dissipation += 2 * creation @ full_operator @ creation.T - available @ full_operator - full_operator @ available
            assert not np.any(twice_dissipation)
    operator_cases.append({'modes': modes, 'exact_adjoint_number_identity': True, 'full_sector_dissipation_zero': True})


probability_cases = 0
maximum_forward_equation_error = 0.0
maximum_mean_error = 0.0
for capacity in range(1, 9):
    vacant = capacity - 1
    count_generator = np.zeros((capacity, capacity))
    for j in range(vacant):
        rate = vacant - j
        count_generator[j, j] = -rate
        count_generator[j + 1, j] = rate
    for time in (0.0, 0.01, 0.1, 1.0, 2.0, 5.0, 20.0):
        survival = math.exp(-time)
        filled = -math.expm1(-time)
        probabilities = np.array([math.comb(vacant, j) * filled ** j * survival ** (vacant - j) for j in range(capacity)])
        # Differentiate an expanded polynomial, independently of the
        # neighboring-count forward-equation recurrence being checked.
        derivatives = np.array([
            math.comb(vacant, j) * sum(
                (-1) ** ell * math.comb(j, ell) * -(vacant - j + ell) * math.exp(-time * (vacant - j + ell))
                for ell in range(j + 1)
            )
            for j in range(capacity)
        ])
        error = float(np.max(np.abs(derivatives - count_generator @ probabilities)))
        assert error < 2e-10
        assert abs(float(probabilities.sum()) - 1) < 2e-12
        assert np.all(probabilities >= 0)
        mean_error = abs(float(probabilities @ np.arange(1, capacity + 1)) - (capacity - vacant * survival))
        assert mean_error < 2e-12
        maximum_forward_equation_error = max(maximum_forward_equation_error, error)
        maximum_mean_error = max(maximum_mean_error, mean_error)
        probability_cases += 1

mean_integral_cases = []
for vacant in range(1, 13):
    integrated_survival = sum((Fraction((-1) ** (j + 1) * math.comb(vacant, j), j) for j in range(1, vacant + 1)), Fraction(0))
    harmonic = sum((Fraction(1, j) for j in range(1, vacant + 1)), Fraction(0))
    assert integrated_survival == harmonic
    mean_integral_cases.append({'vacant_channels': vacant, 'mean_time_times_per_channel_rate': str(harmonic)})

report = {
    'scope': 'Finite gain-response identities, occupation probabilities, and closure-time law; no source-free-origin or empirical validation.',
    'operator_cases': operator_cases,
    'operator_arithmetic': 'exact integer',
    'count_probability_cases': probability_cases,
    'maximum_forward_equation_error': maximum_forward_equation_error,
    'maximum_mean_error': maximum_mean_error,
    'mean_integral_cases': mean_integral_cases,
    'mean_integral_arithmetic': 'exact rational',
    'checks_passed': True,
}
target = Path(__file__).resolve().parents[2] / 'results' / 'audits' / 'quantum-gain-audit.json'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'checks_passed': True, 'operator_cases': len(operator_cases), 'count_probability_cases': probability_cases, 'exact_mean_integrals': len(mean_integral_cases), 'output': target.relative_to(Path(__file__).resolve().parents[2]).as_posix()}))

"""Checks of conditional response structure, not evidence for concrete genesis.

The written proofs establish the general results. Exact finite stabilizer ranks
and independent matrix evolution check their implementation and degenerate cases.
"""

from fractions import Fraction
from pathlib import Path
import json
import math
import numpy as np


def exact_rank(rows):
    pivots = {}
    for row in rows:
        current = {j: Fraction(int(value)) for j, value in enumerate(row) if value}
        while current:
            column = min(current)
            if column not in pivots:
                scale = current[column]
                pivots[column] = {j: value / scale for j, value in current.items()}
                break
            scale = current[column]
            for j, value in pivots[column].items():
                updated = current.get(j, Fraction(0)) - scale * value
                if updated:
                    current[j] = updated
                else:
                    current.pop(j, None)
    return len(pivots)


def hermitian_basis(dimension):
    basis = []
    for j in range(dimension):
        matrix = np.zeros((dimension, dimension), dtype=complex)
        matrix[j, j] = 1
        basis.append(matrix)
    for j in range(dimension):
        for k in range(j + 1, dimension):
            symmetric = np.zeros((dimension, dimension), dtype=complex)
            symmetric[j, k] = symmetric[k, j] = 1
            antisymmetric = np.zeros((dimension, dimension), dtype=complex)
            antisymmetric[j, k], antisymmetric[k, j] = 1j, -1j
            basis.extend((symmetric, antisymmetric))
    return basis


def random_unitary(dimension, rng):
    raw = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    unitary, _ = np.linalg.qr(raw)
    return unitary


seed = 20261013
rng = np.random.default_rng(seed)
symmetry_cases = []
rotated_states = 0
max_stationarity_error = 0.0
max_covariance_error = 0.0
for dimension in range(1, 7):
    patterns = {
        tuple([1] * dimension),
        tuple(range(1, dimension + 1)),
        tuple([1] * (dimension // 2) + [2] * (dimension - dimension // 2)),
        tuple(1 + j // 2 for j in range(dimension)),
        tuple([1] + [0] * (dimension - 1)),
    }
    for pattern in sorted(patterns):
        basis = hermitian_basis(dimension)
        generators = []
        for j in range(dimension):
            phase = np.eye(dimension, dtype=complex)
            phase[j, j] = -1
            generators.append(phase)
        for eigenvalue in sorted(set(pattern)):
            group = [j for j, value in enumerate(pattern) if value == eigenvalue]
            for j, k in zip(group, group[1:]):
                swap = np.eye(dimension, dtype=complex)
                swap[[j, k]] = swap[[k, j]]
                generators.append(swap)
        constraints = []
        for unitary in generators:
            changes = [unitary @ matrix @ unitary.conj().T - matrix for matrix in basis]
            real_rows = np.stack([change.real.ravel() for change in changes], axis=1)
            imag_rows = np.stack([change.imag.ravel() for change in changes], axis=1)
            constraints.extend(real_rows.astype(int).tolist())
            constraints.extend(imag_rows.astype(int).tolist())
        rank = exact_rank(constraints)
        invariant_dimension = dimension * dimension - rank
        assert invariant_dimension == len(set(pattern))
        rho_diagonal = np.diag(np.array(pattern, dtype=float) / sum(pattern))
        for _ in range(16):
            rotation = random_unitary(dimension, rng)
            values = {value: rng.normal() for value in set(pattern)}
            generator_diagonal = np.diag([values[value] for value in pattern])
            rho = rotation @ rho_diagonal @ rotation.conj().T
            generator = rotation @ generator_diagonal @ rotation.conj().T
            error = float(np.linalg.norm(generator @ rho - rho @ generator))
            assert error < 2e-12
            max_stationarity_error = max(max_stationarity_error, error)
            # A covariant nonunitary map is a counterexample to an unrestricted
            # claim that covariance forbids every type of change.
            further_rotation = random_unitary(dimension, rng)
            attenuation = math.exp(-0.7 * 0.6)
            transformed = attenuation * rho + (1 - attenuation) * np.eye(dimension) / dimension
            rotated_rho = further_rotation @ rho @ further_rotation.conj().T
            transformed_rotated = attenuation * rotated_rho + (1 - attenuation) * np.eye(dimension) / dimension
            covariance_error = float(np.linalg.norm(transformed_rotated - further_rotation @ transformed @ further_rotation.conj().T))
            assert covariance_error < 2e-12
            max_covariance_error = max(max_covariance_error, covariance_error)
            if len(set(pattern)) > 1:
                assert np.linalg.norm(transformed - rho) > 1e-5
            rotated_states += 1
        symmetry_cases.append({
            'dimension': dimension,
            'spectrum_pattern': pattern,
            'exact_constraint_rank': rank,
            'invariant_hermitian_dimension': invariant_dimension,
            'distinct_eigenvalues': len(set(pattern)),
        })


capacity_cases = []
states_checked = 0
successful_jump_channels = 0
max_rate_error = 0.0
max_number_error = 0.0
for modes in range(1, 6):
    occupancy_dimension = 1 << modes
    dimension = 2 * occupancy_dimension
    creations = []
    for mode in range(modes):
        creation = np.zeros((occupancy_dimension, occupancy_dimension), dtype=np.int64)
        for mask in range(occupancy_dimension):
            if mask & (1 << mode):
                continue
            parity = (mask & ((1 << mode) - 1)).bit_count()
            creation[mask | (1 << mode), mask] = (-1) ** parity
        creations.append(np.kron(creation, np.eye(2, dtype=np.int64)))
    number_diagonal = np.array([mask.bit_count() for mask in range(occupancy_dimension) for _ in range(2)])
    number = np.diag(number_diagonal)
    free_channels = sum((creation.T @ creation for creation in creations), np.zeros((dimension, dimension), dtype=np.int64))
    assert np.array_equal(free_channels, modes * np.eye(dimension, dtype=np.int64) - number)
    assert np.sum(number_diagonal == modes) == 2
    for occupied in range(1, modes + 1):
        indices = np.flatnonzero(number_diagonal == occupied)
        block_size = len(indices)
        raw = rng.normal(size=(block_size, block_size)) + 1j * rng.normal(size=(block_size, block_size))
        generator = (raw + raw.conj().T) / 2
        eigenvalues, eigenvectors = np.linalg.eigh(generator)
        unitary = (eigenvectors * np.exp(-0.37j * eigenvalues)) @ eigenvectors.conj().T
        for _ in range(32):
            block_state = rng.normal(size=block_size) + 1j * rng.normal(size=block_size)
            block_state /= np.linalg.norm(block_state)
            before = np.zeros(dimension, dtype=complex)
            before[indices] = block_state
            after = np.zeros(dimension, dtype=complex)
            after[indices] = unitary @ block_state
            number_error = float(np.linalg.norm(number @ after - occupied * after))
            assert number_error < 2e-12
            max_number_error = max(max_number_error, number_error)
            for state in (before, after):
                weights = [float(np.vdot(creation @ state, creation @ state).real) for creation in creations]
                rate_error = abs(sum(weights) / modes - (1 - occupied / modes))
                assert rate_error < 2e-12
                max_rate_error = max(max_rate_error, rate_error)
                for creation, weight in zip(creations, weights):
                    if weight > 1e-10:
                        next_state = creation @ state / math.sqrt(weight)
                        assert np.linalg.norm(number @ next_state - (occupied + 1) * next_state) < 2e-12
                        successful_jump_channels += 1
                    elif occupied == modes:
                        assert np.linalg.norm(creation @ state) == 0
            if occupied == modes:
                assert np.linalg.norm(np.outer(after, after.conj()) - np.outer(before, before.conj())) > 1e-7
            states_checked += 1
    capacity_cases.append({'modes': modes, 'full_sector_dimension': 2, 'new_sector_checks_passed': True})


sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
sigma_z = np.diag([1, -1]).astype(complex)
initial_internal = np.array([1, 1], dtype=complex) / math.sqrt(2)
spin_errors = []
for time in np.linspace(0, 2 * math.pi, 101):
    unitary = math.cos(time / 2) * np.eye(2) - 1j * math.sin(time / 2) * sigma_z
    internal = unitary @ initial_internal
    expectation = float(np.vdot(internal, sigma_x @ internal).real)
    spin_errors.append(abs(expectation - math.cos(time)))
assert max(spin_errors) < 2e-12

four_mode_rates = [Fraction(4 - occupied, 4) for occupied in range(1, 5)]
four_mode_means = [1 / rate for rate in four_mode_rates[:-1]]
four_mode_mean_ratios = [four_mode_means[j + 1] / four_mode_means[j] for j in range(2)]
assert four_mode_mean_ratios == [Fraction(3, 2), Fraction(2)]

report = {
    'scope': 'Conditional finite-dimensional response and restricted addition closure; no concrete source-free realization, cosmological prediction, or empirical validation.',
    'seed': seed,
    'symmetry_constraint_arithmetic': 'Exact rational row reduction of integer constraint matrices',
    'symmetry_cases': symmetry_cases,
    'rotated_state_checks': rotated_states,
    'maximum_stationarity_commutator_norm': max_stationarity_error,
    'maximum_nonunitary_counterexample_covariance_error': max_covariance_error,
    'capacity_cases': capacity_cases,
    'post_first_sector_states_checked': states_checked,
    'successful_creation_channel_checks_before_and_after_evolution': successful_jump_channels,
    'maximum_rate_identity_error': max_rate_error,
    'maximum_number_preservation_error': max_number_error,
    'internal_oscillation_times_checked': len(spin_errors),
    'maximum_internal_oscillation_error': max(spin_errors),
    'four_mode_rates_divided_by_r': [str(rate) for rate in four_mode_rates],
    'four_mode_conditional_mean_waiting_times_times_r': [str(value) for value in four_mode_means],
    'four_mode_consecutive_mean_waiting_ratios': [str(value) for value in four_mode_mean_ratios],
    'checks_passed': True,
}
target = Path(__file__).resolve().parents[2] / 'results' / 'audits' / 'response-structure-audit.json'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'checks_passed': True, 'exact_symmetry_cases': len(symmetry_cases), 'rotated_states': rotated_states, 'post_first_sector_states': states_checked, 'output': target.relative_to(Path(__file__).resolve().parents[2]).as_posix()}))

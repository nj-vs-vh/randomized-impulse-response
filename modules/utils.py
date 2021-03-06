import numpy as np
import timeit
from functools import wraps
from numba import njit
from scipy.special import gamma
from math import erf

from typing import Any
from nptyping import NDArray
from numbers import Real


rng = np.random.default_rng()


def generate_poissonian_ns(n_mean: Real, count: int) -> NDArray[Real]:
    return rng.poisson(n_mean, count)


def slice_edge_effects(mat: NDArray[(Any,), float], L: int, N: int, axis: int = 0):
    """See \\ref{sec:edge-effects}"""
    # t (one-based) in L+1, ..., N => index (zero-based) in L, ..., N-1
    return np.take(mat, range(L, N), axis=axis)


def timer(args_formatter=None):
    if args_formatter is None:
        args_formatter = (
            lambda *args, **kwargs: (
                ", ".join(
                    [
                        s
                        for s in [", ".join(str(a) for a in args), ", ".join(f"{k}={w}" for k, w in kwargs.items())]
                        if s
                    ]
                )
            )
        )  # noqa

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = timeit.default_timer()
            result = func(*args, **kwargs)
            elapsed = timeit.default_timer() - start_time
            print(f'{func.__name__}({args_formatter(*args, **kwargs)}) took {elapsed} seconds to complete.')
            return result

        return wrapper

    return decorator


def enforce_bounds(logprob, n_vec_center, upper_bound_factor: int = 100):
    n_vec_min = np.zeros_like(n_vec_center, dtype=float)
    n_vec_max = n_vec_center * upper_bound_factor

    @wraps(logprob)
    def bounded_logprob(n_vec):
        if np.any(np.logical_or(n_vec < n_vec_min, n_vec > n_vec_max)):
            return - np.inf
        return logprob(n_vec)

    return bounded_logprob


@njit
def norm_cdf(x, mu, sigma):
    cdf = np.zeros_like(x)
    for i, x_i in enumerate(x):
        cdf[i] = 0.5 * (1 + erf((x_i - mu) / (sigma * 1.41421356237)))
    return cdf


@njit
def poisson_pmf(k: NDArray[(Any), float], lmb: float):
    k_flattened = k.reshape(k.size)
    k_factorial = np.zeros_like(k_flattened)
    for i, k_ in enumerate(k_flattened):
        k_factorial[i] = gamma(k_ + 1) if k_ > 0 else np.inf
    return np.exp(-lmb) * (np.power(lmb, k)) / k_factorial.reshape(k.shape)


# print(poisson_pmf(np.array([1, -10000], dtype=float), 4))


def angle_between(theta1, phi1, theta2, phi2):
    """Angle between unit vectors with corresponding theta and phi angles"""
    chord = np.sqrt(
        (np.cos(theta1) - np.cos(theta2)) ** 2  # delta Z
        + (np.sin(theta1) * np.sin(phi1) - np.sin(theta2) * np.sin(phi2)) ** 2  # delta Y
        + (np.sin(theta1) * np.cos(phi1) - np.sin(theta2) * np.cos(phi2)) ** 2  # delta X
    )
    return 2 * np.arcsin(chord / 2)


def apply_mask(*numpy_arrays, mask=NDArray[(Any,), bool]):
    """mask is True -> element is kept, not masked (slicing convention but I like to call it masking, sorry)"""
    return tuple(arr[mask] for arr in numpy_arrays)


def concat_vectors_as_cols(v1: NDArray, v2: NDArray) -> NDArray:
    n = v1.size
    return np.concatenate((v1.reshape(n, 1), v2.reshape(n, 1)), axis=1)

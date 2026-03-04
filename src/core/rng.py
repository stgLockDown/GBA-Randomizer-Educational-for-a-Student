"""
Deterministic RNG engine for reproducible randomization.
Uses Python's random module with explicit seed control.
"""
import random
import hashlib
from typing import List, TypeVar, Optional

T = TypeVar('T')


class RNGEngine:
    """Deterministic random number generator with seed tracking."""

    def __init__(self, seed: Optional[str] = None):
        self._rng = random.Random()
        self._seed_str = seed or self.generate_seed()
        self._numeric_seed = self._string_to_numeric_seed(self._seed_str)
        self._rng.seed(self._numeric_seed)
        self._call_count = 0

    @staticmethod
    def generate_seed() -> str:
        """Generate a random seed string."""
        import time
        raw = f"{time.time_ns()}-{random.getrandbits(64)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12].upper()

    @staticmethod
    def _string_to_numeric_seed(seed_str: str) -> int:
        """Convert any string seed to a stable numeric seed."""
        h = hashlib.sha256(seed_str.encode('utf-8')).digest()
        return int.from_bytes(h[:8], 'big')

    @property
    def seed(self) -> str:
        return self._seed_str

    @property
    def call_count(self) -> int:
        return self._call_count

    def randint(self, a: int, b: int) -> int:
        """Return random integer N such that a <= N <= b."""
        self._call_count += 1
        return self._rng.randint(a, b)

    def choice(self, seq: List[T]) -> T:
        """Return a random element from non-empty sequence."""
        self._call_count += 1
        return self._rng.choice(seq)

    def choices_weighted(self, population: List[T], weights: List[float], k: int = 1) -> List[T]:
        """Return k weighted random choices."""
        self._call_count += 1
        return self._rng.choices(population, weights=weights, k=k)

    def shuffle(self, lst: List[T]) -> List[T]:
        """Shuffle list in-place and return it."""
        self._call_count += 1
        self._rng.shuffle(lst)
        return lst

    def sample(self, population: List[T], k: int) -> List[T]:
        """Return k unique random elements from population."""
        self._call_count += 1
        return self._rng.sample(population, k)

    def random_float(self) -> float:
        """Return random float in [0.0, 1.0)."""
        self._call_count += 1
        return self._rng.random()

    def gauss(self, mu: float, sigma: float) -> float:
        """Gaussian distribution."""
        self._call_count += 1
        return self._rng.gauss(mu, sigma)

    def clamp_randint(self, base: int, variance: int, minimum: int = 0, maximum: int = 255) -> int:
        """Random int within ±variance of base, clamped to [minimum, maximum]."""
        low = max(minimum, base - variance)
        high = min(maximum, base + variance)
        if low > high:
            low, high = high, low
        return self.randint(low, high)

    def fork(self, label: str) -> 'RNGEngine':
        """Create a child RNG derived from this seed + a label (for module isolation)."""
        child_seed = f"{self._seed_str}:{label}"
        return RNGEngine(child_seed)

    def get_state(self) -> dict:
        """Serialize RNG state for logging."""
        return {
            "seed": self._seed_str,
            "numeric_seed": self._numeric_seed,
            "call_count": self._call_count,
        }
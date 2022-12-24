from typing import Sequence, TypeVar, Union

T = TypeVar("T")
MaybeSequence = Union[T, Sequence[T]]

try:
    import numpy.typing as npt

    # The numpy typing module was introduced in numpy 1.20

    MaybeArray = Union[T, npt.NDArray[T]]
    MaybeArrayLike = Union[T, Sequence[T], npt.NDArray[T]]
except ImportError:
    import numpy as np

    # This fallback for numpy < 1.20

    MaybeArray = Union[T, np.ndarray]
    MaybeArrayLike = Union[T, Sequence[T], np.ndarray]

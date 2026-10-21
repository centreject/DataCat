import logging
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger(__name__)
T = TypeVar("T")


def load_cached_first(load: Callable[..., T]) -> T:
    """Load from the local Hugging Face cache without any network call; download only if missing.

    Without this, every startup asks the Hub whether a newer revision exists — slow, and a
    failure point at a demo with bad Wi-Fi. `load` must accept `local_files_only`.
    """
    try:
        return load(local_files_only=True)
    except (OSError, ValueError):  # missing cache: huggingface_hub/transformers raise these
        log.info("model not in local cache; downloading")
        return load(local_files_only=False)

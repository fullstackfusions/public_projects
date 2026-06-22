class TokenBucket:
    def __init__(self, rate: float, capacity: float) -> None:
        raise NotImplementedError

    def acquire(self, tokens: float = 1.0) -> bool:
        raise NotImplementedError

from typing import Any, Awaitable, Callable


class Redeem:
    title: str
    description: str
    cost: int
    enabled: bool

    handler: Callable[[], Awaitable[Any]]

    def __init__(self, title: str, description: str, cost: int, enabled: bool,
                 handler: Callable) -> None:
        self.title = title
        self.description = description
        self.cost = cost
        self.enabled = enabled

        self.handler = handler

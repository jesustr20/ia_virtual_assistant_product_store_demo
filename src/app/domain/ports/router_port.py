from abc import ABC, abstractmethod
from ..entities.route_decision import RouteDecision

class RouterPort(ABC):

    @abstractmethod
    def classify(self, message: str) -> RouteDecision:
        pass
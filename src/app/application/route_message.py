from ..domain.ports.router_port import RouterPort

class RouteMessageService:
    def __init__(self, router: RouterPort):
        self.router = router

    def route(self, message: str) -> str:
        decision = self.router.classify(message)
        return decision.category
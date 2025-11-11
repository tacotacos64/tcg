class Controller:
    def team_name(self) -> str:
        raise NotImplementedError

    def update(self, info) -> tuple[int, int, int]:
        raise NotImplementedError


class Human(Controller):
    def team_name(self) -> str:
        return "Human"

    def update(self, info) -> tuple[int, int, int]:
        # Implement human input logic here
        return 0, 0, 0

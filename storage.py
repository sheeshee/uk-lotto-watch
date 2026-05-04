from dataclasses import dataclass
from abc import ABC, abstractmethod
from fetch import Game
import yaml


class AbstractRepository(ABC):
    @abstractmethod
    def add(self, label: str, game: Game) -> None:
        """Add a game to the repository."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    @abstractmethod
    def get_all(self) -> dict[str, Game]:
        """List all games in the repository."""
        raise NotImplementedError("This method should be implemented by subclasses.")


@dataclass
class GamesRepository(AbstractRepository):
    filename: str

    def add(self, label: str, game: Game) -> None:
        """Add a game to the repository."""
        games = self.get_all()
        games[label] = game
        with open(self.filename, "w") as file:
            yaml.dump(
                {label: game.as_dict() for label, game in games.items()},
                file,
                default_flow_style=False,
            )

    def get_all(self) -> dict[str, Game]:
        """List all games in the repository."""
        try:
            with open(self.filename, "r") as file:
                games_data = yaml.safe_load(file)
                if games_data is None:
                    return {}
                return {label: Game(**game) for label, game in games_data.items()}
        except FileNotFoundError:
            return {}
        except yaml.YAMLError as e:
            print(f"Error reading YAML file: {e}")
            return {}

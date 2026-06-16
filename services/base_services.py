from abc import ABC, abstractmethod


class BaseServices(ABC):

    @abstractmethod
    def fetch_service(self, url: str, depth_data: bool = False) -> dict | None:
        pass
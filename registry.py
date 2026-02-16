import importlib.util
import pathlib
from typing import Dict, Type
from basetypes import *

class ProviderRegistry:
    def __init__(self, folder_path: str, base_class: Type):
        self.folder = pathlib.Path(folder_path)
        self.base_class = base_class
        self._instances = {}
        self._available_providers = self._scan_folder()

    def _scan_folder(self) -> Dict[str, pathlib.Path]:
        return {
            f.stem: f for f in self.folder.glob("*.py")
            if f.stem != "__init__"
        }

    def _load_provider(self, name: str):
        if name not in self._available_providers:
            raise AttributeError(f"Provider '{name}' not found in {self.folder}")

        file_path = self._available_providers[name]
        spec = importlib.util.spec_from_file_location(name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                    issubclass(attr, self.base_class) and
                    attr is not self.base_class):
                return attr()

        raise TypeError(f"No valid {self.base_class.__name__} found in {file_path}")

    def __getattr__(self, name: str) -> NotificationProvider:
        if name not in self._instances:
            self._instances[name] = self._load_provider(name)
        return self._instances[name]
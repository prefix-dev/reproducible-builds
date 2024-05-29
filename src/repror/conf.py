from typing import Self
import yaml


def load_config(config_path: str = "config.yaml"):
    with open(config_path, "r", encoding="utf8") as file:
        config = yaml.safe_load(file)
    return config

def save_config(data, config_path: str = "config.yaml"):
    with open(config_path, "w", encoding="utf8") as file:
        yaml.safe_dump(data, file)



class RecipeConfig:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def load_recipe(recipe_file) -> Self:
        with open(recipe_file, "r", encoding="utf8") as file:
            recipe = yaml.safe_load(file)
        return RecipeConfig(recipe)

    @property
    def name(self) -> str:
        if "name" in self.config.get("context", {}):
            return self.config["context"]["name"]

        return self.config["package"]["name"]

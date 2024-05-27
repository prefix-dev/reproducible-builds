from typing import Self
import yaml


def load_config(config_path: str = "config.yaml"):
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config


class RecipeConfig:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def load_recipe(recipe_file) -> Self:
        with open(recipe_file, "r") as file:
            recipe = yaml.safe_load(file)
        return RecipeConfig(recipe)

    @property
    def name(self) -> str:
        if "name" in self.config.get("context", {}):
            return self.config["context"]["name"]

        return self.config["package"]["name"]

import locale
import json
import os


def load_language_list(language):
    with open(f"./locale/{language}.json", "r", encoding="utf-8") as f:
        language_list = json.load(f)
    return language_list


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        else:
            cls._instances[cls].__init__(*args, **kwargs)
        return cls._instances[cls]


class I18nUtil(metaclass=Singleton):
    def __init__(self, language=None):
        if language is None:
            language = "auto"
        if language == "auto":
            language = locale.getlocale()[0]
        if not os.path.exists(f"./locale/{language}.json"):
            language = "en_US"
        self.language = language
        print("Use Language:", language)
        self.language_map = load_language_list(language)

    def __call__(self, key):
        return self.language_map[key]

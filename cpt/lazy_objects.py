import functools
import os

from conans import __version__ as client_version
from conans.model.ref import ConanFileReference
from conans.model.version import Version


class LazyObject(object):
    def __init__(self, api, cwd, recipe_name):
        self._api = api
        self._cwd = cwd
        self._recipe_name = recipe_name

    @property
    def recipe_path(self):
        return os.path.join(self._cwd, self._recipe_name)

    def load_recipe(self):
        path = self.recipe_path
        if not os.path.exists(path):
            return

        if Version(client_version) < Version("1.7.0"):
            from conans.client.loader_parse import load_conanfile_class
            return load_conanfile_class(path)
        else:
            return self._api._loader.load_class(path)


class LazyPackageOption(LazyObject):
    def __init__(self, name, api, cwd, recipe_name, reference):
        super(LazyPackageOption, self).__init__(api, cwd, recipe_name)
        self._name = name
        self._reference = reference
        self._loaded = False

    def __str__(self):
        if not self._loaded:
            self._load()
        return self._name

    def _load(self):
        recipe = self.load_recipe()
        if recipe and hasattr(recipe, "options") and recipe.options \
           and self._name in recipe.options:
            self._name = "%s:shared" % self._reference.name
        else:
            self._name = ""
        self._loaded = True


class LazyConanFileReference(LazyObject):
    def __init__(self, api, cwd, recipe_name, reference_text, username, channel):
        super(LazyConanFileReference, self).__init__(api, cwd, recipe_name)
        self._reference_text = reference_text
        self._username = username
        self._channel = channel
        self._reference = None

    def __getattr__(self, name):
        if self._reference is None:
            self._load()

        return getattr(self._reference, name)

    def __iter__(self):
        return self.__getattr__("__iter__")()

    def _load(self):
        if self._reference_text:
            if "@" in self._reference_text:
                reference = ConanFileReference.loads(self._reference_text)
            else:
                name, version = self._reference_text.split("/")
                reference = ConanFileReference(name, version, self._username, self._channel)
        else:
            recipe = self.load_recipe()
            if recipe is None:
                raise Exception("Conanfile not found, specify a 'reference' "
                                "parameter with name and version")

            name, version = recipe.name, recipe.version
            if name and version:
                reference = ConanFileReference(name, version, self._username, self._channel)
            else:
                raise Exception("Specify a CONAN_REFERENCE or name and version "
                                "fields in the recipe")

        self._reference = reference

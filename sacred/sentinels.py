
class Sentinel(object):
    __slots__ = ('name', 'module', '__doc__')
    _existing_instances = {}

    def __new__(cls, name, module=None, docstring=None):
        qualname = cls._qualname(name, module)
        existing_instance = cls._existing_instances.get(qualname)
        if existing_instance is not None:
            return existing_instance
        instance = super(Sentinel, cls).__new__(cls)
        object.__setattr__(instance, 'name', name)
        object.__setattr__(instance, 'module', module)
        object.__setattr__(instance, '__doc__', docstring)
        Sentinel._existing_instances[qualname] = instance
        return instance

    def __setattr__(self, name, value):
        if name not in Sentinel.__slots__:
            raise AttributeError("{} has no attribute {}".format(self, name))
        else:
            raise AttributeError("{} is immutable".format(self, name))

    @staticmethod
    def _qualname(name, module):
        if module is None:
            return name
        else:
            return "{}.{}".format(module, name)

    def __repr__(self):
        return "<{}>".format(self._qualname(self.name, self.module))

    def __getnewargs__(self):
        return self.name, self.module, self.__doc__

    def __setstate__(self, state):
        return self


NotSet = Sentinel('NotSet', 'sacred',
                  'Indicates that an optional value has not been set.')

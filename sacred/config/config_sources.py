class ConfigSource:
    @staticmethod
    def get_string(config_source, ):
        if isinstance(config_source, dict):
            def _get_sources(d):
                sources = set()
                if isinstance(d, dict):
                    for v in config_source.values():
                        sources.update(_get_sources(v))
                else:
                    sources.add(d)
                return sources
            sources = _get_sources(config_source)
            # '\n'.join([s.get_source_string_for_config()])
        else:
            return config_source.get_source_string_for_config

    def get_source_string_for_config(self, config=None):
        raise NotImplementedError()


class FileConfigSource(ConfigSource):
    def __init__(self, file, line=None) -> None:
        super().__init__()
        self.file = file
        self.line = line

    def get_source_string_for_config(self, config=None):
        if self.line is None:
            return '"{}"'.format(self.file)
        else:
            return '"{}:{}"'.format(self.file, self.line)


class ConfigScopeConfigSource(ConfigSource):
    def __init__(self, config_scope) -> None:
        super().__init__()
        self.config_scope = config_scope

    def get_source_string_for_config(self, config=None):
        return '"{}:{}"'.format(self.config_scope._file_name,
                              self.config_scope._line_offset)


class NamedConfigScopeConfigSource(ConfigScopeConfigSource):
    def __init__(self, config_name, config_scope):
        super().__init__(config_scope)
        self.config_name = config_name

    def get_source_string_for_config(self, config=None):
        file = super().get_source_string_for_config(config)
        return 'Named Config "{}" at {}'.format(self.config_name, file)


class CommandLineConfigSource(ConfigSource):

    def __init__(self, config_updates) -> None:
        super().__init__()
        self.config_updates = config_updates

    def get_source_string_for_config(self, config=None):
        if config is not None and config in self.config_updates:
            return 'command line config "{}={}"'.format(config,
                                                      self.config_updates[
                                                          config])
        else:
            return 'command line config with "{}"'.format(' '.join(
                '{}={}'.format(k, v) for k, v in self.config_updates.items()))


class ConfigDictConfigSource(ConfigSource):
    def __init__(self, config_dict) -> None:
        self.config_dict = config_dict

    def get_source_string_for_config(self, config=None):
        return 'Set in config dict (unknown source)'



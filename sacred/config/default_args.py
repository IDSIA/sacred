from sphinx.ext.napoleon.docstring import GoogleDocstring
from sphinx.ext.napoleon import Config
import inspect


class Parameter:
    def __init__(self, value, description=None, type_=None):
        self.value = value
        self.description = description
        self.type_ = type_


class GoogleDocGetDesciption(GoogleDocstring):
    def __init__(self, *args, **kwargs):
        self.argument_descriptions = None
        super().__init__(*args, **kwargs)

    def _parse_parameters_section(self, section):
        fields = self._consume_fields()
        self.argument_descriptions = fields.copy()
        if self._config.napoleon_use_param:
            return self._format_docutils_params(fields)
        else:
            from sphinx.locale import _

            return self._format_fields(_("Parameters"), fields)


def get_default_args_description(func):
    config = Config(napoleon_use_param=True, napoleon_use_rtype=True)

    parsed = GoogleDocGetDesciption(
        remove_indentation(func.__doc__), obj=func, config=config
    )
    return parsed.argument_descriptions


def remove_indentation(docstring):
    processed_docstring = docstring.splitlines()
    for i in range(1, len(processed_docstring)):
        processed_docstring[i] = processed_docstring[i][4:]
    return processed_docstring


def get_default_args_values(func):
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


def get_default_args(func):
    default_args_values = get_default_args_values(func)
    default_args_description = get_default_args_description(func)

    default_args = {}
    for name, type_, description in default_args_description:
        default_value = default_args_values[name]
        description = "\n".join(description).strip()
        default_args[name] = Parameter(default_value, description, type_)
    return default_args

ROLE_OPTIONS = ["input", "output"]


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _clean_examples(raw):
    if raw is None:
        return []
    items = []
    for line in str(raw).replace("\r", "\n").split("\n"):
        cleaned = line.strip()
        if cleaned:
            items.append(cleaned)
    return items


def _set_if(schema, key, value):
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    schema[key] = value


def _numeric_constraints(gt, ge, lt, le, multiple_of):
    constraints = {}
    if gt is not None:
        constraints["exclusiveMinimum"] = gt
    if ge is not None:
        constraints["minimum"] = ge
    if lt is not None:
        constraints["exclusiveMaximum"] = lt
    if le is not None:
        constraints["maximum"] = le
    if multiple_of not in (None, 0, 0.0):
        constraints["multipleOf"] = multiple_of
    return constraints


class BaseSchemaParameterNode:
    CATEGORY = "inout/schema"
    FUNCTION = "execute"

    json_type = "string"
    python_type = "str"
    default_value = None
    output_type = "STRING"
    type_label = "text"

    @classmethod
    def base_required_inputs(cls):
        return {
            "name": ("STRING", {"default": "parameter_name"}),
            "io_kind": (ROLE_OPTIONS, {"default": "input"}),
            "description": ("STRING", {"default": "", "multiline": True}),
            "required": ("BOOLEAN", {"default": True}),
        }

    @classmethod
    def type_required_inputs(cls):
        return {}

    @classmethod
    def optional_inputs(cls):
        return {
            "value_in": (cls.output_type, {"forceInput": True}),
        }

    @classmethod
    def INPUT_TYPES(cls):
        required = cls.base_required_inputs()
        required.update(cls.type_required_inputs())
        return {
            "required": required,
            "optional": cls.optional_inputs(),
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    RETURN_TYPES = ()
    RETURN_NAMES = ("value", "field")

    def _resolve_value(self, value_in, fallback):
        return fallback if value_in is None else value_in

    def _field_schema(self, *, name, io_kind, description, required):
        schema = {
            "name": _clean_text(name),
            "io": io_kind,
            "type": self.json_type,
            "python_type": self.python_type,
            "required": bool(required),
            "description": str(description),
            "node_type": self.__class__.__name__,
        }
        return schema

    def execute(self, **kwargs):
        raise NotImplementedError


class SchemaStringParameter(BaseSchemaParameterNode):
    output_type = "STRING"
    json_type = "string"
    python_type = "str"
    default_value = ""
    type_label = "string"
    RETURN_TYPES = ("STRING", "SCHEMA_FIELD")

    @classmethod
    def type_required_inputs(cls):
        return {
            "default": ("STRING", {"default": "", "multiline": True}),
            "multiline": ("BOOLEAN", {"default": False}),
            "placeholder": ("STRING", {"default": ""}),
            "min_length": ("INT", {"default": 0, "min": 0, "max": 65535, "step": 1}),
            "max_length": ("INT", {"default": 0, "min": 0, "max": 65535, "step": 1}),
            "pattern": ("STRING", {"default": ""}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        default,
        multiline,
        placeholder,
        min_length,
        max_length,
        pattern,
        value_in=None,
    ):
        value = self._resolve_value(value_in, default)
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = default
        if min_length > 0:
            field["minLength"] = min_length
        if max_length > 0:
            field["maxLength"] = max_length
        _set_if(field, "pattern", pattern)
        field["ui"] = {
            "multiline": bool(multiline),
            "placeholder": placeholder,
        }
        return (value, field)


class SchemaIntegerParameter(BaseSchemaParameterNode):
    output_type = "INT"
    json_type = "integer"
    python_type = "int"
    default_value = 0
    type_label = "integer"
    RETURN_TYPES = ("INT", "SCHEMA_FIELD")

    @classmethod
    def type_required_inputs(cls):
        return {
            "default": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647, "step": 1}),
            "ge": ("INT", {"default": -2147483648, "min": -2147483648, "max": 2147483647, "step": 1}),
            "gt": ("INT", {"default": -2147483648, "min": -2147483648, "max": 2147483647, "step": 1}),
            "le": ("INT", {"default": 2147483647, "min": -2147483648, "max": 2147483647, "step": 1}),
            "lt": ("INT", {"default": 2147483647, "min": -2147483648, "max": 2147483647, "step": 1}),
            "multiple_of": ("INT", {"default": 0, "min": 0, "max": 2147483647, "step": 1}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        default,
        ge,
        gt,
        le,
        lt,
        multiple_of,
        value_in=None,
    ):
        value = int(self._resolve_value(value_in, default))
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = int(default)
        field.update(
            _numeric_constraints(
                None if gt == -2147483648 else int(gt),
                None if ge == -2147483648 else int(ge),
                None if lt == 2147483647 else int(lt),
                None if le == 2147483647 else int(le),
                int(multiple_of),
            )
        )
        return (value, field)


class SchemaFloatParameter(BaseSchemaParameterNode):
    output_type = "FLOAT"
    json_type = "number"
    python_type = "float"
    default_value = 0.0
    type_label = "float"
    RETURN_TYPES = ("FLOAT", "SCHEMA_FIELD")

    @classmethod
    def type_required_inputs(cls):
        return {
            "default": ("FLOAT", {"default": 0.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "ge": ("FLOAT", {"default": -1000000.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "gt": ("FLOAT", {"default": -1000000.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "le": ("FLOAT", {"default": 1000000.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "lt": ("FLOAT", {"default": 1000000.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "multiple_of": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1000000.0, "step": 0.01}),
            "round_to": ("INT", {"default": 0, "min": 0, "max": 10, "step": 1}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        default,
        ge,
        gt,
        le,
        lt,
        multiple_of,
        round_to,
        value_in=None,
    ):
        value = float(self._resolve_value(value_in, default))
        if round_to > 0:
            value = round(value, round_to)
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = float(default)
        field.update(
            _numeric_constraints(
                None if gt == -1000000.0 else float(gt),
                None if ge == -1000000.0 else float(ge),
                None if lt == 1000000.0 else float(lt),
                None if le == 1000000.0 else float(le),
                float(multiple_of),
            )
        )
        if round_to > 0:
            field["precision"] = int(round_to)
        return (value, field)


class SchemaBooleanParameter(BaseSchemaParameterNode):
    output_type = "BOOLEAN"
    json_type = "boolean"
    python_type = "bool"
    default_value = False
    type_label = "boolean"
    RETURN_TYPES = ("BOOLEAN", "SCHEMA_FIELD")

    @classmethod
    def type_required_inputs(cls):
        return {
            "default": ("BOOLEAN", {"default": False}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        default,
        value_in=None,
    ):
        value = bool(self._resolve_value(value_in, default))
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = bool(default)
        return (value, field)


class SchemaEnumParameter(BaseSchemaParameterNode):
    output_type = "STRING"
    json_type = "string"
    python_type = "str"
    default_value = ""
    type_label = "enum"
    RETURN_TYPES = ("STRING", "SCHEMA_FIELD")

    @classmethod
    def type_required_inputs(cls):
        return {
            "options": ("STRING", {"default": "option_a\noption_b", "multiline": True}),
            "default": ("STRING", {"default": "option_a"}),
            "allow_custom_value": ("BOOLEAN", {"default": False}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        options,
        default,
        allow_custom_value,
        value_in=None,
    ):
        option_list = _clean_examples(options)
        value = self._resolve_value(value_in, default)
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = str(default)
        field["enum"] = option_list
        if allow_custom_value:
            field["allow_custom_value"] = True
        return (str(value), field)


class BaseSchemaMediaParameter(BaseSchemaParameterNode):
    RETURN_TYPES = ()

    @classmethod
    def type_required_inputs(cls):
        return {
            "accepted_formats": ("STRING", {"default": "", "multiline": True}),
        }

    @classmethod
    def optional_inputs(cls):
        return {
            "value_in": (cls.output_type, {"forceInput": True}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        accepted_formats,
        value_in=None,
    ):
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        formats = _clean_examples(accepted_formats)
        if formats:
            field["accepted_formats"] = formats
        field["expects_connection"] = True
        return (value_in, field)


class SchemaImageParameter(BaseSchemaMediaParameter):
    output_type = "IMAGE"
    json_type = "image"
    python_type = "IMAGE"
    type_label = "image"
    RETURN_TYPES = ("IMAGE", "SCHEMA_FIELD")


class SchemaVideoParameter(BaseSchemaMediaParameter):
    output_type = "VIDEO"
    json_type = "video"
    python_type = "VIDEO"
    type_label = "video"
    RETURN_TYPES = ("VIDEO", "SCHEMA_FIELD")


class SchemaAudioParameter(BaseSchemaMediaParameter):
    output_type = "AUDIO"
    json_type = "audio"
    python_type = "AUDIO"
    type_label = "audio"
    RETURN_TYPES = ("AUDIO", "SCHEMA_FIELD")


SCHEMA_CLASS_MAPPINGS = {
    "SchemaAudioParameter": SchemaAudioParameter,
    "SchemaStringParameter": SchemaStringParameter,
    "SchemaIntegerParameter": SchemaIntegerParameter,
    "SchemaFloatParameter": SchemaFloatParameter,
    "SchemaBooleanParameter": SchemaBooleanParameter,
    "SchemaEnumParameter": SchemaEnumParameter,
    "SchemaImageParameter": SchemaImageParameter,
    "SchemaVideoParameter": SchemaVideoParameter,
}

SCHEMA_DISPLAY_NAME_MAPPINGS = {
    "SchemaAudioParameter": "Schema Audio Parameter",
    "SchemaStringParameter": "Schema String Parameter",
    "SchemaIntegerParameter": "Schema Integer Parameter",
    "SchemaFloatParameter": "Schema Float Parameter",
    "SchemaBooleanParameter": "Schema Boolean Parameter",
    "SchemaEnumParameter": "Schema Enum Parameter",
    "SchemaImageParameter": "Schema Image Parameter",
    "SchemaVideoParameter": "Schema Video Parameter",
}

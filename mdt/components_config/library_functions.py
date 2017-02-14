import inspect
import os
from copy import deepcopy

import six

from mdt.components_loader import ParametersLoader, ComponentConfigMeta, ComponentConfig, ComponentBuilder, \
    method_binding_meta
from mot.cl_data_type import CLDataType
from mot.model_building.cl_functions.base import LibraryFunction, SimpleLibraryFunction
from mot.model_building.cl_functions.parameters import LibraryParameter

__author__ = 'Robbert Harms'
__date__ = "2017-02-14"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


def _get_parameters_list(parameter_list):
    """Convert all the parameters in the given parameter list to actual parameter objects.

    This will load all the parameters as :class:`~mot.model_building.cl_functions.parameters.LibraryParameter`.

    Args:
        parameter_list (list): a list containing a mix of either parameter objects or strings. If it is a parameter
            we add a copy of it to the return list. If it is a string we will autoload it.

    Returns:
        list: the list of actual parameter objects
    """
    parameters = []
    for item in parameter_list:
        if isinstance(item, six.string_types):
            LibraryParameter(CLDataType.from_string('mot_float_type'), item)
        else:
            parameters.append(deepcopy(item))
    return parameters


def _construct_cl_function_definition(return_type, cl_function_name, parameters):
    """Create the CL function definition for a compartment function.

    This will construct something like (for the NeumannCylPerpPGSESum model):

    .. code-block:: c

        mot_float_type NeumannCylPerpPGSESum(const mot_float_type Delta,
                                             const mot_float_type delta,
                                             const mot_float_type d,
                                             const mot_float_type R)

    Args:
        return_type (str): the return type
        cl_function_name (str): the name of the function
        parameters (list of CLFunctionParameter): the list of function parameters we use for the arguments

    Returns:
        str: the function definition (only the signature).
    """
    def parameter_str(parameter):
        s = parameter.data_type.cl_type

        if parameter.data_type.pre_data_type_type_qualifiers:
            for qualifier in parameter.data_type.pre_data_type_type_qualifiers:
                s = qualifier + ' ' + s

        if parameter.data_type.address_space_qualifier:
            s = parameter.data_type.address_space_qualifier + ' ' + s

        if parameter.data_type.post_data_type_type_qualifier:
            s += ' ' + parameter.data_type.post_data_type_type_qualifier

        s += ' ' + parameter.name

        return s

    parameters_str = ',\n'.join(parameter_str(parameter) for parameter in parameters)
    return '{return_type} {cl_function_name}({parameters})'.format(return_type=return_type,
                                                                   cl_function_name=cl_function_name,
                                                                   parameters=parameters_str)


class LibraryFunctionConfigMeta(ComponentConfigMeta):

    def __new__(mcs, name, bases, attributes):
        """Extends the default meta class with extra functionality for the library functions.

        This adds the cl_function_name if it is not defined, and creates the correct cl_code and cl_header.
        """
        result = super(LibraryFunctionConfigMeta, mcs).__new__(mcs, name, bases, attributes)

        if 'cl_function_name' not in attributes:
            result.cl_function_name = '{}'.format(name)

        # to prevent the base from loading the initial meta class.
        if any(isinstance(base, LibraryFunctionConfigMeta) for base in bases):
            result.cl_code = mcs._get_cl_code(result, bases, attributes)
            result.cl_header = mcs._get_cl_header(result, bases, attributes)

        return result

    @classmethod
    def _get_cl_code(mcs, result, bases, attributes):
        if 'cl_code' in attributes and attributes['cl_code'] is not None:
            s = _construct_cl_function_definition(
                'mot_float_type', result.cl_function_name, _get_parameters_list(result.parameter_list))
            s += '{\n' + attributes['cl_code'] + '\n}'
            return s

        module_path = os.path.abspath(inspect.getfile(result))
        path = os.path.join(os.path.dirname(module_path), os.path.splitext(os.path.basename(module_path))[0]) + '.cl'
        if os.path.isfile(path):
            with open(path, 'r') as f:
                return f.read()

        for base in bases:
            if hasattr(base, 'cl_code') and base.cl_code is not None:
                return base.cl_code

    @classmethod
    def _get_cl_header(mcs, result, bases, attributes):
        if 'cl_header' in attributes and attributes['cl_header'] is not None:
            return attributes['cl_header']

        module_path = os.path.abspath(inspect.getfile(result))
        path = os.path.join(os.path.dirname(module_path), os.path.splitext(os.path.basename(module_path))[0]) + '.h'
        if os.path.isfile(path):
            with open(path, 'r') as f:
                return f.read()

        for base in bases:
            if hasattr(base, 'cl_header') and base.cl_code is not None:
                return base.cl_header

        return _construct_cl_function_definition('mot_float_type', result.cl_function_name,
                                                 _get_parameters_list(result.parameter_list)) + ';'


class LibraryFunctionConfig(six.with_metaclass(LibraryFunctionConfigMeta, ComponentConfig)):
    """The library function config to inherit from.

    These configs are loaded on the fly by the LibraryFunctionsBuilder.

    All methods you define are automatically bound to the LibraryFunction. Also, to do extra
    initialization you can define a method ``init``. This method is called after object construction to allow
    for additional initialization and is is not added to the final object.

    Attributes:
        name (str): the name of the model, defaults to the class name
        description (str): model description
        cl_function_name (str): the name of the function in the CL kernel
        return_type (str): the return type of the function, defaults to ``mot_float_type``
        parameter_list (list): the list of parameters to use. If a parameter is a string we will
            use it automatically, if not it is supposed to be a LibraryParameter
            instance that we append directly.
        cl_header (CLHeaderDefinition): the CL header definition to use. Defaults to CLHeaderFromTemplate.
        cl_code (CLCodeDefinition): the CL code definition to use. Defaults to CLCodeFromAdjacentFile.
        dependency_list (list): the list of functions this function depends on, can contain string which will be
            resolved as library functions.
    """
    name = ''
    description = ''
    cl_function_name = None
    return_type = 'mot_float_type'
    parameter_list = []
    cl_header = None
    cl_code = None
    dependency_list = []


class LibraryFunctionBuildingBase(SimpleLibraryFunction):
    """Use this class in super calls if you want to overwrite methods in the inherited compartment configs.

    In python2 super needs a type to be able to do its work. This is the type you can give it to allow
    it to do its work.
    """


class LibraryFunctionsBuilder(ComponentBuilder):

    def create_class(self, template):
        """Creates classes with as base class LibraryFunctionsBase

        Args:
            template (LibraryFunctionConfig): the library config template to use for creating
                the class with the right init settings.
        """
        class AutoCreatedLibraryFunction(method_binding_meta(template, LibraryFunctionBuildingBase)):

            def __init__(self, *args):
                new_args = [template.return_type,
                            template.cl_function_name,
                            _get_parameters_list(template.parameter_list),
                            _resolve_dependencies(template.dependency_list),
                            template.cl_header,
                            template.cl_code,
                            ]

                for ind, already_set_arg in enumerate(args):
                    new_args[ind] = already_set_arg

                super(AutoCreatedLibraryFunction, self).__init__(*new_args)

                if hasattr(template, 'init'):
                    template.init(self)

        return AutoCreatedLibraryFunction


def _resolve_dependencies(dependency_list):
    """Resolve the dependency list such that the result contains all functions.

    Args:
        dependency_list (list): the list of dependencies as given by the user. Elements can either include actual
            instances of :class:`~mot.model_building.cl_functions.base.CLFunction` or strings with the name of the
            component to auto-load.

    Returns:
        list: a new list with the string elements resolved
            as :class:`~mot.model_building.cl_functions.base.LibraryFunction`.
    """
    from mdt.components_loader import LibraryFunctionsLoader

    lib_loader = LibraryFunctionsLoader()
    result = []
    for dependency in dependency_list:
        if isinstance(dependency, six.string_types):
            result.append(lib_loader.load(dependency))
        else:
            result.append(dependency)

    return result

import six
import mdt
from mdt.models.base import DMRIOptimizable
from mdt.utils import simple_parameter_init, condense_protocol_problems

__author__ = 'Robbert Harms'
__date__ = "2015-04-24"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


class DMRICascadeModelInterface(DMRIOptimizable):

    def __init__(self):
        """The interface to cascade models.

        A cascade model is a model consisting of multi-compartment models or other cascade models. The idea is that
        it contains a number of models that are to be ran one after each other and with which the output results of
        the previous fit_model(s) are used for the next fit_model.
        """
        self._double_precision = False

    @property
    def name(self):
        """Get the name of this cascade model.

        Returns:
            str: The name of this cascade model
        """
        return ''

    @property
    def double_precision(self):
        return self._double_precision

    @double_precision.setter
    def double_precision(self, double_precision):
        self._double_precision = double_precision
        self._set_double_precision(double_precision)

    def has_next(self):
        """Check if this cascade model has a next model.

        Returns:
            boolean: True if there is a next model, false otherwise.
        """

    def get_next(self, output_previous_models):
        """Get the next model in the cascade. This is the only function called by the cascade model optimizer

        This class is supposed to remember which model it gave the optimizer in what order.

        Args:
            output_previous_models (dict): The output of all the previous models. The first level of the
                dict is for the models and is indexed by the model name. The second layer contains all the maps.

        Returns:
            SampleModelInterface: The sample model used for the next fit_model.
        """

    def reset(self):
        """Reset the iteration over the cascade.

        The implementing class should now reset the iteration such that get_next gets the first model again.
        """

    def get_model(self, name):
        """Get one of the models in the cascade by name.

        Args:
            name (str): the name of the model we want to return

        Returns:
            the model we want to have or None if no model found
        """

    def get_model_names(self):
        """Get the names of the models in this cascade in order of execution.

        Returns:
            list of str: the names of the models in this list
        """

    def _set_double_precision(self, double_precision):
        """Set the value double precision for all models in the cascade.

        Args:
            double_precision (boolean): the value to set for all models in the cascade
        """

    def set_problem_data(self, problem_data):
        """Set the problem data in every model in the cascade."""

    def set_gradient_deviations(self, grad_dev):
        """Set the gradient deviations in every model."""


class SimpleCascadeModel(DMRICascadeModelInterface):

    def __init__(self, name, model_list):
        """Create a new cascade model from a given list of models.

        This class adds some standard bookkeeping to make implementing cascade models easier.

        Args:
            name (str): the name of this cascade model
            model_list (list of models): the list of models this cascade consists of
        """
        super(DMRICascadeModelInterface, self).__init__()
        self._name = name
        self._model_list = model_list
        self._iteration_position = 0

    @property
    def name(self):
        return self._name

    def has_next(self):
        return self._iteration_position != len(self._model_list)

    def get_next(self, output_previous_models):
        next_model = self._model_list[self._iteration_position]
        output_previous = {}
        if self._iteration_position > 0:
            output_previous = output_previous_models[self._model_list[self._iteration_position - 1].name]
        self._prepare_model(next_model, output_previous, output_previous_models)
        self._iteration_position += 1
        return next_model

    def reset(self):
        self._iteration_position = 0

    def is_protocol_sufficient(self, protocol=None):
        for model in self._model_list:
            if not model.is_protocol_sufficient(protocol):
                return False
        return True

    def get_protocol_problems(self, protocol=None):
        return condense_protocol_problems([model.get_protocol_problems(protocol) for model in self._model_list])

    def get_required_protocol_names(self):
        protocol_names = []
        for model in self._model_list:
            protocol_names.extend(model.get_required_protocol_names())
        return list(set(protocol_names))

    def get_model(self, name):
        for model in self._model_list:
            if model.name == name:
                return model
        return None

    def get_model_names(self):
        return [model.name for model in self._model_list]

    def set_problem_data(self, problem_data):
        for model in self._model_list:
            model.set_problem_data(problem_data)

    def set_gradient_deviations(self, grad_dev):
        for model in self._model_list:
            model.set_gradient_deviations(grad_dev)

    def _prepare_model(self, model, output_previous, output_all_previous):
        """Prepare the next model with the output of the previous model.

        By default this model initializes all parameter maps to the output of the previous model.

        Args:
            model: The model to prepare
            output_previous (dict): the output of the (direct) previous model.
            output_all_previous (dict): The output of all the previous models. Indexed first by model name, second
                by full parameter name.

        Returns:
            None, preparing should happen in-place.
        """
        if not isinstance(model, DMRICascadeModelInterface):
            simple_parameter_init(model, output_previous)

    def _set_double_precision(self, double_precision):
        for model in self._model_list:
            model.double_precision = double_precision


class CascadeModelBuilder(SimpleCascadeModel):
    """The model builder to inherit from.

    One can use this to create models in a declarative style. Example of such a model definition:

    class BallStick(CascadeModelBuilder):
        name = 'BallStick (Cascade)'
        description = 'Cascade for Ballstick'
        models = ('s0', 'BallStick')
    """
    name = '<default>'
    description = '<default>'
    models = ()
    inits = {}
    fixes = {}

    def __init__(self, *args, **kwargs):
        if len(args) == 2:
            # inheritance is used, the name and model list are already set
            super(CascadeModelBuilder, self).__init__(*args)
        else:
            super(CascadeModelBuilder, self).__init__(self.name, list(map(mdt.get_model, self.models)))

    @classmethod
    def meta_info(cls):
        return {'name': cls.name,
                'description': cls.description}

    def _prepare_model(self, model, output_previous, output_all_previous):
        super(CascadeModelBuilder, self)._prepare_model(model, output_previous, output_all_previous)

        def parse_value(v):
            if isinstance(v, six.string_types):
                return output_previous[v]
            elif hasattr(v, '__call__'):
                return v(output_previous)
            return v

        if model.name in self.inits:
            for item in self.inits[model.name]:
                model.init(item[0], parse_value(item[1]))

        if model.name in self.fixes:
            for item in self.fixes[model.name]:
                model.fix(item[0], parse_value(item[1]))
from mdt.utils import spherical_to_cartesian
from mot.model_building.cl_functions.base import ModelFunction

__author__ = 'Robbert Harms'
__date__ = "2015-12-13"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


class DMRICompartmentModelFunction(ModelFunction):

    def __init__(self, name, cl_function_name, parameter_list, cl_code, dependency_list, prior=None):
        """Create a new dMRI compartment model function.

        Args:
            name (str): the name of this compartment model
            cl_function_name (str): the name of this function in the CL kernel
            parameter_list (list of CLFunctionParameter): the list of the function parameters
            cl_code (str): the code for the function in CL
            dependency_list (list): the list of functions we depend on inside the kernel
            prior (CompartmentPrior): an additional prior on top of the parameter priors.
        """
        super(DMRICompartmentModelFunction, self).__init__(name, cl_function_name, parameter_list,
                                                           dependency_list=dependency_list)
        self._cl_code = cl_code
        self.prior = prior

    def get_cl_code(self):
        return '''
            {dependencies}
            #ifndef {inclusion_guard_name}
            #define {inclusion_guard_name}
            {code}
            #endif // {inclusion_guard_name}
        '''.format(dependencies=self._get_cl_dependency_code(),
                   inclusion_guard_name='DMRICM_' + self.cl_function_name + '_CL',
                   code=self._cl_code)

    def _get_vector_result_maps(self, theta, phi, vector_name='vec0'):
        """Convert spherical coordinates to cartesian vector in 3d

        Args:
            theta (ndarray): the double array with the theta values
            phi (ndarray): the double array with the phi values
            vector_name (str): the name for this vector, the common naming scheme is:
                <model_name>.<vector_name>[_{0,1,2}]

        Returns:
            dict: containing the cartesian vector with the main the fibre direction.
                It returns only the element .vec0
        """
        cartesian = spherical_to_cartesian(theta, phi)
        extra_dict = {'{}'.format(vector_name): cartesian}
        return extra_dict


class CompartmentPrior(object):

    def get_prior_function(self):
        """Return the function that represents this prior.

        Returns:
            string: the cl for the prior of this function.
                This function must accept all the parameters listed by :meth:`get_function_parameters`.
                The signature is:

                .. code-block: c

                    mot_float_type <prior_fname>(mot_float_type p1, mot_float_type p2, ...);
        """
        raise NotImplementedError()

    def get_function_parameters(self):
        """Get a list of the parameters required in this prior (in that order).

        Returns:
            list of str: the list of parameter names this prior requires.
        """
        raise NotImplementedError()

    def get_prior_function_name(self):
        """Get the name of the prior function call.

         This is used by the model builder to construct the call to the prior function.

         Returns:
            str: name of the function
        """
        raise NotImplementedError()


class SimpleCompartmentPrior(CompartmentPrior):

    def __init__(self, body, parameters, function_name):
        """Create a compartment prior from the function body and a list of its parameters.

        Args:
            body (str): the CL code of the function body
            parameters (list of str): the list with parameter names
            function_name (str): the name of this function
        """
        self._body = body
        self._parameters = parameters
        self._function_name = function_name

    def get_prior_function(self):
        return '''
            mot_float_type {function_name}({parameters}){{
                {body}
            }}
        '''.format(function_name=self._function_name,
                   parameters=', '.join('const mot_float_type {}'.format(p) for p in self._parameters),
                   body=self._body)

    def get_prior_function_name(self):
        return self._function_name

    def get_function_parameters(self):
        return self._parameters

import numpy as np

from mdt.components_loader import bind_function
from mdt.models.compartments import CompartmentConfig
from mdt.cl_routines.mapping.dti_measures import DTIMeasures
from mdt.utils import eigen_vectors_from_tensor

__author__ = 'Robbert Harms'
__date__ = "2015-06-21"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


class Tensor(CompartmentConfig):

    parameter_list = ('g', 'b', 'd', 'dperp0', 'dperp1', 'theta', 'phi', 'psi')

    @bind_function
    def get_extra_results_maps(self, results_dict):
        eigen_vectors = eigen_vectors_from_tensor(results_dict[self.name + '.theta'], results_dict[self.name + '.phi'],
                                                  results_dict[self.name + '.psi'])

        eigen_values = Tensor.create_eigen_values_matrix([results_dict[self.name + '.d'],
                                                          results_dict[self.name + '.dperp0'],
                                                          results_dict[self.name + '.dperp1']])

        ranking = Tensor.get_ranking_matrix(eigen_values)

        voxels_listing = np.arange(ranking.shape[0])
        sorted_eigen_values = [eigen_values[voxels_listing, ranking[:, ind]] for ind in range(ranking.shape[1])]

        fa, md = DTIMeasures().concat_and_calculate(eigen_values[:, 0], eigen_values[:, 1], eigen_values[:, 2])

        extra_maps = {self.name + '.eigen_ranking': ranking,
                      self.name + '.FA': fa,
                      self.name + '.MD': md,
                      self.name + '.AD': sorted_eigen_values[0],
                      self.name + '.RD': (sorted_eigen_values[1] + sorted_eigen_values[2]) / 2}

        for ind in range(3):
            extra_maps.update({self.name + '.vec' + repr(ind): eigen_vectors[:, ind, :]})

            for dimension in range(3):
                extra_maps.update({self.name + '.vec' + repr(ind) + '_' + repr(dimension):
                                   eigen_vectors[:, ind, dimension]})
            extra_maps.update({self.name + '.eigval{}'.format(ind): sorted_eigen_values[ind]})

        return extra_maps

    @staticmethod
    def ensure_2d(array):
        if len(array.shape) < 2:
            return array[None, :]
        return array

    @staticmethod
    def create_eigen_values_matrix(diffusivities):
        return Tensor.ensure_2d(np.squeeze(np.concatenate([m[..., None] for m in diffusivities], axis=1)))

    @staticmethod
    def get_ranking_matrix(eigen_values):
        return Tensor.ensure_2d(np.squeeze(np.argsort(eigen_values, axis=1)[:, ::-1]))

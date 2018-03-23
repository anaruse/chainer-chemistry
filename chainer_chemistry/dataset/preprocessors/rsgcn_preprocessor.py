from chainer_chemistry.dataset.preprocessors.common import construct_adj_matrix
from chainer_chemistry.dataset.preprocessors.common \
    import construct_atomic_number_array
from chainer_chemistry.dataset.preprocessors.common import type_check_num_atoms
from chainer_chemistry.dataset.preprocessors.mol_preprocessor \
    import MolPreprocessor
from chainer_chemistry.functions import sparse_dense2coo

import numpy


class RSGCNPreprocessor(MolPreprocessor):
    """RSGCN Preprocessor

    Args:
        max_atoms (int): Max number of atoms for each molecule, if the
            number of atoms is more than this value, this data is simply
            ignored.
            Setting negative value indicates no limit for max atoms.
        out_size (int): It specifies the size of array returned by
            `get_input_features`.
            If the number of atoms in the molecule is less than this value,
            the returned arrays is padded to have fixed size.
            Setting negative value indicates do not pad returned array.

    """

    def __init__(self, max_atoms=-1, out_size=-1, add_Hs=False, multiplier=1):
        super(RSGCNPreprocessor, self).__init__(add_Hs=add_Hs)
        if max_atoms >= 0 and out_size >= 0 and max_atoms > out_size:
            raise ValueError('max_atoms {} must be equal to or larger than '
                             'out_size {}'.format(max_atoms, out_size))
        self.max_atoms = max_atoms
        self.out_size = out_size
        self.multiplier = multiplier  # for test purpose
        print('# rsgcn_preprocessor.py: multiplier:{}'.format(multiplier))

    def get_input_features(self, mol):
        """get input features

        Args:
            mol (Mol):

        Returns:

        """
        type_check_num_atoms(mol, self.max_atoms)
        atom_array = construct_atomic_number_array(mol, out_size=self.out_size)
        adj_array = construct_adj_matrix(mol, out_size=self.out_size)

        # adjust adjacent matrix
        degree_vec = numpy.sum(adj_array, axis=1)
        degree_sqrt_inv = 1. / numpy.sqrt(degree_vec)
        adj_array *= numpy.broadcast_to(degree_sqrt_inv[:, None],
                                        adj_array.shape)
        adj_array *= numpy.broadcast_to(degree_sqrt_inv[None, :],
                                        adj_array.shape)

        mult = self.multiplier
        if mult > 1:
            n_atoms = atom_array.shape[0]
            x_atom_array = numpy.zeros((n_atoms * mult),
                                       dtype=atom_array.dtype)
            x_adj_array = numpy.zeros((n_atoms * mult, n_atoms * mult),
                                      dtype=adj_array.dtype)
            for i in range(mult):
                x_atom_array[n_atoms*i:n_atoms*(i+1)] = atom_array
                x_adj_array[n_atoms*i:n_atoms*(i+1),
                            n_atoms*i:n_atoms*(i+1)] = adj_array
            atom_array = x_atom_array
            adj_array = x_adj_array

        return atom_array, adj_array


class SparseRSGCNPreprocessor(RSGCNPreprocessor):
    """Sparse RSGCN Preprocessor

    See: RSGCN Preprocessor
    """

    def get_input_features(self, mol):
        """get input features

        Args:
            mol (Mol):

        Returns:

        """
        atom_array, adj_array = super(SparseRSGCNPreprocessor,
                                      self).get_input_features(mol)

        # make sparse matrix
        sp_adj = sparse_dense2coo(adj_array)

        return atom_array, sp_adj.data, sp_adj.row, sp_adj.col
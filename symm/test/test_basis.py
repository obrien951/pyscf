#
# File: test_basis.py
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

import unittest
import numpy
from pyscf.gto.basis import cc_pvqz
from pyscf import symm

def get_so(atoms, basis):
    gpname, atoms = symm.detect_symm(atoms)
    eql_atoms = symm.symm_identical_atoms(gpname, atoms)
    so = symm.basis.symm_adapted_basis(gpname, eql_atoms, atoms, basis)
    n = 0
    for c in so:
        if c.size > 0:
            n += c.shape[1]
    return n, so


class KnowValues(unittest.TestCase):
    def test_symm_orb_h2o(self):
        atoms = [['O' , (1. , 0.    , 0.   ,)],
                 [1   , (0. , -.757 , 0.587,)],
                 [1   , (0. , 0.757 , 0.587,)] ]
        basis = {'H': cc_pvqz.C,
                 'O': cc_pvqz.C,}
        self.assertEqual(get_so(atoms,basis)[0], 165)

    def test_symm_orb_d2h(self):
        atoms = [[1, (0., 0., 0.)],
                 [1, (1., 0., 0.)],
                 [1, (0., 1., 0.)],
                 [1, (0., 0., 1.)],
                 [1, (-1, 0., 0.)],
                 [1, (0.,-1., 0.)],
                 [1, (0., 0.,-1.)]]
        basis = {'H': cc_pvqz.C,}
        self.assertEqual(get_so(atoms,basis)[0], 385)

    def test_symm_orb_c2v(self):
        atoms = [[1, (1., 0., 2.)],
                 [2, (0., 1., 0.)],
                 [1, (-2.,0.,-1.)],
                 [2, (0.,-1., 0.)]]
        basis = {'H' : cc_pvqz.C,
                 'He': cc_pvqz.C,}
        self.assertEqual(get_so(atoms,basis)[0], 220)

    def test_symm_orb_c2h(self):
        atoms = [[1, (1., 0., 2.)],
                 [2, (0., 1., 0.)],
                 [1, (-1.,0.,-2.)],
                 [2, (0.,-1., 0.)]]
        basis = {'H' : cc_pvqz.C,
                 'He': cc_pvqz.C,}
        self.assertEqual(get_so(atoms,basis)[0], 220)

        atoms = [[1, (1., 0., 1.)],
                 [1, (1., 0.,-1.)],
                 [2, (0., 0., 2.)],
                 [2, (2., 0.,-2.)],
                 [3, (1., 1., 0.)],
                 [3, (1.,-1., 0.)]]
        basis = {'H' : cc_pvqz.C,
                 'He': cc_pvqz.C,
                 'Li': cc_pvqz.C,}
        self.assertEqual(get_so(atoms,basis)[0], 330)

    def test_symm_orb_d2(self):
        atoms = [[1, (1., 0., 1.)],
                 [1, (1., 0.,-1.)],
                 [2, (0., 0., 2.)],
                 [2, (2., 0., 2.)],
                 [2, (1., 1.,-2.)],
                 [2, (1.,-1.,-2.)]]
        basis = {'H' : cc_pvqz.C,
                 'He': cc_pvqz.C,}
        self.assertEqual(get_so(atoms,basis)[0], 330)

    def test_symm_orb_ci(self):
        atoms = [[1, ( 1., 0., 0.)],
                 [2, ( 0., 1., 0.)],
                 [3, ( 0., 0., 1.)],
                 [4, ( .5, .5, .5)],
                 [1, (-1., 0., 0.)],
                 [2, ( 0.,-1., 0.)],
                 [3, ( 0., 0.,-1.)],
                 [4, (-.5,-.5,-.5)]]
        basis = {'H' : cc_pvqz.C,
                 'He': cc_pvqz.C,
                 'Li': cc_pvqz.C,
                 'Be': cc_pvqz.C,}
        self.assertEqual(get_so(atoms,basis)[0], 440)

    def test_symm_orb_cs(self):
        atoms = [[1, (1., 0., 2.)],
                 [2, (1., 0., 0.)],
                 [3, (2., 0.,-1.)],
                 [4, (0., 0., 1.)]]
        basis = {'H' : cc_pvqz.C,
                 'He': cc_pvqz.C,
                 'Li': cc_pvqz.C,
                 'Be': cc_pvqz.C,}
        self.assertEqual(get_so(atoms,basis)[0], 220)

    def test_symm_orb_c1(self):
        atoms = [[1, ( 1., 0., 0.)],
                 [2, ( 0., 1., 0.)],
                 [3, ( 0., 0., 1.)],
                 [4, ( .5, .5, .5)]]
        basis = {'H' : cc_pvqz.C,
                 'He': cc_pvqz.C,
                 'Li': cc_pvqz.C,
                 'Be': cc_pvqz.C,}
        self.assertEqual(get_so(atoms,basis)[0], 220)


if __name__ == "__main__":
    print "Full Tests geom"
    unittest.main()
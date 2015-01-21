#!/usr/bin/env python

import time
import ctypes
import tempfile
from functools import reduce
import numpy
import scipy.linalg
import pyscf.lib
from pyscf.lib import logger


def density_fit(mf):
    '''For the given SCF object, update the J, K matrix constructor with
    corresponding density fitting integrals.

    Args:
        mf : an SCF object

    Returns:
        An SCF object with a modified J, K matrix constructor which uses density
        fitting integrals to compute J and K

    Examples:

    >>> mol = gto.Mole()
    >>> mol.build(atom='H 0 0 0; F 0 0 1', basis='ccpvdz', verbose=0)
    >>> mf = scf.density_fit(scf.RHF(mol))
    >>> mf.scf()
    -100.005306000435510

    >>> mol.symmetry = 1
    >>> mol.build(0, 0)
    >>> mf = scf.density_fit(scf.UHF(mol))
    >>> mf.scf()
    -100.005306000435510
    '''
    class HF(mf.__class__):
        def __init__(self):
            self.__dict__.update(mf.__dict__)
            self.auxbasis = 'weigend'
            self._cderi = None
            self.direct_scf = False
            self._keys = self._keys.union(['auxbasis'])

        def get_jk(self, mol, dm, hermi=1):
            return get_jk_(self, mol, dm, hermi)
    return HF()


OCCDROP = 1e-12
BLOCKDIM = 160
def get_jk_(mf, mol, dms, hermi=1):
    from pyscf import df
    from pyscf.ao2mo import _ao2mo
    t0 = (time.clock(), time.time())
    if not hasattr(mf, '_cderi') or mf._cderi is None:
        log = logger.Logger(mf.stdout, mf.verbose)
        nao = mol.nao_nr()
        auxmol = df.incore.format_aux_basis(mol, mf.auxbasis)
        mf._naoaux = auxmol.nao_nr()
        if nao*(nao+1)/2*mf._naoaux*8 < mf.max_memory*1e6:
            mf._cderi = df.incore.cholesky_eri(mol, auxbasis=mf.auxbasis,
                                               verbose=log)
        else:
            mf._cderi_file = tempfile.NamedTemporaryFile()
            mf._cderi = mf._cderi_file.name
            mf._cderi = df.outcore.cholesky_eri(mol, mf._cderi,
                                                auxbasis=mf.auxbasis,
                                                verbose=log)

    s = mf.get_ovlp()
    cderi = mf._cderi
    nao = s.shape[0]

    def fjk(dm):
        #:vj = reduce(numpy.dot, (cderi.reshape(-1,nao*nao), dm.reshape(-1),
        #:                        cderi.reshape(-1,nao*nao))).reshape(nao,nao)
        dmtril = pyscf.lib.pack_tril(dm+dm.T)
        for i in range(nao):
            dmtril[i*(i+1)//2+i] *= .5

        fmmm = df.incore._fpointer('RIhalfmmm_nr_s2_bra')
        fdrv = _ao2mo.libao2mo.AO2MOnr_e2_drv
        ftrans = _ao2mo._fpointer('AO2MOtranse2_nr_s2kl')
        vj = numpy.zeros_like(dm)
        vk = numpy.zeros_like(dm)
        if hermi == 1:
# I cannot assume dm is positive definite because it might be the density
# matrix difference when the mf.direct_scf flag is set.
            e, c = scipy.linalg.eigh(dm, s, type=2)
            pos = e > OCCDROP
            neg = e < -OCCDROP
            if sum(pos)+sum(neg) > 0:
                #:vk = numpy.einsum('pij,jk->kpi', cderi, c[:,abs(e)>OCCDROP])
                #:vk = numpy.einsum('kpi,kpj->ij', vk, vk)
                cpos = numpy.einsum('ij,j->ij', c[:,pos], numpy.sqrt(e[pos]))
                cpos = numpy.asfortranarray(cpos)
                cneg = numpy.einsum('ij,j->ij', c[:,neg], numpy.sqrt(-e[neg]))
                cneg = numpy.asfortranarray(cneg)
                cposargs = (ctypes.c_int(nao),
                            ctypes.c_int(0), ctypes.c_int(cpos.shape[1]),
                            ctypes.c_int(0), ctypes.c_int(0))
                cnegargs = (ctypes.c_int(nao),
                            ctypes.c_int(0), ctypes.c_int(cneg.shape[1]),
                            ctypes.c_int(0), ctypes.c_int(0))
                for b0, b1 in prange(0, mf._naoaux, BLOCKDIM):
                    eri1 = df.load_buf(cderi, b0, b1-b0)
                    buf = reduce(numpy.dot, (eri1, dmtril, eri1))
                    vj += pyscf.lib.unpack_tril(buf, hermi)
                    if cpos.shape[1] > 0:
                        buf = numpy.empty(((b1-b0)*cpos.shape[1],nao))
                        fdrv(ftrans, fmmm,
                             buf.ctypes.data_as(ctypes.c_void_p),
                             eri1.ctypes.data_as(ctypes.c_void_p),
                             cpos.ctypes.data_as(ctypes.c_void_p),
                             ctypes.c_int(b1-b0), *cposargs)
                        vk += numpy.dot(buf.T, buf)
                    if cneg.shape[1] > 0:
                        buf = numpy.empty(((b1-b0)*cneg.shape[1],nao))
                        fdrv(ftrans, fmmm,
                             buf.ctypes.data_as(ctypes.c_void_p),
                             eri1.ctypes.data_as(ctypes.c_void_p),
                             cneg.ctypes.data_as(ctypes.c_void_p),
                             ctypes.c_int(b1-b0), *cnegargs)
                        vk -= numpy.dot(buf.T, buf)
        else:
            #:vk = numpy.einsum('pij,jk->pki', cderi, dm)
            #:vk = numpy.einsum('pki,pkj->ij', cderi, vk)
            fcopy = df.incore._fpointer('RImmm_nr_s2_copy')
            rargs = (ctypes.c_int(nao),
                     ctypes.c_int(0), ctypes.c_int(nao),
                     ctypes.c_int(0), ctypes.c_int(0))
            dm = numpy.asfortranarray(dm)
            for b0, b1 in prange(0, mf._naoaux, BLOCKDIM):
                eri1 = df.load_buf(cderi, b0, b1-b0)
                buf = reduce(numpy.dot, (eri1, dmtril, eri1))
                vj += pyscf.lib.unpack_tril(buf, 1)
                buf = numpy.empty((b1-b0,nao,nao))
                fdrv(ftrans, fmmm,
                     buf.ctypes.data_as(ctypes.c_void_p),
                     eri1.ctypes.data_as(ctypes.c_void_p),
                     dm.ctypes.data_as(ctypes.c_void_p),
                     ctypes.c_int(b1-b0), *rargs)
                buf1 = numpy.empty((b1-b0,nao,nao))
                fdrv(ftrans, fcopy,
                     buf1.ctypes.data_as(ctypes.c_void_p),
                     eri1.ctypes.data_as(ctypes.c_void_p),
                     dm.ctypes.data_as(ctypes.c_void_p),
                     ctypes.c_int(b1-b0), *rargs)
                vk += numpy.dot(buf.reshape(-1,nao).T, buf1.reshape(-1,nao))
        return vj, vk

    if isinstance(dms, numpy.ndarray) and dms.ndim == 2:
        vj, vk = fjk(dms)
    else:
        vjk = [fjk(dm) for dm in dms]
        vj = numpy.array([x[0] for x in vjk])
        vk = numpy.array([x[1] for x in vjk])
    logger.timer(mf, 'vj and vk', *t0)
    return vj, vk


def prange(start, end, step):
    for i in range(start, end, step):
        yield i, min(i+step, end)


if __name__ == '__main__':
    import pyscf.gto
    import pyscf.scf
    mol = pyscf.gto.Mole()
    mol.build(
        verbose = 0,
        atom = [["O" , (0. , 0.     , 0.)],
                [1   , (0. , -0.757 , 0.587)],
                [1   , (0. , 0.757  , 0.587)] ],
        basis = 'ccpvdz',
    )

    method = density_fit(pyscf.scf.RHF(mol))
    method.max_memory = 0
    energy = method.scf()
    print(energy), -76.0259362997

    mol.build(
        verbose = 0,
        atom = [["O" , (0. , 0.     , 0.)],
                [1   , (0. , -0.757 , 0.587)],
                [1   , (0. , 0.757  , 0.587)] ],
        basis = 'ccpvdz',
        spin = 1,
        charge = 1,
    )

    method = density_fit(pyscf.scf.UHF(mol))
    energy = method.scf()
    print(energy), -75.6310072359
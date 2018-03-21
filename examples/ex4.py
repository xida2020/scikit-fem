from skfem import *
from skfem.models import *
import numpy as np

m = read_comsol("examples/square_smalltris.mphtxt")
M = read_comsol("examples/square_largetris.mphtxt")
M.translate((1.0, 0.0))

map = MappingAffine(m)
Map = MappingAffine(M)
e1 = ElementTriP1()
e = ElementVectorH1(e1)

ib = InteriorBasis(m, e, map, 2)
Ib = InteriorBasis(M, e, Map, 2)

def rule(x, y):
    return (x==1.0)

def param(x, y):
    return y

mortar = InterfaceMesh1D(m, M, rule, param, debug_plot=True)
m.show()

#mortar_map = MappingAffine(mortar)

#mb = {}
#mb[0] = MortarBasis(mortar, e, (map, mortar_map), 2, side=0)
#mb[1] = MortarBasis(mortar, e, (Map, mortar_map), 2, side=1)
mb = {}
#joined_mesh = MeshTri(mortar.p, mortar.t)
mortar_map = MappingAffine(mortar)
#mb[0] = FacetBasis(mortar, e, mortar_map, 2, side=0, dofnum=Dofnum(joined_mesh, e))
#mb[1] = FacetBasis(mortar, e, mortar_map, 2, side=1, dofnum=Dofnum(joined_mesh, e))
mb[0] = FacetBasis(mortar, e, mortar_map, 2, side=0)
mb[1] = FacetBasis(mortar, e, mortar_map, 2, side=1)

#mb[0].normals[0] = 1.0
#mb[0].normals[1] = 0.0
#mb[1].normals[0] = 1.0
#mb[1].normals[1] = 0.0

E1 = 1000.0
E2 = 1000.0

nu1 = 0.3
nu2 = 0.3

Mu1 = E1/(2.0*(1.0 + nu1))
Mu2 = E2/(2.0*(1.0 + nu2))

Lambda1 = E1*nu1/((1.0 + nu1)*(1.0 - 2.0*nu1))
Lambda2 = E2*nu2/((1.0 + nu2)*(1.0 - 2.0*nu2))

weakform1 = plane_strain(Lambda=Lambda1, Mu=Mu1)
weakform2 = plane_strain(Lambda=Lambda2, Mu=Mu2)

K1 = asm(weakform1, ib)
K2 = asm(weakform2, Ib)
L = 0
for i in range(2):
    for j in range(2):
        @bilinear_form
        def bilin_penalty(u, du, v, dv, w):
            n = w[2]
            ju = (-1.0)**i*(u[0]*n[0] + u[1]*n[1])
            jv = (-1.0)**j*(v[0]*n[0] + v[1]*n[1])
            #mu = 0.5*(n*[0]*du[0, 0]*n[0] + n[0]*du[0, 1]*n[1])
            #mv = 0.5*(dv[0]*n[0] + dv[1]*n[1])
            h = w[1]
            return 1.0/h*ju*jv# - mu*jv - mv*ju

        L = asm(bilin_penalty, mb[i], mb[j]) + L

@linear_form
def load(v, dv, w):
    return -50*v[1]

f1 = asm(load, ib)
f2 = np.zeros(K2.shape[0])

import scipy.sparse
K = (scipy.sparse.bmat([[K1, None],[None, K2]]) + 1e4*L).tocsr()

i1 = np.arange(K1.shape[0])
i2 = np.arange(K2.shape[0]) + K1.shape[0]

_, D1 = ib.essential_bc(lambda x, y: x==0.0)
_, D2 = Ib.essential_bc(lambda x, y: x==2.0)

x = np.zeros(K.shape[0])

f = np.hstack((f1, f2))

x = np.zeros(K.shape[0])
D = np.concatenate((D1, D2 + ib.dofnum.N))
I = np.setdiff1d(np.arange(K.shape[0]), D)

x[I] = solve(*condense(K, f, I=I))

sf = 1

m.p[0, :] = m.p[0, :] + sf*x[i1][ib.dofnum.n_dof[0, :]]
m.p[1, :] = m.p[1, :] + sf*x[i1][ib.dofnum.n_dof[1, :]]

M.p[0, :] = M.p[0, :] + sf*x[i2][Ib.dofnum.n_dof[0, :]]
M.p[1, :] = M.p[1, :] + sf*x[i2][Ib.dofnum.n_dof[1, :]]

ax = m.draw()
M.draw(ax=ax)
m.show()

print(np.max(x))

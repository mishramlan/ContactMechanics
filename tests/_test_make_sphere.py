#
# Copyright 2020 Lars Pastewka
#           2019 Antoine Sanner
#
# ### MIT license
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import numpy as np

from SurfaceTopography import make_sphere
from ContactMechanics import FreeFFTElasticHalfSpace, PeriodicFFTElasticHalfSpace

def test_sphere(comm):
    nx = 8
    ny = 5
    sx = 6.
    sy = 7.
    R = 20.
    center = (3.,3.)
    substrate = FreeFFTElasticHalfSpace(nb_grid_pts=(nx, ny), young=1., fft="mpi",
                                        physical_sizes=(sx, sy), communicator=comm)
    extended_topography = make_sphere(R, (2*nx, 2*ny), (sx, sy), centre=center,
                                      nb_subdomain_grid_pts=substrate.nb_subdomain_grid_pts,
                                      subdomain_locations=substrate.subdomain_locations,
                                      communicator=comm)
    X, Y, Z = extended_topography.positions_and_heights()

    np.testing.assert_allclose((X-center[0])**2 + (Y-center[1])**2 + (R+Z)**2,  R**2)


def test_sphere_periodic(comm):
    nx = 8
    ny = 5
    sx = 6.
    sy = 7.
    R = 20.
    center = (1., 1.5)
    substrate = PeriodicFFTElasticHalfSpace(nb_grid_pts=(nx, ny), young=1., fft="mpi",
                                            physical_sizes=(sx, sy))

    extended_topography = make_sphere(R, (nx, ny), (sx, sy),
                                      centre=center,
                                      nb_subdomain_grid_pts=substrate.nb_subdomain_grid_pts,
                                      subdomain_locations=substrate.subdomain_locations,
                                      communicator=comm,
                                      periodic=True)

    X, Y, Z = extended_topography.positions_and_heights()

    np.testing.assert_allclose((X - np.where(X < center[0] + sx/2, center[0], center[0] + sx) ) ** 2
                + (Y - np.where(Y < center[1] + sy/2 , center[1], center[1] + sy) ) ** 2
                  + (R + Z) ** 2, R**2)

def test_sphere_standoff(comm):
    nx = 8
    ny = 5
    sx = 6.
    sy = 7.
    R = 2.
    center = (3., 3.)

    standoff = 10.

    substrate = FreeFFTElasticHalfSpace(nb_grid_pts=(nx, ny), young=1., fft="mpi",
                                        physical_sizes=(sx, sy), communicator=comm)
    extended_topography = make_sphere(R, (2 * nx, 2 * ny), (sx, sy),
                                      centre=center,
                                      nb_subdomain_grid_pts=substrate.nb_subdomain_grid_pts,
                                      subdomain_locations=substrate.subdomain_locations,
                                      communicator=comm,
                                      standoff=standoff)
    X, Y, Z = extended_topography.positions_and_heights()

    sl_inner= (X - center[0]) ** 2 + (Y - center[1]) ** 2 < R**2
    np.testing.assert_allclose((
        (X - center[0]) ** 2 +
        (Y - center[1]) ** 2 +
        (R + Z) ** 2)[sl_inner]
        ,  R ** 2)

    np.testing.assert_allclose(Z[np.logical_not(sl_inner)] , - R - standoff )


#def test_paraboloid(comm, fftengine_class)

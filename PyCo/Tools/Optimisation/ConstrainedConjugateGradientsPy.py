#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@file   ConstrainedConjugateGradientsPy.py

@author Lars Pastewka <lars.pastewka@kit.edu>

@date   08 Dec 2015

@brief  Pure Python reference implementation of the constrained conjugate
        gradient algorithm as described in
        I.A. Polonsky, L.M. Keer, Wear 231, 206 (1999)

@section LICENCE

 Copyright (C) 2015-2016 Till Junge, Lars Pastewka

PyCo is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3, or (at
your option) any later version.

PyCo is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with GNU Emacs; see the file COPYING. If not, write to the
Free Software Foundation, Inc., 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.
"""

from math import isnan, pi, sqrt

import numpy as np

import scipy.optimize as optim

from PyCo.Tools import compute_rms_height

###

def constrained_conjugate_gradients(substrate, surface, hardness=None,
                                    external_force=None, offset=None,
                                    disp0=None, pentol=None,
                                    prestol=1e-5, maxiter=100000, logger=None,
                                    callback=None):
    """
    Use a constrained conjugate gradient optimization to find the equilibrium
    configuration deflection of an elastic manifold. The conjugate gradient
    iteration is reset using the steepest descent direction whenever the contact
    area changes.
    Method is described in I.A. Polonsky, L.M. Keer, Wear 231, 206 (1999)

    Parameters
    ----------
    substrate : elastic manifold
        Elastic manifold.
    surface : array_like
        Height profile of the rigid counterbody.
    hardness : array_like
        Hardness of the substrate. Pressure cannot exceed this value. Can be
        scalar or array (i.e. per pixel) value.
    external_force : float
        External force. Don't optimize force if None.
    offset : float
        Offset of rigid surface. Ignore if external_force is specified.
    disp0 : array_like
        Displacement field for initializing the solver. Guess an initial
        value if set to None.
    u_r : array
        Array used for initial displacements. A new array is created if omitted.
    pentol : float
        Maximum penetration of contacting regions required for convergence.
    maxiter : float
        Maximum number of iterations.

    Returns
    -------
    u : array
        2d-array of displacements.
    p : array
        2d-array of pressure.
    converged : bool
        True if iteration stopped due to convergence criterion.
    """

    # Note: Suffix _r deontes real-space _q reciprocal space 2d-arrays

    if pentol is None:
        # Heuristics for the possible tolerance on penetration.
        # This is necessary because numbers can vary greatly
        # depending on the system of units.
        pentol = compute_rms_height(surface)/(10*np.mean(surface.shape))
        # If pentol is zero, then this is a flat surface. This only makes
        # sense for nonperiodic calculations, i.e. it is a punch. Then
        # use the offset to determine the tolerance
        if pentol == 0:
            pentol = (offset+np.mean(surface[...]))/1000
        # If we are still zero use an arbitrary value
        if pentol == 0:
            pentol = 1e-3

    if logger is not None:
        logger.pr('maxiter = {0}'.format(maxiter))
        logger.pr('pentol = {0}'.format(pentol))

    if offset is None:
        offset = 0

    if disp0 is None:
        u_r = np.zeros(substrate.computational_resolution)
    else:
        u_r = disp0.copy()

    comp_slice = [slice(0, substrate.resolution[i])
                  for i in range(substrate.dim)]
    if substrate.dim not in (1, 2):
        raise Exception(
            ("Constrained conjugate gradient currently only implemented for 1 "
             "or 2 dimensions (Your substrate has {}.).").format(
                 substrate.dim))

    comp_mask = np.zeros(substrate.computational_resolution, dtype=bool)
    comp_mask[comp_slice] = True

    surf_mask = np.ma.getmask(surface)
    if surf_mask is np.ma.nomask:
        surf_mask = np.ones(substrate.resolution, dtype=bool)
    else:
        comp_mask[comp_slice][surf_mask] = False
        surf_mask = np.logical_not(surf_mask)
    pad_mask = np.logical_not(comp_mask)
    N_pad = pad_mask.sum()
    u_r[comp_mask] = np.where(u_r[comp_mask] < surface[surf_mask]+offset,
                              surface[surf_mask]+offset,
                              u_r[comp_mask])

    result = optim.OptimizeResult()
    result.nfev = 0
    result.nit = 0
    result.success = False
    result.message = "Not Converged (yet)"

    # Compute forces
    #p_r = -np.fft.ifft2(np.fft.fft2(u_r)/gf_q).real
    if external_force is None:
        p_r = substrate.evaluate_force(u_r)
        result.nfev += 1
    else:
        p_r = -external_force/np.prod(surface.shape)*np.ones_like(u_r)
    # Pressure outside the computational region must be zero
    p_r[pad_mask] = 0.0

    # iteration
    delta = 0
    delta_str = 'reset'
    G_old = 1.0
    t_r = np.zeros_like(u_r)

    for it in range(1, maxiter+1):
        result.nit = it
        # Reset contact area (area that feels compressive stress)
        c_r = p_r < 0.0
        # If a hardness is specified, exclude values that exceed the hardness
        # from the "contact area". Note: "contact area" here is the region that
        # is optimized by the CG iteration.
        if hardness is not None:
            c_r = np.logical_and(c_r, p_r > -hardness)

        # Compute total contact area (area with compressive pressure)
        A = np.sum(c_r)

        # Compute G = sum(g*g) (over contact area only)
        g_r = u_r[comp_mask]-surface[surf_mask]
        if external_force is not None:
            offset = 0
            if A > 0:
                offset = np.mean(g_r[c_r[comp_mask]])
        g_r -= offset
        G = np.sum(c_r[comp_mask]*g_r*g_r)

        # t = (g + delta*(G/G_old)*t) inside contact area and 0 outside
        if delta > 0 and G_old > 0:
            t_r[comp_mask] = c_r[comp_mask]*(g_r + delta*(G/G_old)*t_r[comp_mask])
        else:
            t_r[comp_mask] = c_r[comp_mask]*g_r

        # Compute elastic displacement that belong to t_r
        #substrate (Nelastic manifold: r_r is negative of Polonsky, Kerr's r)
        #r_r = -np.fft.ifft2(gf_q*np.fft.fft2(t_r)).real
        r_r = substrate.evaluate_disp(t_r)
        result.nfev += 1
        # Note: Sign reversed from Polonsky, Keer because this r_r is negative
        # of theirs.
        tau = 0.0
        if A > 0:
            # tau = -sum(g*t)/sum(r*t) where sum is only over contact region
            x = -np.sum(c_r*r_r*t_r)
            if x > 0.0:
                tau = np.sum(c_r[comp_mask]*g_r*t_r[comp_mask])/x
            else:
                G = 0.0

        p_r += tau*c_r*t_r

        # Find area with tensile stress and negative gap
        # (i.e. penetration of the two surfaces)
        mask_tensile = p_r >= 0.0
        # If hardness is specified, include regions where pressure exceeds
        # hardness
        if hardness is not None:
            mask_flowing = p_r <= -hardness
            mask = np.logical_or(mask_tensile, mask_flowing)
        else:
            mask = mask_tensile
        nc_r = np.logical_and(mask[comp_mask], g_r < 0.0)

        # For nonperiodic calculations: Find maximum pressure in pad region.
        # This must be zero.
        pad_pres = 0
        if N_pad > 0:
            pad_pres = abs(p_r[pad_mask]).max()

        # Find maximum pressure outside contacting region and the deviation
        # from hardness inside the flowing regions. This should go to zero.
        max_pres = 0
        if mask_tensile.sum() > 0:
            max_pres = p_r[mask_tensile].max()
        if hardness and mask_flowing.sum() > 0:
            max_pres = max(max_pres, -(p_r[mask_flowing]+hardness).min())

        # Set all compressive stresses to zero
        p_r[mask_tensile] = 0.0
        # If hardness is specified, set all stress larger than hardness to the
        # hardness value
        if hardness is not None:
            p_r[mask_flowing] = hardness

        if np.sum(nc_r) > 0:
            # nc_r contains area that just jumped into contact. Update their
            # forces.
            p_r[comp_mask] += tau*nc_r*g_r

            delta = 0
            delta_str = 'sd'
        else:
            delta = 1
            delta_str = 'cg'

        converged = True
        psum = -np.sum(p_r[comp_mask])
        if external_force is not None:
            converged = abs(psum-external_force) < prestol
            if psum != 0:
                p_r *= external_force/psum
            else:
                p_r = external_force/np.prod(surface.shape)*np.ones_like(p_r)

        # Compute new displacements from updated forces
        #u_r = -np.fft.ifft2(gf_q*np.fft.fft2(p_r)).real
        u_r = substrate.evaluate_disp(p_r)
        result.nfev += 1

        # Store G for next step
        G_old = G

        # Compute root-mean square penetration, max penetration and max force
        # difference between the steps
        if A > 0:
            rms_pen = sqrt(G/A)
        else:
            rms_pen = sqrt(G)
        max_pen = max(0.0, np.max(c_r[comp_mask]*(surface[surf_mask]+offset-
                                                  u_r[comp_mask])))
        result.maxcv = {"max_pen": max_pen,
                        "max_pres": max_pres}

        # Elastic energy would be
        # e_el = -0.5*np.sum(p_r*u_r)

        converged = converged and rms_pen < pentol and max_pen < pentol and max_pres < prestol and pad_pres < prestol

        if converged:
            if logger is not None:
                logger.st(['status', 'it', 'A', 'A/A0', 'tau', 'rms_pen',
                           'max_pen', 'sum_pres', 'pad_pres', 'max_pres'],
                          ['CONVERGED', it, A, A/surf_mask.sum(), tau,
                           rms_pen, max_pen, psum, pad_pres, max_pres],
                          force_print=True)
            # Return full u_r because this is required to reproduce pressure
            # from evalualte_force
            result.x = u_r#[comp_mask]
            # Return partial p_r because pressure outside computational region
            # is zero anyway
            result.jac = -p_r[comp_slice]
            result.offset = offset
            result.success = True
            result.message = "Polonsky converged"
            return result

        if logger is not None:
            logger.st(['status', 'it', 'A', 'A/A0', 'tau', 'rms_pen', 'max_pen',
                       'sum_pres', 'pad_pres', 'max_pres'],
                      [delta_str, it, A, A/surf_mask.sum(), tau, rms_pen,
                       max_pen, psum, pad_pres, max_pres])
        if callback is not None:
            d = dict(area=np.asscalar(np.int64(A)),
                     fractional_area=np.asscalar(np.float64(A/surf_mask.sum())),
                     rms_penetration=np.asscalar(np.float64(rms_pen)),
                     max_penetration=np.asscalar(np.float64(max_pen)),
                     max_pressure=np.asscalar(np.float64(max_pres)),
                     pad_pressure=np.asscalar(np.float64(pad_pres)),
                     penetration_tol=np.asscalar(np.float64(pentol)),
                     pressure_tol=np.asscalar(np.float64(prestol)))
            callback(it, p_r, d)

        if isnan(G) or isnan(rms_pen):
            raise RuntimeError('nan encountered.')

    # Return full u_r because this is required to reproduce pressure
    # from evalualte_force
    result.x = u_r#[comp_mask]
    # Return partial p_r because pressure outside computational region
    # is zero anyway
    result.jac = -p_r[comp_slice]
    result.offset = offset
    result.message = "Reached maxiter = {}".format(maxiter)
    return result

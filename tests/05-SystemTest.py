#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @file   04-SystemTest.py
#
# @author Till Junge <till.junge@kit.edu>
#
# @date   11 Feb 2015
#
# @brief  Tests the creation of tribosystems
#
# @section LICENCE
#
#  Copyright (C) 2015 Till Junge
#
# PyPyContact is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3, or (at
# your option) any later version.
#
# PyPyContact is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Emacs; see the file COPYING. If not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#

import unittest
from numpy.random import rand, random
import numpy as np

from scipy.optimize import minimize
import time

from PyPyContact.System import System, IncompatibleFormulationError
from PyPyContact.System import IncompatibleResolutionError
import PyPyContact.SolidMechanics as Solid
import PyPyContact.ContactMechanics as Contact
import PyPyContact.Surface as Surface
import PyPyContact.Tools as Tools

class SystemTest(unittest.TestCase):
    def setUp(self):
        self.size = (7.5+5*rand(), 7.5+5*rand())
        self.radius = 100
        base_res = 16
        self.res = (base_res, base_res)
        self.young = 3+2*random()

        self.substrate = Solid.PeriodicFFTElasticHalfSpace(
            self.res, self.young, self.size)

        self.eps = 1+np.random.rand()
        self.sig = 3+np.random.rand()
        self.gam = (5+np.random.rand())
        self.rcut = 2.5*self.sig+np.random.rand()
        self.smooth = Contact.LJ93smooth(self.eps, self.sig, self.gam)

        self.sphere = Surface.Sphere(self.radius, self.res, self.size)


    def test_RejectInconsistentInputTypes(self):
        with self.assertRaises(IncompatibleFormulationError):
            System(12, 13, 24)

    def test_RejectInconsistentSizes(self):
        incompat_res = tuple((2*r for r in self.res))
        incompat_sphere = Surface.Sphere(self.radius, incompat_res, self.size)
        with self.assertRaises(IncompatibleResolutionError):
            System(self.substrate, self.smooth, incompat_sphere)

    def test_SmoothContact(self):
        S = System(self.substrate, self.smooth, self.sphere)
        offset = self.sig
        disp = np.zeros(self.res)
        pot, forces = S.evaluate(disp, offset, forces = True)

    def test_SystemGradient(self):
        res = self.res##[0]
        size = self.size##[0]
        substrate = Solid.PeriodicFFTElasticHalfSpace(
            res, 25*self.young, self.size[0])
        sphere = Surface.Sphere(self.radius, res, size)
        S = System(substrate, self.smooth, sphere)
        disp = random(res)*self.sig/10
        disp -= disp.mean()
        offset = self.sig
        gap = S.computeGap(disp, offset)

        ## check subgradient of potential
        V, dV, ddV = S.interaction.evaluate(gap, pot=True, forces=True)
        f = V.sum()
        g = -dV
        fun = lambda x: S.interaction.evaluate(x)[0].sum()
        approx_g = Tools.evaluate_gradient(
            fun, gap, self.sig/1e5)

        tol = 1e-8
        error = Tools.mean_err(g, approx_g)
        msg = ["interaction: "]
        msg.append("f = {}".format(f))
        msg.append("g = {}".format(g))
        msg.append('approx = {}'.format(approx_g))
        msg.append("error = {}".format(error))
        msg.append("tol = {}".format(tol))
        self.assertTrue(error < tol, ", ".join(msg))
        interaction = dict({"e":f,
                            "g":g,
                            "a":approx_g})
        ## check subgradient of substrate
        V, dV = S.substrate.evaluate(disp, pot=True, forces=True)
        f = V.sum()
        g = -dV
        fun = lambda x: S.substrate.evaluate(x)[0].sum()
        approx_g = Tools.evaluate_gradient(
            fun, disp, self.sig/1e5)

        tol = 1e-8
        error = Tools.mean_err(g, approx_g)
        msg = ["substrate: "]
        msg.append("f = {}".format(f))
        msg.append("g = {}".format(g))
        msg.append('approx = {}'.format(approx_g))
        msg.append("error = {}".format(error))
        msg.append("tol = {}".format(tol))
        self.assertTrue(error < tol, ", ".join(msg))
        substrate = dict({"e":f,
                          "g":g,
                          "a":approx_g})

        V, dV = S.evaluate(disp, offset, forces=True)
        f = V
        g = -dV
        approx_g = Tools.evaluate_gradient(S.objective(offset), disp, 1e-5)
        approx_g2 = Tools.evaluate_gradient(
            lambda x: S.objective(offset, gradient=True)(x)[0], disp, 1e-5)
        tol = 1e-6
        self.assertTrue(
            Tools.mean_err(approx_g2, approx_g) < tol,
            "approx_g  = {}\napprox_g2 = {}\nerror = {}, tol = {}".format(
                approx_g, approx_g2, Tools.mean_err(approx_g2, approx_g),
                tol))


        i, s = interaction, substrate
        f_combo = i['e'] + s['e']
        error = abs(f_combo-V)
        self.assertTrue(
            error < tol,
            "f_combo = {}, f = {}, error = {}, tol = {}".format(
                f_combo, V, error, tol))


        g_combo = -i['g'] + s['g'] ## -minus sign comes from derivative of gap
        error = Tools.mean_err(g_combo, g)
        self.assertTrue(
            error < tol,
            "g_combo = {}, g = {}, error = {}, tol = {}".format(
                g_combo, g, error, tol))

        approx_g_combo = -i['a'] + s['a'] ## minus sign comes from derivative of gap
        error = Tools.mean_err(approx_g_combo, approx_g)
        self.assertTrue(
            error < tol,
            "approx_g_combo = {}, approx_g = {}, error = {}, tol = {}".format(
                approx_g_combo, approx_g, error, tol))

        error = Tools.mean_err(g, approx_g)
        msg = []
        msg.append("f = {}".format(f))
        msg.append("g = {}".format(g))
        msg.append('approx = {}'.format(approx_g))
        msg.append("error = {}".format(error))
        msg.append("tol = {}".format(tol))
        self.assertTrue(error < tol, ", ".join(msg))


    def test_unconfirmed_minimization(self):
        ## this merely makes sure that the code doesn't throw exceptions
        ## the plausibility of the result is not verified
        res = self.res[0]
        size = self.size[0]
        substrate = Solid.PeriodicFFTElasticHalfSpace(
            res, 25*self.young, self.size[0])
        sphere = Surface.Sphere(self.radius, res, size)
        S = System(substrate, self.smooth, sphere)
        offset = self.sig
        disp = np.zeros(res)

        fun_jac = S.objective(offset, gradient=True)
        fun     = S.objective(offset, gradient=False)

        info =[]
        start = time.perf_counter()
        result_grad = minimize(fun_jac, disp.reshape(-1), jac=True)
        duration_g = time.perf_counter()-start
        info.append("using gradient:")
        info.append("solved in {} seconds using {} fevals and {} jevals".format(
            duration_g, result_grad.nfev, result_grad.njev))

        start = time.perf_counter()
        result_simple = minimize(fun, disp)
        duration_w = time.perf_counter()-start
        info.append("without gradient:")
        info.append("solved in {} seconds using {} fevals".format(
            duration_w, result_simple.nfev))

        info.append("speedup (timewise) was {}".format(duration_w/duration_g))

        print('\n'.join(info))


        message = ("Success with gradient: {0.success}, message was '{0.message"
                   "}',\nSuccess without: {1.success}, message was '{1.message}"
                   "'").format(result_grad, result_simple)
        self.assertTrue(result_grad.success and result_simple.success,
                        message)

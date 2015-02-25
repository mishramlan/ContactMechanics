#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@file   Systems.py

@author Till Junge <till.junge@kit.edu>

@date   26 Jan 2015

@brief  Defines the interface for PyPyContact systems

@section LICENCE

 Copyright (C) 2015 Till Junge

PyPyContact is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3, or (at
your option) any later version.

PyPyContact is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with GNU Emacs; see the file COPYING. If not, write to the
Free Software Foundation, Inc., 59 Temple Place - Su ite 330,
Boston, MA 02111-1307, USA.
"""

import numpy as np
import scipy

from .. import ContactMechanics, SolidMechanics, Surface
from ..Tools import compare_containers


class IncompatibleFormulationError(Exception):
    # pylint: disable=missing-docstring
    pass


class IncompatibleResolutionError(Exception):
    # pylint: disable=missing-docstring
    pass


class SystemBase(object):
    "Base class for contact systems"
    def __init__(self, substrate, interaction, surface):
        """ Represents a contact problem
        Keyword Arguments:
        substrate   -- An instance of HalfSpace. Defines the solid mechanics in
                       the substrate
        interaction -- An instance of Interaction. Defines the contact
                       formulation
        surface     -- An instance of Surface, defines the profile.
        """
        self.substrate = substrate
        self.interaction = interaction
        self.surface = surface
        self.dim = None
        self.gap = None
        self.disp = None
    _proxyclass = False

    @classmethod
    def is_proxy(cls):
        """
        subclasses may not be able to implement the full interface because they
        try to do something smart and internally compute a different system.
        They should declare to  to be proxies and provide a method called cls.
        deproxyfied() that returns the energy, force and displacement of the
        full problem based on its internal state. E.g at the end of an
        optimization, you could have:
        if system.is_proxy():
            energy, force, disp = system.deproxyfied()
        """
        return cls._proxyclass

    @property
    def resolution(self):
        "For systems, resolution can become non-trivial"
        # pylint: disable=no-self-use
        return None

    # pylint: disable=unused-argument
    @staticmethod
    def handles(substrate_type, interaction_type, surface_type):
        """
        returns whether this class (in practice a subclass) handles this
        combination of types
        Keyword Arguments:
        substrate_type   -- self-explanatory
        interaction_type -- self-explanatory
        surface_type     -- self-explanatory
        """
        return False

    def compute_gap(self, disp, offset, *profile_args, **profile_kwargs):
        """
        evaluate the gap between surface and substrate. Convention is that
        non-penetrating contact has gap >= 0
        """
        if self.dim == 1:
            return (offset - disp[:self.resolution[0]] -
                    self.surface.profile(*profile_args, **profile_kwargs))
        return (offset - disp[:self.resolution[0], :self.resolution[1]] -
                self.surface.profile(*profile_args, **profile_kwargs))

    def compute_normal_force(self):
        "evaluates and returns the normal force between substrate and surface"
        raise NotImplementedError()

    def shape_minimisation_input(self, in_array):
        """
        For minimisation of smart systems, the initial guess array (e.g.
        displacement) may have a non-intuitive shape and size (The problem size
        may be decreased, as for free, non-periodic systems, or increased as
        with augmented-lagrangian-type issues). Use the output of this function
        as argument x0 for scipy minimisation functions. Also, if you initial
        guess has a shape that makes no sense, this will tell you before you
        get caught in debugging scipy-code

        Arguments:
        in_array -- array with the initial guess. has the intuitive shape you
                    think it has
        """
        if np.prod(self.substrate.computational_resolution) == in_array.size:
            return in_array.reshape(-1)
        raise IncompatibleResolutionError()

    def shape_minimisation_output(self, in_array):
        """
        For minimisation of smart systems, the output array (e.g.
        displacement) may have a non-intuitive shape and size (The problem size
        may be decreased, as for free, non-periodic systems, or increased as
        with augmented-lagrangian-type issues). Use  this function
        to get the array shape you expect to have

        Arguments:
        in_array -- array with the initial guess. has the intuitive shape you
                    think it has
        """
        if np.prod(self.substrate.computational_resolution) == in_array.size:
            return in_array.reshape(self.substrate.computational_resolution)
        raise IncompatibleResolutionError()

    def minimize_proxy(self, offset, disp0=None, method='L-BFGS-B',
                       options=None, gradient=True, tol=None,
                       callback=None):
        """
        Convenience function. Eliminates boilerplate code for most minimisation
        problems by encapsulating the use of scipy.minimize for common default
        options. In the case of smart proxy systems, this may also encapsulate
        things like dynamics computation of safety margins, extrapolation of
        results onto the proxied system, etc.

        Parameters:
        offset   -- determines indentation depth
        disp0    -- (default zero) initial guess for displacement field. If not
                    chosen appropriately, results may be unreliable.
        method   -- (defaults to L-BFGS-B, see scipy documentation). Be sure to
                    choose method that can handle high-dimensional parameter
                    spaces.
        options  -- (default None) options to be passed to the minimizer method
        gradient -- (default True) whether to use the gradient or not
        tol      -- (default None) tolerance for termination. For detailed
                    control, use solver-specific options.
        callback -- (default None) callback function to be at each iteration as
                    callback(disp_k) where disp_k is the current displacement
                    vector. Instead of a callable, it can be set to 'True', in
                    which case the system's default callback function is
                    called.
        """
        fun = self.objective(offset, gradient=gradient)
        if disp0 is None:
            disp0 = np.zeros(self.substrate.computational_resolution)
        disp0 = self.shape_minimisation_input(disp0)
        if callback is True:
            callback = self.callback(force=gradient)
        result = scipy.optimize.minimize(fun, x0=disp0, method=method,
                                         jac=gradient, tol=tol,
                                         callback=callback, options=options)
        self.disp = self.shape_minimisation_output(result.x)
        return result

    def objective(self, offset, gradient=False):
        """
        This helper method exposes a scipy.optimize-friendly interface to the
        evaluate() method. Use this for optimization purposes, it makes sure
        that the shape of disp is maintained and lets you set the offset and
        'forces' flag without using scipy's cumbersome argument passing
        interface. Returns a function of only disp
        Keyword Arguments:
        offset   -- determines indentation depth
        gradient -- (default False) whether the gradient is supposed to be used
        """
        raise NotImplementedError()

    def callback(self, force=False):
        """
        Simple callback function that can be handed over to scipy's minimize to
        get updates during minimisation
        Parameters:
        force -- (default False) whether to include the norm of the force
                 vector in the update message
        """
        raise NotImplementedError()


class SmoothContactSystem(SystemBase):
    """
    For smooth contact mechanics (i.e. the ones for which optimization is only
    kinda-hell
    """
    def __init__(self, substrate, interaction, surface):
        """ Represents a contact problem
        Keyword Arguments:
        substrate   -- An instance of HalfSpace. Defines the solid mechanics in
                       the substrate
        interaction -- An instance of Interaction. Defines the contact
                       formulation
        surface     -- An instance of Surface, defines the profile.
        """
        super().__init__(substrate, interaction, surface)
        if not compare_containers(surface.resolution, substrate.resolution):
            raise IncompatibleResolutionError(
                ("the substrate ({}) and the surface ({}) have incompatible "
                 "resolutions.").format(
                     substrate.resolution, surface.resolution))
        self.dim = len(self.substrate.resolution)
        self.energy = None
        self.force = None

    @property
    def resolution(self):
        # pylint: disable=missing-docstring
        return self.surface.resolution

    @staticmethod
    def handles(substrate_type, interaction_type, surface_type):
        is_ok = True
        # any periodic type of substrate formulation should do
        is_ok &= issubclass(substrate_type,
                            SolidMechanics.Substrate)
        if is_ok:
            is_ok &= substrate_type.is_periodic()
        # only soft interactions allowed
        is_ok &= issubclass(interaction_type,
                            ContactMechanics.SoftWall)

        # any surface should do
        is_ok &= issubclass(surface_type,
                            Surface.Surface)
        return is_ok

    def compute_normal_force(self):
        return self.interaction.force.sum()

    def evaluate(self, disp, offset, pot=True, forces=False):
        """
        Compute the energies and forces in the system for a given displacement
        field
        """
        # attention: the substrate may have a higher resolution than the gap
        # and the interaction (e.g. FreeElasticHalfSpace)
        self.gap = self.compute_gap(disp, offset)
        self.interaction.compute(self.gap, pot, forces)
        self.substrate.compute(disp, pot, forces)

        # attention: the gradient of the interaction has the wrong sign,
        # because the derivative of the gap with respect to displacement
        # introduces a -1 factor. Hence the minus sign in the 'sum' of forces:
        self.energy = (self.interaction.energy + self.substrate.energy
                       if pot else None)
        if forces:
            self.force = self.substrate.force.copy()
            if self.dim == 1:
                self.force[:self.resolution[0]] -= self.interaction.force
            else:
                self.force[:self.resolution[0], :self.resolution[1]] -= \
                  self.interaction.force
        else:
            self.force = None

        return (self.energy, self.force)

    def objective(self, offset, gradient=False):
        """
        This helper method exposes a scipy.optimize-friendly interface to the
        evaluate() method. Use this for optimization purposes, it makes sure
        that the shape of disp is maintained and lets you set the offset and
        'forces' flag without using scipy's cumbersome argument passing
        interface. Returns a function of only disp
        Keyword Arguments:
        offset   -- determines indentation depth
        gradient -- (default False) whether the gradient is supposed to be used
        """
        res = self.substrate.computational_resolution
        if gradient:
            def fun(disp):
                # pylint: disable=missing-docstring
                try:
                    self.evaluate(
                        disp.reshape(res), offset, forces=True)
                except ValueError as err:
                    raise ValueError(
                        "{}: disp.shape: {}, res: {}".format(
                            err, disp.shape, res))
                return (self.energy, -self.force.reshape(-1))
        else:
            def fun(disp):
                # pylint: disable=missing-docstring
                return self.evaluate(
                    disp.reshape(res), offset, forces=False)[0]

        return fun

    def callback(self, force=False):
        """
        Simple callback function that can be handed over to scipy's minimize to
        get updates during minimisation
        Parameters:
        force -- (default False) whether to include the norm of the force
                 vector in the update message
        """
        counter = 0
        if force:
            def fun(dummy):
                "includes the force norm in its output"
                nonlocal counter
                counter += 1
                print("at it {}, e = {}, |f| = {}".format(
                    counter, self.energy,
                    np.linalg.norm(np.ravel(self.force))))
        else:
            def fun(dummy):
                "prints messages without force information"
                nonlocal counter
                counter += 1
                print("at it {}, e = {}".format(
                    counter, self.energy))
        return fun


def SystemFactory(substrate, interaction, surface):
    """
    Factory function for contact systems. Checks the compatibility between the
    substrate, interaction method and surface and returns an object of the
    appropriate type to handle it. The returned object is always of a subtype
    of SystemBase.
    Keyword Arguments:
    substrate   -- An instance of HalfSpace. Defines the solid mechanics in
                   the substrate
    interaction -- An instance of Interaction. Defines the contact formulation
    surface     -- An instance of Surface, defines the profile.
    """
    # pylint: disable=invalid-name
    # pylint: disable=no-member
    args = substrate, interaction, surface
    subclasses = list()

    def check_subclasses(base_class, container):
        """
        accumulates a flattened container containing all subclasses of
        base_class
        Parameters:
        base_class -- self-explanatory
        container  -- self-explanatory
        """
        for cls in base_class.__subclasses__():
            check_subclasses(cls, container)
            container.append(cls)

    check_subclasses(SystemBase, subclasses)
    for cls in subclasses:
        if cls.handles(*(type(arg) for arg in args)):
            return cls(*args)
    raise IncompatibleFormulationError(
        ("There is no class that handles the combination of substrates of type"
         " '{}', interactions of type '{}' and surfaces of type '{}'").format(
             *(arg.__class__.__name__ for arg in args)))
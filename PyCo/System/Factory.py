#
# Copyright 2018-2019 Antoine Sanner
#           2018-2019 Lars Pastewka
#           2016 Till Junge
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

"""
Implements a convenient Factory function for Contact System creation
"""

from .. import ContactMechanics, SolidMechanics, Topography
from ..Tools import compare_containers
from .Systems import SystemBase
from .Systems import IncompatibleFormulationError
from .Systems import IncompatibleResolutionError

from PyCo.SolidMechanics import PeriodicFFTElasticHalfSpace
from PyCo.SolidMechanics import FreeFFTElasticHalfSpace
from PyCo.Topography import open_topography
from PyCo.Topography.IO import ReaderBase
from PyCo.ContactMechanics import HardWall

from NuMPI import MPI
from NuMPI.Tools import Reduction

def make_system(substrate, interaction, surface, communicator=MPI.COMM_WORLD,
                physical_sizes=None, system_class=None,
                **kwargs):
    """
    Factory function for contact systems. Checks the compatibility between the
    substrate, interaction method and surface and returns an object of the
    appropriate type to handle it. The returned object is always of a subtype
    of SystemBase.

    Parameters:
    -----------
    substrate   -- An instance of HalfSpace. Defines the solid mechanics in
                   the substrate
    interaction -- An instance of Interaction. Defines the contact formulation
    surface     -- An instance of Topography, defines the profile.

    Returns
    -------
    """
    # pylint: disable=invalid-name
    # pylint: disable=no-member

    subclasses = list()

    # possibility to give file address instead of topography:
    if (type(surface) is str
        or
        (hasattr(surface, 'read') # is a filelike object
         and not hasattr(surface, 'topography'))): # but not a reader
        if communicator is not None:
            openkwargs = {"communicator": communicator}
        else: openkwargs={}
        surface = open_topography(surface, **openkwargs)

    if hasattr(surface, "nb_grid_pts"): # it is a Topography instance
        nb_grid_pts = surface.nb_grid_pts
    else: # assume it is a reader instance
        nb_grid_pts = surface.channels[surface.default_channel]['nb_grid_pts']

    if physical_sizes is None:
        # if physical_sizes is not given in input arguments,
        # try to extract physical sizes from the input topography or reader
        if hasattr(surface, "physical_sizes"):  # it is a Topography instance
            surface_physical_sizes = surface.physical_sizes
        else:  # we assume it is a reader instance
            surface_physical_sizes = surface.channels[surface.default_channel][
                'physical_sizes']
        if surface_physical_sizes is None:
            raise ValueError("physical sizes neither provided in input or in file")
        else:
            physical_sizes = surface_physical_sizes

    # substrate build with physical sizes and nb_grid_pts
    # matching the topography
    if substrate=="periodic":
        substrate = PeriodicFFTElasticHalfSpace(
            nb_grid_pts,
            physical_sizes=physical_sizes, communicator=communicator, **kwargs)
    elif substrate=="free":
        substrate = FreeFFTElasticHalfSpace(
            nb_grid_pts,
            physical_sizes=physical_sizes, communicator=communicator, **kwargs)

    if interaction=="hardwall":
        interaction=HardWall()
    # make shure the interaction has the correcrt communicator
    interaction.pnp = Reduction(communicator)
    interaction.communicator = communicator

    # now the topography is ready to load
    if issubclass(surface.__class__, ReaderBase):
        surface = surface.topography(
            subdomain_locations=substrate.topography_subdomain_locations,
            nb_subdomain_grid_pts=substrate.topography_nb_subdomain_grid_pts,
            physical_sizes=physical_sizes)
        # TODO: this may fail for some readers

    args = substrate, interaction, surface

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

    if system_class is None:
        check_subclasses(SystemBase, subclasses)
        for cls in subclasses:
            if cls.handles(*(type(arg) for arg in args), communicator.size>1):
                return cls(*args)
        raise IncompatibleFormulationError(
            ("There is no class that handles the combination of substrates of type"
             " '{}', interactions of type '{}' and surfaces of type '{}'").format(
                 *(arg.__class__.__name__ for arg in args)))
    else:
        if not system_class.handles(*(type(arg) for arg in args),
                                    communicator.size>1):

            raise IncompatibleFormulationError(
            "Specified system class {} cannot"
            " handle the combination of substrates of type"
            " '{}', interactions of type '{}' and surfaces of type '{}'".format(
            system_class, *(arg.__class__.__name__ for arg in args)) )
        return system_class(*args)


#
# Copyright 2016, 2019-2020 Lars Pastewka
#           2019-2020 Antoine Sanner
#           2015-2016 Till Junge
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
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
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
Defines all solid mechanics model used in PyCo
"""

import ContactMechanics.PipelineFunction  # noqa: F401
from .Substrates import Substrate, ElasticSubstrate, \
    PlasticSubstrate  # noqa: F401
from .FFTElasticHalfSpace import PeriodicFFTElasticHalfSpace, FreeFFTElasticHalfSpace  # noqa: F401
from .Factory import make_system, make_plastic_system  # noqa: F401

try:
    from importlib.metadata import version

    __version__ = version(__name__)
except ImportError:
    from pkg_resources import get_distribution

    __version__ = get_distribution(__name__).version

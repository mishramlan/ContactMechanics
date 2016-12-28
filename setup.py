#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@file   setup.py

@author Till Junge <till.junge@kit.edu>

@date   26 Jan 2015

@brief  Installation script

@section LICENCE

 Copyright (C) 2015 Till Junge

This project is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3, or (at
your option) any later version.

This project is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with GNU Emacs; see the file COPYING. If not, write to the
Free Software Foundation, Inc., 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.
"""

import numpy as np
import versioneer
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize
import os

tools_path = os.path.join(os.path.dirname(__file__), "PyCo/Tools/")
fftext_path = tools_path
extensions = [
    Extension(
        name="PyCo.Tools.fftext",
        sources=[fftext_path + src_name for src_name in ("fftext.pyx", "fftext_cc.cc")],
        extra_compile_args=["-std=c++11"],
        extra_link_args=["-lfftw3", "-lm"],
        # Uncomment the following lines (and comment the above) to get OpenMP
        # support.
        #extra_compile_args=["-std=c++11", "-fopenmp"],
        #extra_link_args=["-lfftw3_omp", "-lfftw3", "-lm", "-fopenmp"],
        include_dirs=[np.get_include()],
        language="c++"),
    Extension(
        name="PyCo.Tools.Optimisation.ConstrainedConjugateGradientsOpt",
        sources=[os.path.join(tools_path,"Optimisation/ConstrainedConjugateGradientsOpt.pyx")],
        include_dirs=[np.get_include()],
        language="c++")]



setup(
    name = "PyCo",
    version = versioneer.get_version(),
    cmdclass = versioneer.get_cmdclass(),
    packages = find_packages(),
    package_data = {'': ['ChangeLog.md']},
    include_package_data = True,
    ext_modules = cythonize(extensions),
    # metadata for upload to PyPI
    author = "Till Junge",
    author_email = "till.junge@kit.edu",
    description = "Simple contact mechanics code",
    license = "GPLv3",
    test_suite = 'tests'
)

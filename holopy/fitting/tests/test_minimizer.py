# Copyright 2011, Vinothan N. Manoharan, Thomas G. Dimiduk, Rebecca W. Perry,
# Jerome Fung, and Ryan McGorty
#
# This file is part of Holopy.
#
# Holopy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Holopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Holopy.  If not, see <http://www.gnu.org/licenses/>.

import holopy
from holopy.scattering.scatterer import Sphere
from holopy.scattering.scatterer import Spheres
from holopy.scattering.theory import Mie
from holopy.core import ImageTarget, Optics
from holopy.fitting import Model, par, fit
from holopy.fitting.minimizer import Nmpfit
import warnings

import numpy as np
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from nose.tools import with_setup, nottest
from nose.plugins.attrib import attr
from numpy.testing import assert_equal, assert_approx_equal, assert_raises, assert_allclose
from ...scattering.scatterer import Sphere, Spheres, ScattererByFunction
from ...scattering.theory import Mie, Multisphere, DDA
from ...core import Optics, ImageTarget, load, save, DataTarget
from ...core.process import normalize
from .. import fit, Parameter, ComplexParameter, par, Parametrization, Model
from ..minimizer import Nmpfit
from ..errors import ParameterSpecificationError, MinimizerConvergenceFailed
from ...core.tests.common import assert_obj_close, get_example_data, assert_parameters_allclose

def test_minimizer():
    x = np.arange(-10, 10, .1)
    a = 5.3
    b = -1.8
    c = 3.4
    gold_dict = OrderedDict((('a', a), ('b', b), ('c', c)))
    y = a*x**2 + b*x + c

    # This test does NOT handle scaling correctly -- we would need a Model
    # which knows the parameters to properly handle the scaling/unscaling
    def cost_func(pars):
        a = pars['a']
        b = pars['b']
        c = pars['c']
        return a*x**2 + b*x + c - y

    # test basic usage
    parameters = [Parameter(name='a', guess = 5),
                 Parameter(name='b', guess = -2),
                 Parameter(name='c', guess = 3)]
    minimizer = Nmpfit()
    result, minimization_details = minimizer.minimize(parameters, cost_func)
    assert_obj_close(gold_dict, result, context = 'basic_minimized_parameters')

    # test inadequate specification
    with assert_raises(ParameterSpecificationError):
        minimizer.minimize([Parameter(name = 'a')], cost_func)

    # now test limiting minimizer iterations
    minimizer = Nmpfit(maxiter=1)
    try:
        result, minimization_details = minimizer.minimize(parameters, cost_func)
    except MinimizerConvergenceFailed as cf: # the fit shouldn't converge
        result, minimization_details = cf.result, cf.details
    assert_equal(minimization_details.niter, 2) # there's always an offset of 1

    # now test parinfo argument passing
    parameters2 = [Parameter(name='a', guess = 5, mpside = 2),
                   Parameter(name='b', guess = -2, limit = [-4, 4.]),
                   Parameter(name='c', guess = 3, step = 1e-4, mpmaxstep = 2., 
                             limit = [0., 12.])]
    minimizer = Nmpfit()
    result2, details2, parinfo = minimizer.minimize(parameters2, cost_func, 
                                                    debug = True)
    assert_equal(parinfo[0]['mpside'], 2)
    assert_equal(parinfo[2]['limits'], np.array([0., 12.])/3.)
    assert_allclose(parinfo[2]['step'], 1e-4/3.)
    assert_equal(parinfo[2]['limited'], [True, True])
    assert_obj_close(gold_dict, result2, context = 'minimized_parameters_with_parinfo')
    


def test_iter_limit():
    #calculate a hologram with known particle positions to do a fit against
    target = ImageTarget(shape = 256, pixel_size = .1, optics = Optics(wavelen = .660, index = 1.33))

    s1 = Sphere(center=(15, 15, 20), n = 1.59, r = 0.5)
    s2 = Sphere(center=(14, 14, 20), n = 1.59, r = 0.5)
    cluster = Spheres([s1, s2])
    holo = Mie.calc_holo(cluster, target)
    from holopy.fitting.minimizer import Nmpfit
    
    #trying to do a fast fit:
    guess1 = Sphere(center = (par(guess = 15, limit = [5,25]), par(15, [5, 25]), par(20, [5, 25])), r = (par(guess = .45, limit=[.4,.6])), n = 1.59)
    guess2 = Sphere(center = (par(guess = 14, limit = [5,25]), par(14, [5, 25]), par(20, [5, 25])), r = (par(guess = .45, limit=[.4,.6])), n = 1.59)
    par_s = Spheres([guess1,guess2])

    model = Model(par_s, Mie.calc_holo, alpha = par(.6, [.1, 1]))
    warnings.simplefilter
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        result4 = fit(model, holo, minimizer = Nmpfit(maxiter=2))

        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert "Convergence Failed" in str(w[-1].message)
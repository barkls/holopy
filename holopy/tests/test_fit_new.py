# Copyright 2011, Vinothan N. Manoharan, Thomas G. Dimiduk, Rebecca
# W. Perry, Jerome Fung, and Ryan McGorty
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
from __future__ import division

import os
try:
    from collections import OrderedDict
except OrderedDict:
    from ordereddict import OrderedDict
import tempfile

import numpy as np

import holopy as hp

from nose.tools import with_setup, nottest
from nose.plugins.attrib import attr
from numpy.testing import assert_allclose, assert_equal, assert_approx_equal, assert_raises
from scatterpy.theory import Mie, Multisphere
from scatterpy.scatterer import Sphere, SphereCluster

from holopy.analyze.fit_new import Parameter, Model, fit, Minimizer, InvalidParameterSpecification
from common import assert_parameters_allclose, assert_obj_close


def setup_optics():
    # set up optics class for use in several test functions
    global optics
    wavelen = 658e-9
    polarization = [0., 1.0]
    divergence = 0
    pixel_scale = [.1151e-6, .1151e-6]
    index = 1.33
    
    optics = hp.optics.Optics(wavelen=wavelen, index=index,
                              pixel_scale=pixel_scale,
                              polarization=polarization,
                              divergence=divergence)
    
def teardown_optics():
    global optics
    del optics

gold_single = OrderedDict((('center[0]', 5.534e-6),
               ('center[1]', 5.792e-6),
               ('center[2]', 1.415e-5),
               ('n.imag', 1e-4),
               ('n.real', 1.582),
               ('r', 6.484e-7)))
gold_alpha = .6497

@attr('medium')
@with_setup(setup=setup_optics, teardown=teardown_optics)
def test_fit_mie_single():
    """
    Fit Mie theory to a hologram of a single sphere
    """
    path = os.path.abspath(hp.__file__)
    path = os.path.join(os.path.split(path)[0],'tests', 'exampledata')
    holo = hp.process.normalize(hp.load(os.path.join(path, 'image0001.npy'),
                                        optics=optics))

    parameters = [Parameter(name='x', guess=.567e-5, limit = [0.0, 1e-5]),
                  Parameter(name='y', guess=.576e-5, limit = [0, 1e-5]),
                  Parameter(name='z', guess=15e-6, limit = [1e-5, 2e-5]),
                  Parameter(name='r', guess=8.5e-7, limit = [1e-8, 1e-5]),
                  Parameter(name='n', guess=1.59, limit = [1, 2]),
                  Parameter(name='alpha', guess=.6, limit = [.1, 1])]

    
    def make_scatterer(x, y, z, r, n):
        return Sphere(n=n+1e-4j, r = r, center = (x, y, z))

    model = Model(parameters, Mie, make_scatterer=make_scatterer)

    result = fit(model, holo)

    assert_parameters_allclose(result.scatterer, gold_single)
    assert_approx_equal(result.alpha, gold_alpha, significant=4)
    assert_equal(model, result.model)

@nottest
@attr('slow')
def test_fit_superposition():
    """
    Fit Mie superposition to a calculated hologram from two spheres
    """
    # Make a test hologram
    optics = hp.Optics(wavelen=6.58e-07, index=1.33, polarization=[0.0, 1.0],
                    divergence=0, pixel_size=None, train=None, mag=None,
                    pixel_scale=[2*2.302e-07, 2*2.302e-07])

    s1 = Sphere(n=1.5891+1e-4j, r = .65e-6, 
                center=(1.56e-05, 1.44e-05, 15e-6))
    s2 = Sphere(n=1.5891+1e-4j, r = .65e-6, 
                center=(3.42e-05, 3.17e-05, 10e-6))
    sc = SphereCluster([s1, s2])
    alpha = .629
    
    theory = Mie(optics, 100)
    holo = theory.calc_holo(sc, alpha)

    # Now construct the model, and fit
    parameters = [Parameter(name = 'x0', guess = 1.6e-5, limit = [0, 1e-4]),
                  Parameter('y0', 1.4e-5, [0, 1e-4]),
                  Parameter('z0', 15.5e-6, [0, 1e-4]),
                  Parameter('r0', .65e-6, [0.6e-6, 0.7e-6]),
                  Parameter('nr', 1.5891, [1, 2]),
                  Parameter('x1', 3.5e-5, [0, 1e-4]),
                  Parameter('y1', 3.2e-5, [0, 1e-4]),
                  Parameter('z1', 10.5e-6, [0, 1e-4]),
                  Parameter('r1', .65e-6, [0.6e-6, 0.7e-6]),
                  Parameter('alpha', .63, [.5, 0.8])]

    def make_scatterer(x0, x1, y0, y1, z0, z1, r0, r1, nr):
        s = SphereCluster([
                Sphere(center = (x0, y0, z0), r=r0, n = nr+1e-4j),
                Sphere(center = (x1, y1, z1), r=r1, n = nr+1e-4j)])
        return s

    model = Model(parameters, Mie, make_scatterer=make_scatterer)
    result = fit(model, holo)

    assert_parameters_allclose(result.scatterer, sc)
    assert_approx_equal(result.alpha, alpha, significant=4)
    assert_equal(result.model, model)

@attr('slow')
def test_fit_multisphere_noisydimer_slow():
    """
    Fit multisphere superposition model to noisified dimer hologram
    """
    optics = hp.Optics(wavelen=658e-9, polarization = [0., 1.0], 
                       divergence = 0., pixel_scale = [0.345e-6, 0.345e-6], 
                       index = 1.334)

    path = os.path.abspath(hp.__file__)
    path = os.path.join(os.path.split(path)[0],'tests', 'exampledata')
    holo = hp.process.normalize(hp.load(os.path.join(path, 'image0002.npy'),
                                        optics=optics))
    
    # Now construct the model, and fit
    parameters = [Parameter(name = 'x0', guess = 1.64155e-5, 
                            limit = [0, 1e-4]),
                  Parameter('y0', 1.7247e-5, [0, 1e-4]),
                  Parameter('z0', 20.582e-6, [0, 1e-4]),
                  Parameter('r0', .6856e-6, [1e-8, 1e-4]),
                  Parameter('nr0', 1.6026, [1, 2]),
                  Parameter('x1', 1.758e-5, [0, 1e-4]),
                  Parameter('y1', 1.753e-5, [0, 1e-4]),
                  Parameter('z1', 21.2698e-6, [1e-8, 1e-4]),
                  Parameter('r1', .695e-6, [1e-8, 1e-4]),
                  Parameter('nr1', 1.6026, [1, 2]),
                  Parameter('alpha', .99, [.1, 1.0])]

    def make_scatterer(x0, x1, y0, y1, z0, z1, r0, r1, nr0, nr1):
        s = SphereCluster([
                Sphere(center = (x0, y0, z0), r=r0, n = nr0+1e-5j),
                Sphere(center = (x1, y1, z1), r=r1, n = nr1+1e-5j)])
        return s

    # initial guess
    #s1 = Sphere(n=1.6026+1e-5j, r = .6856e-6, 
    #            center=(1.64155e-05, 1.7247e-05, 20.582e-6)) 
    #s2 = Sphere(n=1.6026+1e-5j, r = .695e-6, 
    #            center=(1.758e-05, 1.753e-05, 21.2698e-6)) 
    #sc = SphereCluster([s1, s2])
    #alpha = 0.99

    #lb1 = Sphere(1+1e-5j, 1e-8, 0, 0, 0)
    #ub1 = Sphere(2+1e-5j, 1e-5, 1e-4, 1e-4, 1e-4)
    #step1 = Sphere(1e-4+1e-4j, 1e-8, 0, 0, 0)
    #lb = SphereCluster([lb1, lb1]), .1
    #ub = SphereCluster([ub1, ub1]), 1    
    #step = SphereCluster([step1, step1]), 0

    model = Model(parameters, Multisphere, make_scatterer=make_scatterer)
    result = fit(model, holo)
    print result.scatterer

    gold = np.array([1.642e-5, 1.725e-5, 2.058e-5, 1e-5, 1.603, 6.857e-7, 
                     1.758e-5, 1.753e-5, 2.127e-5, 1e-5, 1.603,
                     6.964e-7])
    gold_alpha = 1.0

    assert_parameters_allclose(result.scatterer, gold, rtol=1e-2)
    # TODO: This test fails, alpha comes back as .9899..., where did
    # the gold come from?
    assert_approx_equal(result.alpha, gold_alpha, significant=2)


@attr('fast')
def test_parameter():
    par = Parameter(name='x', guess=.567e-5, limit = [0.0, 1e-5])
    assert_equal(1e-6, par.unscale(par.scale(1e-6)))


@attr('fast')
def test_model():
    parameters = [Parameter(name='x', guess=.567e-5, limit = [0.0, 1e-5]),
                  Parameter(name='y', guess=.576e-5, limit = [0, 1e-5]),
                  Parameter(name='z', guess=15e-6, limit = [1e-5, 2e-5]),
                  Parameter(name='r', guess=8.5e-7, limit = [1e-8, 1e-5]),
                  Parameter(name='alpha', guess=.6, limit = [.1, 1])]

    def make_scatterer(x, y, z, r):
        return Sphere(n=1.59+1e-4j, r = r, center = (x, y, z))

    model = Model(parameters, Mie, make_scatterer=make_scatterer)

    x, y, z, r = 1, 2, 3, 1
    s = model.make_scatterer(x, y, z, r)

    assert_parameters_allclose(s, Sphere(center=(x, y, z), n=1.59+1e-4j,
                                         r=r))

    # check that Model correctly returns None when asked for alpha on a
    # parameter set that does not contain alpha
    
    parameters = [Parameter(name='x', guess=.567e-5, limit = [0.0, 1e-5]),
                  Parameter(name='y', guess=.576e-5, limit = [0, 1e-5]),
                  Parameter(name='z', guess=15e-6, limit = [1e-5, 2e-5]),
                  Parameter(name='r', guess=8.5e-7, limit = [1e-8, 1e-5])]
    model = Model(parameters, Mie, make_scatterer=make_scatterer)

    assert_equal(model.alpha([x, y, z, r]), None)

@with_setup(setup=setup_optics, teardown=teardown_optics)
@attr('fast')
def test_cost_func():
    
    parameters = [Parameter(name='x', guess=.567e-5, limit = [0.0, 1e-5]),
        Parameter(name='y', guess=.576e-5, limit = [0, 1e-5]),
        Parameter(name='z', guess=15e-6, limit = [1e-5, 2e-5]),
        Parameter(name='r', guess=8.5e-7, limit = [1e-8, 1e-5]),
        Parameter(name='alpha', guess=.6, limit = [.1, 1])]

    def make_scatterer(x, y, z, r):
        return Sphere(n=1.59+1e-4j, r = r, center = (x, y, z))

    model = Model(parameters, Mie, make_scatterer=make_scatterer)

    theory = Mie(optics, 100)
    holo = theory.calc_holo(Sphere(center = (.567e-5, .576e-5, 15e-6),
                                   r = 8.5e-7, n = 1.59+1e-4j), .6)

    cost_func = model.cost_func(holo)

    cost = cost_func([p.scale(p.guess) for p in parameters])

    assert_allclose(cost, np.zeros_like(cost), atol=1e-10)
    

@attr('fast')
def test_minimizer():
    x = np.arange(-10, 10, .1)
    a = 5.3
    b = -1.8
    c = 3.4
    y = a*x**2 + b*x + c

    def cost_func(par_values, selection=None):
        a, b, c = par_values
        return a*x**2 + b*x + c - y

    parameters = [Parameter(name='a', guess = 5),
                 Parameter(name='b', guess = -2),
                 Parameter(name='c', guess = 3)]

    minimizer = Minimizer()

    result, converged, minimization_details = minimizer.minimize(parameters,
                                                                 cost_func)

    assert_allclose([a, b, c], result)

    assert_equal(converged, True)

    with assert_raises(InvalidParameterSpecification):
        minimizer.minimize([Parameter('a')])

@attr('fast')
@with_setup(setup=setup_optics, teardown=teardown_optics)
def test_serialization():
    parameters = [Parameter(name='x', guess=.567e-5, limit = [0.0, 1e-5]),
                  Parameter(name='y', guess=.576e-5, limit = [0, 1e-5]),
                  Parameter(name='z', guess=15e-6, limit = [1e-5, 2e-5]),
                  Parameter(name='r', guess=8.5e-7, limit = [1e-8, 1e-5]),
                  Parameter(name='n', guess=1.59, limit = [1, 2]),
                  Parameter(name='alpha', guess=.6, limit = [.1, 1])]
    
    def make_scatterer(x, y, z, r, n):
        return Sphere(n=n+1e-4j, r = r, center = (x, y, z))

    mie = Mie(optics, 100)

    model = Model(parameters, Mie, make_scatterer=make_scatterer)

    holo = mie.calc_holo(
        model.make_scatterer_from_par_values([p.guess for p in
                                              parameters]),
        parameters[-1].guess)

    result = fit(model, holo)

    temp = tempfile.NamedTemporaryFile()
    hp.io.save(temp, result)

    temp.flush()
    temp.seek(0)
    
    loaded = hp.io.yaml_io.load(temp)

    # manually put the make_scatterer function back in because
    # save/load currently does not handle them correctly.  This is a
    # BUG, but not an easy one to fix
    #loaded.model.make_scatterer = make_scatterer

    # VNM: commented above line.  Test *should fail* until the bug is
    # fixed.  Below should work when this bug is corrected.
    # Alternative is to change the specification of the fit results
    # so that it is clear that it will not serialize the
    # make_scatterer function
    loaded.model.make_scatterer_from_par_values([p.guess for p in
                                                 parameters])

    assert_obj_close(result, loaded)

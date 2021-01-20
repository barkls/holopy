.. _advanced_pars_tutorial:

Advanced Parameter Specification
================================

You can use the :class:`.Model` framework to more finely control parameters,
such as specifying a complex refractive index :

..  testcode::

    n = prior.ComplexPrior(real=prior.Gaussian(1.58, 0.02), imag=1e-4)

When this refractive index is used to define a :class:`.Sphere`, :func:`.fit`
will fit to the real part of index of refraction while holding the imaginary
part fixed. You could fit it as well by specifying a :class:`.Prior` for
``imag``.

You may desire to fit holograms with *tied parameters*, in which
several physical quantities that could be varied independently are
constrained to have the same (but non-constant) value. A common
example involves fitting a model to a multi-particle hologram in which
all of the particles are constrained to have the same refractive
index, but the index is determined by the fitter. This may be done by
defining a parameter and using it in multiple places. Other tools for handling
tied parameters are described in the user guide on :ref:`scatterers_user`.

..  testcode::

    n1 = prior.Gaussian(1.58, 0.02)
    sphere_cluster = Spheres([
    Sphere(n = n1, r = 0.5, center = [10., 10., 20.]),
    Sphere(n = n1, r = 0.5, center = [9., 11., 21.])])

from SurfaceTopography import make_sphere
import ContactMechanics as Solid
from NuMPI.Optimization import generic_cg_polonsky
import numpy as np
import scipy.optimize as optim


def test_primal_obj():
    nx, ny = 128, 128
    sx, sy = 1., 1.
    R = 10.

    gtol = 1e-8

    surface = make_sphere(R, (nx, ny), (sx, sy), kind="paraboloid")
    Es = 50.
    substrate = Solid.PeriodicFFTElasticHalfSpace((nx, ny), young=Es,
                                                  physical_sizes=(sx, sy))

    system = Solid.Systems.NonSmoothContactSystem(substrate, surface)

    offset = 0.005
    lbounds = np.zeros((nx, ny))
    bnds = system._reshape_bounds(lbounds, )
    init_gap = np.zeros((nx, ny))  # .flatten()
    disp = init_gap + surface.heights() + offset

    # ####################POLONSKY-KEER##############################
    res = generic_cg_polonsky.min_cg(
        system.primal_objective(offset, gradient=True),
        system.primal_hessian_product,
        disp, polonskykeer=True, gtol=gtol)

    assert res.success
    polonsky = res.x.reshape((nx, ny))

    # ####################BUGNICOURT###################################
    res = generic_cg_polonsky.min_cg(
        system.primal_objective(offset, gradient=True),
        system.primal_hessian_product,
        disp, bugnicourt=True, gtol=gtol)
    assert res.success

    bugnicourt = res.x.reshape((nx, ny))

    # #####################LBFGSB#####################################
    res = optim.minimize(system.primal_objective(offset, gradient=True),
                         disp,
                         method='L-BFGS-B', jac=True,
                         bounds=bnds,
                         options=dict(gtol=1e-8, ftol=1e-20))

    assert res.success
    _lbfgsb = res.x.reshape((nx, ny))

    np.testing.assert_allclose(polonsky, bugnicourt, atol=1e-3)
    np.testing.assert_allclose(polonsky, _lbfgsb, atol=1e-3)
    np.testing.assert_allclose(_lbfgsb, bugnicourt, atol=1e-3)

    # ##########TEST MEAN VALUES#######################################
    mean_val = np.mean(_lbfgsb)
    # disp = _lbfgsb
    # ####################POLONSKY-KEER##############################
    res = generic_cg_polonsky.min_cg(
        system.primal_objective(offset, gradient=True),
        system.primal_hessian_product,
        disp, polonskykeer=True, mean_value=mean_val, gtol=gtol)

    assert res.success
    polonsky_mean = res.x.reshape((nx, ny))

    # ####################BUGNICOURT###################################
    res = generic_cg_polonsky.min_cg(
        system.primal_objective(offset, gradient=True),
        system.primal_hessian_product,
        disp, bugnicourt=True, mean_value=mean_val, gtol=gtol)
    assert res.success

    bugnicourt_mean = res.x.reshape((nx, ny))

    np.testing.assert_allclose(polonsky_mean, _lbfgsb, atol=1e-3)
    np.testing.assert_allclose(bugnicourt_mean, _lbfgsb, atol=1e-3)


def test_dual_obj():
    nx, ny = 128, 128
    sx, sy = 1., 1.
    R = 10.

    gtol = 1e-8

    surface = make_sphere(R, (nx, ny), (sx, sy), kind="paraboloid")
    Es = 50.
    substrate = Solid.PeriodicFFTElasticHalfSpace((nx, ny), young=Es,
                                                  physical_sizes=(sx, sy))

    system = Solid.Systems.NonSmoothContactSystem(substrate, surface)

    offset = 0.005
    lbounds = np.zeros((nx, ny))
    bnds = system._reshape_bounds(lbounds, )
    init_gap = np.zeros((nx, ny))
    disp = init_gap + surface.heights() + offset
    init_pressure = substrate.evaluate_force(disp)

    # ####################LBFGSB########################################
    res = optim.minimize(system.dual_objective(offset, gradient=True),
                         init_pressure,
                         method='L-BFGS-B', jac=True,
                         bounds=bnds,
                         options=dict(gtol=1e-8, ftol=1e-20))
    assert res.success
    CA_lbfgsb = res.x.reshape((nx, ny)) > 0  # Contact area
    print(CA_lbfgsb / (nx * ny))
    _lbfgsb = res.x.reshape((nx, ny))
    fun = system.dual_objective(offset, gradient=True)
    gap_lbfgsb = fun(res.x)[1]
    gap_lbfgsb = gap_lbfgsb.reshape((nx, ny))

    # ###################BUGNICOURT########################################
    res = generic_cg_polonsky.min_cg(
        system.dual_objective(offset, gradient=True),
        system.dual_hessian_product,
        init_pressure, bugnicourt=True, gtol=gtol)
    assert res.success

    CA_bugnicourt = res.x.reshape((nx, ny)) > 0  # Contact area
    gap_bugnicourt = fun(res.x)[1]
    gap_bugnicourt = gap_bugnicourt.reshape((nx, ny))

    # ##################POLONSKY-KEER#####################################
    res = generic_cg_polonsky.min_cg(
        system.dual_objective(offset, gradient=True),
        system.dual_hessian_product,
        init_pressure, polonskykeer=True, gtol=gtol)
    assert res.success

    CA_polonsky = res.x.reshape((nx, ny)) > 0  # Contact area
    gap_polonsky = fun(res.x)[1]
    gap_polonsky = gap_polonsky.reshape((nx, ny))

    np.testing.assert_allclose(CA_lbfgsb, CA_polonsky, atol=1e-3)
    np.testing.assert_allclose(gap_lbfgsb, gap_polonsky, atol=1e-3)
    np.testing.assert_allclose(CA_lbfgsb, CA_bugnicourt, atol=1e-3)
    np.testing.assert_allclose(gap_lbfgsb, gap_bugnicourt, atol=1e-3)
    np.testing.assert_allclose(CA_bugnicourt, CA_polonsky, atol=1e-3)
    np.testing.assert_allclose(gap_bugnicourt, gap_polonsky, atol=1e-3)

    # ##########TEST MEAN VALUES#######################################
    mean_val = np.mean(_lbfgsb)
    # print('mean {}'.format(mean_val))
    # ####################POLONSKY-KEER##############################
    res = generic_cg_polonsky.min_cg(
        system.dual_objective(offset, gradient=True),
        system.dual_hessian_product,
        init_pressure, polonskykeer=True, mean_value=mean_val, gtol=gtol)

    assert res.success
    polonsky_mean = res.x.reshape((nx, ny))
    # print('polonsky mean {}'.format(np.mean(polonsky_mean)))

    # # ####################BUGNICOURT###################################
    res = generic_cg_polonsky.min_cg(
        system.dual_objective(offset, gradient=True),
        system.dual_hessian_product,
        init_pressure, mean_value=mean_val, gtol=gtol, bugnicourt=True,
        residual_plot=False, maxiter=5000)
    assert res.success

    bugnicourt_mean = res.x.reshape((nx, ny))
    print(bugnicourt_mean)

    np.testing.assert_allclose(polonsky_mean, _lbfgsb, atol=1e-3)
    np.testing.assert_allclose(bugnicourt_mean, _lbfgsb, atol=1e-3)

import numpy as np
from scipy.linalg import cholesky

from JumpGP_code_py.calculate_gx import calculate_gx


def calculate_bias_and_variance(model, xt_j, logtheta=None):
    """
    Calculate bias, variance, and related terms for a Gaussian process model.
    
    Arguments:
        model : dict - Contains GP model parameters like 'x', 'y', 'r', 'w', 'gamma', and covariance function 'cv'
        xt_j : np.array - Test location, shape (Nt, 1)
        logtheta : optional, np.array - Hyperparameters for the covariance function

    Returns:
        bias2 : float - Bias squared
        var : float - Variance
        bias : float - Bias
        parts : np.array(5,1) - Components of the bias calculation
    """
    D = model['x'].shape[1]
    xt_j = xt_j.reshape(-1, D)

    if logtheta is None:
        logtheta = model['logtheta']
    
    # Obtain training points from the model
    x_j = model['x']
    
    # Compute `gx` using a function like `calculate_gx`, which you would define based on `model['w']`
    gx, _ = calculate_gx(xt_j, model['w'])
    prior_z = 1 / (1 + np.exp(-0.05 * model['nw'] * gx))

    # Covariance matrices and Cholesky decomposition
    r1 = model['r'].flatten() # for model['r'] shape (N,1)
    K = model['cv'][0](model['cv'][1], logtheta, x_j[r1, :])
    Ktt, Kt = model['cv'][0](model['cv'][1], logtheta, x_j[r1, :], xt_j)
    L = cholesky(K, lower=True)
    
    # Check model properties and calculate RR_1
    k = len(model['r'])
    ns = np.sum(model['r'] == 1)
    if min(ns, k - ns) / k > 0.2:
        RR_1 = - np.mean(model['y'][r1 == 1]) + np.mean(model['y'][r1 == 0])
    else:
        RR_1 = 0  # Could be set to `model['sigma']` if defined

    if np.isnan(RR_1):
        RR_1 = 0
    
    RR = RR_1 ** 2
    
    # Calculate bias and variance components
    one_ns = np.ones(ns)
    one_ns = one_ns.reshape(-1, 1)
    L1 = np.linalg.solve(L, one_ns)
    alpha_before = np.linalg.solve(L.T, L1) / (L1.T @ L1)
    beta_before = np.linalg.solve(L.T, np.linalg.solve(L, Kt))
    
    # Extract gamma values
    gamma_before = model['gamma'][r1]
    gamma_s = prior_z  # Assuming gamma_s is 1 based on the MATLAB code's truncation section
    gamma_s = 1
    
    # Bias calculations
    a1 = alpha_before * (1 - gamma_before)
    b1 = beta_before * gamma_before
    a2 = alpha_before * gamma_before
    b2 = beta_before * (1 - gamma_before)
    ab1 = np.outer(a1, b1)
    ab2 = np.outer(a2, b2)

    bias = np.sum(-a1) * gamma_s - np.sum(a2) * (1 - gamma_s) - np.sum(ab1) + np.sum(ab2)
    parts = [np.sum(a1) * gamma_s, -np.sum(a2) * (1 - gamma_s), -np.sum(ab1), np.sum(ab2), RR_1]
    parts = np.array([x.item() if hasattr(x, 'item') else x for x in parts])
    bias *= RR_1
    bias2 = bias ** 2

    # Variance calculation
    LK = np.linalg.solve(L, Kt)
    var = Ktt - np.sum(LK ** 2)
    
    return bias2.item(), var.item(), bias.item(), parts.reshape(-1,1)
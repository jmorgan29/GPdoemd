"""
MIT License

Copyright (c) 2018 Simon Olofsson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import numpy as np

"""
Marginaliser class
"""
class Analytic:
	def __init__(self, model, param_mean):
		self.num_outputs = model.num_outputs  # Number of output dimensions
		self.call        = model.call         # Function call
		self.param_mean  = param_mean         # Parameter mean
		
	@property
	def Sigma (self):
		return None if not hasattr(self,'_Sigma') else self._Sigma
	@Sigma.setter
	def Sigma (self, value):
		assert isinstance(value, np.ndarray)
		dim_p = len(self.param_mean)
		assert value.shape == (dim_p, dim_p)
		self._Sigma = value

	def d_mu_d_p (self, X):
		grad = lambda x: self.call(x, self.param_mean, grad=True)[1]
		dmu  = np.array([ grad(x) for x in X ])
		assert dmu.ndim == 3
		return dmu

	def d2_mu_d_p2 (self, gp, X):
		return NotImplementedError

	def d_s2_d_p (self, gp, X):
		return NotImplementedError

	def d2_s2_d_p2 (self, gp, X):
		return NotImplementedError
	
	def compute_param_covar (self, Xdata, meas_noise_var):
		# Dimensions
		E = self.num_outputs
		D = len(self.param_mean)

		if isinstance(meas_noise_var, (int, float)):
			meas_noise_var = np.array([meas_noise_var] * E)
		
		# Invert measurement noise covariance
		if meas_noise_var.ndim == 1: 
			imeasvar = np.diag(1./meas_noise_var)
		else: 
			imeasvar = np.linalg.inv(meas_noise_var)
		
		# Inverse covariance matrix
		iA  = np.zeros( (D, D) )
		dmu = self.d_mu_d_p(Xdata)

		for e1 in range(E):
			dmu1 = dmu[:,e1]
			iA  += imeasvar[e1,e1] * np.matmul(dmu1.T, dmu1)

			if meas_noise_var.ndim == 1:
				continue
			for e2 in range(e1+1,E):
				if imeasvar[e1,e2] == 0.:
					continue
				dmu2 = dmu[:,e2]
				iA  += imeasvar[e1,e2] * np.matmul(dmu1.T, dmu2)
				iA  += imeasvar[e2,e1] * np.matmul(dmu2.T, dmu1)

		self.Sigma = np.linalg.inv(iA)


	def __call__ (self, xnew):
		N = len(xnew)
		E = self.num_outputs
		D = len(self.param_mean)

		M   = np.zeros((N,E))
		dmu = np.zeros((N,E,D))

		# Mean and gradient
		for n,x in enumerate(xnew):
			M[n], dmu[n] = self.call(x,self.param_mean,grad=True)

		# Cross-covariance terms
		S = np.zeros((N,E,E))
		for n in range(N):
			S[n] = np.matmul( dmu[n], np.matmul(self.Sigma, dmu[n].T) )

		for e in range(E):
			S[:,e,e] = np.maximum(1e-15,S[:,e,e])
		return M, S

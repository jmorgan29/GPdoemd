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

from GPy.models import GPRegression
from GPy.kern import Kern

from . import SurrogateModel
from ..marginal import GPMarginal
from ..utils import binary_dimensions


class VanillaGPModel (SurrogateModel):
	def __init__ (self, model_dict):
		super().__init__(model_dict)
		# Optional parameters
		self.gp_noise_var     = model_dict.get('gp_noise_var', 1e-6)


	"""
	Surrogate model kernels
	"""
	## Design variable kernels
	@property
	def kern_x (self):
		return None if not hasattr(self,'_kern_x') else self._kern_x
	@kern_x.setter
	def kern_x (self, value):
		if value is not None:
			assert issubclass(value, Kern)
			self._kern_x = value

	## Model parameter kernel
	@property
	def kern_p (self):
		return None if not hasattr(self,'_kern_p') else self._kern_x
	@kern_p.setter
	def kern_p (self, value):
		if value is not None:
			assert issubclass(value, Kern)
			self._kern_p = value

	def set_kernels (self, kern_x, kern_p):
		self.kern_x = kern_x
		self.kern_p = kern_p



	"""
	Surrogate model
	"""
	@property
	def gps (self):
		return None if not hasattr(self,'_gps') else self._gps
	@gps.setter
	def gps(self, value):
		assert len(value) == self.num_outputs
		self._gps = value
	@gps.deleter
	def gps (self):
		self._gps = None

	@property
	def gp_noise_var (self):
		return self._gp_noise_var
	@gp_noise_var.setter
	def gp_noise_var (self, value):
		assert isinstance(value, (int,float)) and value > 0.
		self._gp_noise_var = value


	def gp_surrogate (self, Z=None, Y=None, kern_x=None, kern_p=None):
		self.set_training_data(Z, Y)	
		Z = self.Z
		Y = self.Y

		self.set_kernels(kern_x, kern_p)
		kern_x = self.kern_x
		kern_p = self.kern_p
		dim_x  = self.dim_x - self.dim_b
		dim_p  = self.dim_p
		dim    = dim_x + dim_p

		R, I, J = binary_dimensions(Z, self.binary_variables)

		assert not np.any([ value is None for value in [Z, Y, kern_x, kern_p] ])

		gps = []
		for e in range( self.num_outputs ):
			gps.append([])
			for r in R:
				Jr = (J==r)

				if not np.any(Jr):
					gps[e].append(None)
					continue

				kernx = kern_x(dim_x, range(dim_x), 'kernx')
				kernp = kern_p(dim_p, range(dim_x, dim), 'kernp')
				Zr    = Z[ np.ix_(Jr,  I ) ]
				Yr    = Y[ np.ix_(Jr, [e]) ]
				gp    = GPRegression(Zr, Yr, kernx * kernp)
				gps[e].append(gp)
		self.gps = gps


	def gp_load_hyp (self, index=None):
		if index is None:
			index = range( self.num_outputs )
		elif isinstance(index, int):
			index = [index]

		for e in index:
			gps  = self.gps[e]
			hyps = self.hyp[e]
			for gp,hyp in zip(gps,hyps):
				if gp is None:
					continue
				gp.update_model(False)
				gp.initialize_parameter()
				gp[:] = hyp
				gp.update_model(True)


	def gp_optimize (self, index=None, max_lengthscale=10):
		self.gp_optimise(index=index, max_lengthscale=max_lengthscale)

	def gp_optimise (self, index=None, max_lengthscale=10):
		if index is None:
			index = range( self.num_outputs )
		elif isinstance(index, int):
			index = [index]

		for e in index:
			gps = self.gps[e]
			for gp in gps:
				if gp is None:
					continue
				# Constrain noise variance
				gp.Gaussian_noise.variance.constrain_fixed(self._gp_noise_var)
				# Constrain kern_x lengthscales
				for j in range(self.dim_x-self.dim_b):
					gp.kern.kernx.lengthscale[[j]].constrain_bounded(
						lower=0., upper=max_lengthscale, warning=False )
				# Constrain kern_p lengthscales
				for j in range(self.dim_p):
					gp.kern.kernp.lengthscale[[j]].constrain_bounded(
						lower=0., upper=max_lengthscale, warning=False )
				# Optimise
				gp.optimize()

		hyp = []
		for e,gps in enumerate(self.gps):
			hyp.append([])
			for gp in gps:
				if gp is None:
					hyp[e].append(None)
				else:
					hyp[e].append(gp[:])
		self.hyp = hyp


	def predict (self, xnew, p=None):
		if p is None:
			p = self.pmean
		znew    = np.array([ x.tolist() + p.tolist() for x in xnew ])
		znew    = self.transform_z(znew)
		R, I, J = binary_dimensions(znew, self.binary_variables)
		znew    = znew[:,I]

		n = len(znew)
		M = np.zeros((n, self.num_outputs))
		S = np.zeros((n, self.num_outputs))

		for r in R:
			Jr = J==r
			if not np.any(Jr):
				continue

			for e in range( self.num_outputs ):
				I          = np.ix_(Jr,[e])
				M[I], S[I] = self.gps[e][r].predict_noiseless(znew[Jr])

		return self.backtransform_prediction(M,S)

	def clear_surrogate_model (self):
		del self.gps
		del self.hyp
		self.clear_training_data()
		if not self.gprm is None:
			del self.gprm


	"""
	Marginal surrogate predictions
	"""
	@property
	def gprm (self):
		return None if not hasattr(self,'_gprm') else self._gprm
	@gprm.setter
	def gprm (self, value):
		assert isinstance(value, GPMarginal)
		self._gprm = value
	@gprm.deleter
	def gprm (self):
		self._gprm = None

	def marginal_init (self, method):
		self.gprm = method( self, self.transform_p(self.pmean) )

	def marginal_compute_covar (self, Xdata):
		if self.gprm is None:
			return None
		Xdata = self.transform_x(Xdata)
		mvar  = self.transformed_meas_noise_var
		self.gprm.compute_param_covar(Xdata, mvar)

	def marginal_init_and_compute_covar (self, method, Xdata):
		self.marginal_init(method)
		self.marginal_compute_covar(Xdata)

	def marginal_predict (self, xnew):
		if self.gprm is None:
			return None
		M, S = self.gprm( self.transform_x(xnew) )
		return self.backtransform_prediction(M, S)

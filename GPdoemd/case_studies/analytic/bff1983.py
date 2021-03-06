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
Model super class
"""
class BFF1983Model:
	"""
	G. Buzzi-Ferraris and P. Forzatti
	"A new sequential experimental design procedure for discriminating among 
	rival models" 
	Chem Eng Sci, 38(2):225-232, 1983
	"""
	@property
	def n_outputs (self):
		return 1
	@property
	def x_bounds (self):
		return np.array([[15.,25.], [200.,250.], [5.,10.]])
	@property
	def p_bounds (self):
		return np.array([[   1., 10000.], 
			             [ 1e-2,    10.], 
			             [ 1e-4,     1.], 
			             [   1.,  1000.], 
			             [1e-10,     1.]])

"""
Models
"""
class M1 (BFF1983Model):
	@property
	def name (self):
		return 'M1'

	def __call__ (self,x,p,grad=False):
		x1,x2,x3 = x.astype(float)
		K1,K2,K3,K4,Keq = p

		nom = x1 * x2**2 - x3/Keq
		dnm = K1 + K2*x1 + K3*x2 + K4*x3
		y   = nom/dnm**2
		if not grad: return np.array([y])

		dK1  = -2. * y / dnm
		dK2  = dK1 * x1
		dK3  = dK1 * x2
		dK4  = dK1 * x3
		dKeq = x3 / (Keq * dnm)**2
		return np.array([y]), np.array([[dK1, dK2, dK3, dK4, dKeq]])

class M2 (BFF1983Model):
	@property
	def name (self):
		return 'M2'

	def __call__ (self,x,p,grad=False):
		x1,x2,x3 = x.astype(float)
		K1,K2,K3,K4,Keq = p

		nom = x1 * x2**2 - x3/Keq
		dnm = K1 + K2*x1 + K3*x2 + K4*x1*x2
		y   = nom/dnm
		if not grad: return np.array([y])

		dK1  = -y / dnm
		dK2  = dK1 * x1
		dK3  = dK1 * x2
		dK4  = dK1 * x1 * x2
		dKeq = x3 / (Keq**2 * dnm)
		return np.array([y]), np.array([[dK1, dK2, dK3, dK4, dKeq]])

class M3 (BFF1983Model):
	@property
	def name (self):
		return 'M3'

	def __call__ (self,x,p,grad=False):
		x1,x2,x3 = x.astype(float)
		K1,K2,K3,K4,Keq = p

		nom = x1 * x2**2 - x3/Keq
		dnm = x2**2 * (K1 + K2*x3 + K3*x2) + K4*x2*x3
		y   = nom/dnm
		if not grad: return np.array([y])

		dK1  = -y * x2**2 / dnm
		dK2  = dK1 * x3
		dK3  = dK1 * x2
		dK4  = dK1 * x3 / x2
		dKeq = x3 / (Keq**2 * dnm)
		return np.array([y]), np.array([[dK1, dK2, dK3, dK4, dKeq]])

class M4 (BFF1983Model):
	@property
	def name (self):
		return 'M4'

	def __call__ (self,x,p,grad=False):
		x1,x2,x3 = x.astype(float)
		x32 = x3/x2
		K1,K2,K3,K4,Keq = p

		nom = x1 * x2**2 - x3/Keq
		dnm = K1 + K2*x1 + K3*x32 + K4*x3
		y   = nom / (x2 * dnm**2)
		if not grad: return np.array([y])

		dK1  = -2. * y / dnm
		dK2  = dK1 * x1
		dK3  = dK1 * x32
		dK4  = dK1 * x3
		dKeq = x32 / (Keq * dnm)**2
		return np.array([y]), np.array([[dK1, dK2, dK3, dK4, dKeq]])

class M5 (BFF1983Model):
	@property
	def name (self):
		return 'M5'

	def __call__ (self,x,p,grad=False):
		x1,x2,x3 = x.astype(float)
		K1,K2,K3,K4,Keq = p

		nom = x1 * x2**2 - x3/Keq
		dnm = K1 + K2*x2 + K3*x1*x2 + K4*x3
		y   = nom/dnm**2
		if not grad: return np.array([y])

		dK1  = -2. * y / dnm
		dK2  = dK1 * x2
		dK3  = dK1 * x1 * x2
		dK4  = dK1 * x3
		dKeq = x3 / (Keq * dnm)**2
		return np.array([y]), np.array([[dK1, dK2, dK3, dK4, dKeq]])

"""
Data generator
"""
class DataGen (M5):
	@property
	def truemodel (self):
		return 4
	@property
	def measvar (self):
		return np.array([4e-7])
	@property
	def p (self):
		return [1704., 4.25, 0.241, 444.6, 1.7e-5]

	def __call__ (self,x):
		state = super().__call__(x, self.p)
		noise = np.sqrt(self.measvar) * np.random.randn(self.n_outputs)
		return state + noise

"""
Get model functions
"""
def get (*args):
	return DataGen(), [M1(),M2(),M3(),M4(),M5()]




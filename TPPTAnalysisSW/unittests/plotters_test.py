"""
Copyright (c) 2019, OptoFidelity OY

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    3. All advertising materials mentioning features or use of this software must display the following acknowledgement: This product includes software developed by the OptoFidelity OY.
    4. Neither the name of the OptoFidelity OY nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import unittest
import TPPTAnalysisSW.plotters as plotters
import numpy as np
import random
import matplotlib.pyplot as plt
import os
from TPPTAnalysisSW.measurementdb import *

class TestEvalFunctions(unittest.TestCase):
	
	def test_get_color(self):
		print(plotters.get_color(1000,0,2550))
		
	def test_eval_closest_point(self):
		linebegin = [0,0]
		lineend = [5,5]
		point = [2,1]
		p,d = plotters.eval_closest_point_at_line(linebegin,lineend,point)
	def test_panel_to_robot(self):
		x = 48.0
		y = 80.0
		topleftpanel = [0.0,0.0]
		botrightpanel = [480.0,800.0]
		topleftrobo = [240.0,400.0]
		botrightrobo = [0.0,0.0]
		v1 = plotters.eval_panel_to_robot(x,y,topleftpanel,botrightpanel,topleftrobo,botrightrobo)
		topleftpanel = [0.0,0.0]
		botrightpanel = [480.0,800.0]
		topleftrobo = [250.0,410.0]
		botrightrobo = [10.0,10.0]
		v2 = plotters.eval_panel_to_robot(x,y,topleftpanel,botrightpanel,topleftrobo,botrightrobo)
		v2 = [v2[0]-10.0,v2[1]-10.0]
		self.assertEqual(v1,v2)
class TestPlotters(unittest.TestCase):

	def set_up(self):
		plt.clf()
	def save(self,file,fig):
		savepath = os.getcwd()+"/"+file
		print(savepath)
		fig.savefig(savepath)
	def test_plot_offset_line(self):
		fig = plt.figure()
		plt.axis('equal')
		linebegin = [0,0]
		lineend = [100,100]
		mpoints = np.arange(0,100,5)
		mpoints = map(lambda x: [x+(random.random()*5-2.5),x+(random.random()*5-2.5)+5],mpoints)
		fig = plotters.plot_offset_line(fig,mpoints)
		
		plt.axis('equal')
		linebegin = [0,50]
		lineend = [100,100]
		mpoints = np.arange(0,100,5)
		mpoints = map(lambda x: [x+(random.random()*5-2.5),x+(random.random()*5-2.5)+5],mpoints)
		fig = plotters.plot_offset_line(fig,mpoints)
		self.save("test_plot_offset_line.png",fig)
	def test_single_point_diff(self):
		fig = plt.figure()
		plt.axis('equal')
		linebegin = [0,0]
		lineend = [5,5]
		points =[[2,1]]
		fig = plotters.plot_measurement_line(fig,points,linebegin,lineend)
		self.save("test_single_point_diff.png",fig)
	def test_plot_line_diff(self):
		fig = plt.figure()
		plt.axis('equal')
		linebegin = [0,0]
		lineend = [100,100]
		mpoints = np.arange(0,100,2)
		mpoints = map(lambda x: [x+(random.random()*5-2.5),x+(random.random()*5-2.5)],mpoints)
		fig = plotters.plot_measurement_line(fig,mpoints,linebegin,lineend)
		self.save("test_plot_line_diff.png",fig)
	def test_plot_dx_dy_chart(self):
		fig = plt.figure()
		plt.axis('equal')
		plt.grid(True)
		a= 40
		b = 20
		xt,yt = plotters.eval_ellipse_points(np.arange(0,2*np.pi,0.1),a,b,np.pi/3,20,20)
		measurements = []
		for i in range(0,len(xt)):
			measurements.append([xt[i]+(random.random()*5-2.5+0.5),yt[i]+(random.random()*5-2.5+0.5)])
		delays = [random.random()*20 for i in measurements]
		plotters.plot_dx_dy_chart(fig,measurements,delays,xt,yt,2.0,params={'errmin' : 0,'errmax' : 20})
		self.save("test_plot_dx_dy_chart.png",fig)
	def test_plot_ellipse(self):
		fig = plt.figure()
		plt.axis('equal')
		tarr = np.arange(0,2*np.pi,0.1)
		a= 40
		b = 20
		xt,yt = plotters.eval_ellipse_points(np.arange(0,2*np.pi,0.1),a,b,np.pi/3,20,20)
		measurements = []
		for i in range(0,len(xt)):
			measurements.append([xt[i]+(random.random()*5-2.5),yt[i]+(random.random()*5-2.5)])
		#print measurements
		plotters.plot_ellipse_diff(fig,measurements,a,b,np.pi/3,20,20)
		self.save("test_plot_ellipse.png",fig)
	def test_plot_jitter(self):
		mpoints = np.arange(0,100,0.5)
		mpoints = map(lambda x: [x,x+(random.random()*20.0-10.0)],mpoints)
		fig = plt.figure()
		distances,jits,m = plotters.eval_jitter(mpoints,1.0)
		fig = plotters.plot_jitter_per_distance(fig,distances,jits)
		self.save("test_plot_jitter_bars.png",fig)
		fig = plt.figure()
		fig = plotters.plot_offset_line(fig,mpoints)
		self.save("test_plot_jitter_line.png",fig)
	def test_plot_p2p_measurements(self):
		xlen = 400
		ylen = 400
		mpoints = [[random.random()*xlen,random.random()*ylen] for i in range(0,400)]
		rpoints = [[i[0]+5,i[1]+5]for i in mpoints]
		delays = [random.random()*20 for i in mpoints]
		fig = plt.figure()
		fig = plotters.plot_p2p_measurements(fig,mpoints,rpoints,delays)
		self.save("test_plot_p2p_measurements.png",fig)
if __name__ == '__main__':
    unittest.main()
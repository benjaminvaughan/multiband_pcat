import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.fftpack import fft, ifft
import networkx as nx
from matplotlib.collections import PatchCollection
import matplotlib.patches as patches
from PIL import Image
import sys
from pcat_spire import *

if sys.version_info[0] == 3:
	from celluloid import Camera

from fourier_bkg_modl import *


def convert_pngs_to_gif(filenames, gifdir='/Users/richardfeder/Documents/multiband_pcat/', name='', duration=1000, loop=0):

	# Create the frames
	frames = []
	for i in range(len(filenames)):
		new_frame = Image.open(gifdir+filenames[i])
		frames.append(new_frame)

	# Save into a GIF file that loops forever
	frames[0].save(gifdir+name+'.gif', format='GIF',
				   append_images=frames[1:],
				   save_all=True,
				   duration=duration, loop=loop)

def compute_dNdS(trueminf, stars, nsrc, _X=0, _Y=1, _F=2):

	binz = np.linspace(np.log10(trueminf)+3., np.ceil(np.log10(np.max(stars[_F, 0:nsrc]))+3.), 20)
	hist = np.histogram(np.log10(stars[_F, 0:nsrc])+3., bins=binz)
	logSv = 0.5*(hist[1][1:]+hist[1][:-1])-3.
	binz_Sz = 10**(binz-3)
	dSz = binz_Sz[1:]-binz_Sz[:-1]
	dNdS = hist[0]

	return logSv, dSz, dNdS


def plot_atcr(listsamp, title):

	numbsamp = listsamp.shape[0]
	four = fft(listsamp - np.mean(listsamp, axis=0), axis=0)
	atcr = ifft(four * np.conjugate(four), axis=0).real
	atcr /= np.amax(atcr, 0)

	autocorr = atcr[:int(numbsamp/2), ...]
	indxatcr = np.where(autocorr > 0.2)
	timeatcr = np.argmax(indxatcr[0], axis=0)

	numbsampatcr = autocorr.size

	figr, axis = plt.subplots(figsize=(6,4))
	plt.title(title, fontsize=16)
	axis.plot(np.arange(numbsampatcr), autocorr)
	axis.set_xlabel(r'$\tau$', fontsize=16)
	axis.set_ylabel(r'$\xi(\tau)$', fontsize=16)
	axis.text(0.8, 0.8, r'$\tau_{exp} = %.3g$' % timeatcr, ha='center', va='center', transform=axis.transAxes, fontsize=16)
	axis.axhline(0., ls='--', alpha=0.5)
	plt.tight_layout()

	return figr


def plot_custom_multiband_frame(obj, resids, models, panels=['data0','model0', 'residual0','residual1','residual2','residual2zoom'], \
							zoomlims=[[[0, 40], [0, 40]],[[70, 110], [70, 110]], [[50, 70], [50, 70]]], \
							ndeg=0.11, panel0=None, panel1=None, panel2=None, panel3=None, panel4=None, panel5=None, fourier_bkg=None, sz=None, frame_dir_path=None, smooth_fac=4):

	
	if panel0 is not None:
		panels[0] = panel0
	if panel1 is not None:
		panels[1] = panel1
	if panel2 is not None:
		panels[2] = panel2
	if panel3 is not None:
		panels[3] = panel3
	if panel4 is not None:
		panels[4] = panel4
	if panel5 is not None:
		panels[5] = panel5

	plt.gcf().clear()
	plt.figure(1, figsize=(15, 10))
	plt.clf()

	for i in range(6):

		plt.subplot(2,3,i+1)

		band_idx = int(panels[i][-1])


		if 'data' in panels[i]:

			plt.imshow(obj.dat.data_array[band_idx], origin='lower', interpolation='none', cmap='Greys', vmin=np.percentile(obj.dat.data_array[band_idx], 5.), vmax=np.percentile(obj.dat.data_array[band_idx], 95.0))
			plt.colorbar()

			if band_idx > 0:
				xp, yp = obj.dat.fast_astrom.transform_q(obj.stars[obj._X, 0:obj.n], obj.stars[obj._Y, 0:obj.n], band_idx-1)
				plt.scatter(xp, yp, marker='x', s=obj.stars[obj._F+1, 0:obj.n]*100, color='r')
			else:
				plt.scatter(obj.stars[obj._X, 0:obj.n], obj.stars[obj._Y, 0:obj.n], marker='x', s=obj.stars[obj._F, 0:obj.n]*100, color='r')
			if 'zoom' in panels[i]:
				plt.title('Data (band '+str(band_idx)+', zoomed in)')
				plt.xlim(zoomlims[band_idx][0][0], zoomlims[band_idx][0][1])
				plt.ylim(zoomlims[band_idx][1][0], zoomlims[band_idx][1][1])
			else:
				plt.title('Data (band '+str(band_idx)+')')
				plt.xlim(-0.5, obj.imszs[band_idx][0]-0.5)
				plt.ylim(-0.5, obj.imszs[band_idx][1]-0.5)


		elif 'model' in panels[i]:

			plt.imshow(models[band_idx], origin='lower', interpolation='none', cmap='Greys', vmin=np.percentile(models[band_idx], 5.), vmax=np.percentile(models[band_idx], 95.0))
			plt.colorbar()

			if 'zoom' in panels[i]:
				plt.title('Model (band '+str(band_idx)+', zoomed in)')
				plt.xlim(zoomlims[band_idx][0][0], zoomlims[band_idx][0][1])
				plt.ylim(zoomlims[band_idx][1][0], zoomlims[band_idx][1][1])
			else:
				plt.title('Model (band '+str(band_idx)+')')
				plt.xlim(-0.5, obj.imszs[band_idx][0]-0.5)
				plt.ylim(-0.5, obj.imszs[band_idx][1]-0.5)

		elif 'injected_diffuse_comp' in panels[i]:
			plt.imshow(obj.dat.injected_diffuse_comp[band_idx], origin='lower', interpolation='none', cmap='Greys', vmin=np.percentile(obj.dat.injected_diffuse_comp[band_idx], 5.), vmax=np.percentile(obj.dat.injected_diffuse_comp[band_idx], 95.))
			plt.colorbar()
		
			plt.title('Injected cirrus (band '+str(band_idx)+')')
			plt.xlim(-0.5, obj.imszs[band_idx][0]-0.5)
			plt.ylim(-0.5, obj.imszs[band_idx][1]-0.5)

		elif 'fourier_bkg' in panels[i]:
			fbkg = fourier_bkg[band_idx]

			# if band_idx > 1:
				# fbkg = gaussian_filter(fbkg, sigma=0.25*obj.imszs[0][0]/obj.n_fourier_terms)

			plt.imshow(fbkg, origin='lower', interpolation='none', cmap='Greys', vmin = np.percentile(fbkg , 5), vmax=np.percentile(fbkg, 95))
			plt.colorbar()
		
			plt.title('Sum of FCs (band '+str(band_idx)+')')
			plt.xlim(-0.5, obj.imszs[band_idx][0]-0.5)
			plt.ylim(-0.5, obj.imszs[band_idx][1]-0.5)


		elif 'residual' in panels[i]:

			if obj.gdat.weighted_residual:
				plt.imshow(resids[band_idx]*np.sqrt(obj.dat.weights[band_idx]), origin='lower', interpolation='none', cmap='Greys', vmin=-5, vmax=5)
			else:
				plt.imshow(resids[band_idx], origin='lower', interpolation='none', cmap='Greys', vmin = np.percentile(resids[band_idx][obj.dat.weights[band_idx] != 0.], 5), vmax=np.percentile(resids[band_idx][obj.dat.weights[band_idx] != 0.], 95))
			plt.colorbar()

			if band_idx > 0:
				xp, yp = obj.dat.fast_astrom.transform_q(obj.stars[obj._X, 0:obj.n], obj.stars[obj._Y, 0:obj.n], band_idx-1)
				plt.scatter(xp, yp, marker='x', s=obj.stars[obj._F+1, 0:obj.n]*100, color='r')
			else:
				plt.scatter(obj.stars[obj._X, 0:obj.n], obj.stars[obj._Y, 0:obj.n], marker='x', s=obj.stars[obj._F, 0:obj.n]*100, color='r')

			if 'zoom' in panels[i]:
				plt.title('Residual (band '+str(band_idx)+', zoomed in)')
				plt.xlim(zoomlims[band_idx][0][0], zoomlims[band_idx][0][1])
				plt.ylim(zoomlims[band_idx][1][0], zoomlims[band_idx][1][1])
			else:           
				plt.title('Residual (band '+str(band_idx)+')')
				plt.xlim(-0.5, obj.imszs[band_idx][0]-0.5)
				plt.ylim(-0.5, obj.imszs[band_idx][1]-0.5)		

		elif 'sz' in panels[i]:


			plt.imshow(sz[band_idx], origin='lower', interpolation='none', cmap='Greys', vmin = np.percentile(sz[band_idx], 1), vmax=np.percentile(sz[band_idx], 99))
			plt.colorbar()

			if band_idx > 0:
				xp, yp = obj.dat.fast_astrom.transform_q(obj.stars[obj._X, 0:obj.n], obj.stars[obj._Y, 0:obj.n], band_idx-1)
				plt.scatter(xp, yp, marker='x', s=obj.stars[obj._F+1, 0:obj.n]*100, color='r')
			else:
				plt.scatter(obj.stars[obj._X, 0:obj.n], obj.stars[obj._Y, 0:obj.n], marker='x', s=obj.stars[obj._F, 0:obj.n]*100, color='r')

			if 'zoom' in panels[i]:
				plt.title('SZ (band '+str(band_idx)+', zoomed in)')
				plt.xlim(zoomlims[band_idx][0][0], zoomlims[band_idx][0][1])
				plt.ylim(zoomlims[band_idx][1][0], zoomlims[band_idx][1][1])
			else:           
				plt.title('SZ (band '+str(band_idx)+')')
				plt.xlim(-0.5, obj.imszs[band_idx][0]-0.5)
				plt.ylim(-0.5, obj.imszs[band_idx][1]-0.5)		


		elif panels[i]=='dNdS':

			logSv, dSz, dNdS = compute_dNdS(obj.trueminf, obj.stars, obj.n)

			if obj.gdat.raw_counts:
				plt.plot(logSv+3, dNdS, marker='.')
				plt.ylabel('dN/dS')
				plt.ylim(5e-1, 3e3)

			else:
				n_steradian = ndeg/(180./np.pi)**2 # field covers 0.11 degrees, should change this though for different fields
				n_steradian *= obj.gdat.frac # a number of pixels in the image are not actually observing anything
				dNdS_S_twop5 = dNdS*(10**(logSv))**(2.5)
				plt.plot(logSv+3, dNdS_S_twop5/n_steradian/dSz, marker='.')
				plt.ylabel('dN/dS.$S^{2.5}$ ($Jy^{1.5}/sr$)')
				plt.ylim(1e0, 1e5)

			plt.yscale('log')
			plt.legend()
			plt.xlabel('log($S_{\\nu}$) (mJy)')
			plt.xlim(np.log10(obj.trueminf)+3.-0.5, 2.5)


	if frame_dir_path is not None:
		plt.savefig(frame_dir_path, bbox_inches='tight', dpi=200)
	plt.draw()
	plt.pause(1e-5)



def scotts_rule_bins(samples):
	'''
	Computes binning for a collection of samples using Scott's rule, which minimizes the integrated MSE of the density estimate.

	Parameters
	----------

	samples : 'list' or '~numpy.ndarray' of shape (Nsamples,)

	Returns
	-------

	bins : `~numpy.ndarray' of shape (Nsamples,)
		bin edges

	'''
	n = len(samples)
	bin_width = 3.5*np.std(samples)/n**(1./3.)
	k = np.ceil((np.max(samples)-np.min(samples))/bin_width)
	bins = np.linspace(np.min(samples), np.max(samples), k)
	return bins


def make_pcat_sample_gif(timestr, im_path, gif_path=None, cat_xy=True, resids=True, color_color=True, result_path='/Users/luminatech/Documents/multiband_pcat/spire_results/', \
						gif_fpr = 5):

	chain = np.load('spire_results/'+timestr+'/chain.npz')
	residz = chain['residuals0']
	gdat, filepath, result_path = load_param_dict(timestr, result_path='spire_results/')


	n_panels = np.sum(np.array([cat_xy, resids, color_color]).astype(np.int))
	print('n_panels = ', n_panels)

	im = fits.open(im_path)['SIGNAL'].data

	im = im[gdat.bounds[0][0,0]:gdat.bounds[0][0,1], gdat.bounds[0][1,0]:gdat.bounds[0][1,1]]

	fig = plt.figure(figsize=(6*n_panels,7))
	camera = Camera(fig)


	for k in np.arange(0, len(residz), 10):
		tick = 1

		if cat_xy:
			plt.subplot(1,n_panels, tick)
			plt.imshow(im-np.median(im), vmin=-0.007, vmax=0.01, cmap='Greys')
			plt.scatter(chain['x'][-200+k,:], chain['y'][-200+k,:], s=1.5e4*chain['f'][0,-200+k,:], marker='+', color='r')
			plt.text(15, -2, 'Nsamp = '+str(chain['x'].shape[0]-200+k)+', Nsrc='+str(chain['n'][-200+k]), fontsize=20)
			tick += 1

		if resids:
			plt.subplot(1,n_panels, tick)
			plt.imshow(residz[-200+k,:,:], cmap='Greys', vmax=0.008, vmin=-0.005, origin='lower')
			tick += 1

		if color_color:
			ax3 = plt.subplot(1,n_panels, tick)
			asp = np.diff(ax3.get_xlim())[0] / np.diff(ax3.get_ylim())[0]
			ax3.set_aspect(asp)
			plt.scatter(chain['f'][1,-200+k,:]/chain['f'][0,-200+k,:], chain['f'][2,-200+k,:]/chain['f'][1,-200+k,:], s=1.5e4*chain['f'][0,-200+k,:], marker='x', c='k')
			plt.ylim(-0.5, 10.5)
			plt.xlim(-0.5, 10.5)

			plt.xlabel('$S_{350}/S_{250}$', fontsize=18)
			plt.ylabel('$S_{500}/S_{350}$', fontsize=18)


		plt.tight_layout()
		camera.snap()

	an = camera.animate()
	if gif_path is None:
		gif_path = 'pcat_sample_gif_'+timestr+'.gif'
	an.save(gif_path, writer='PillowWriter', fps=gif_fpr)


def plot_bkg_sample_chain(bkg_samples, band='250 micron', title=True, show=False, convert_to_MJy_sr_fac=None):

	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.
		ylabel_unit = ' [Jy/beam]'
	else:
		ylabel_unit = ' [MJy/sr]'

	f = plt.figure()
	if title:
		plt.title('Uniform background level - '+str(band))

	plt.plot(np.arange(len(bkg_samples)), bkg_samples/convert_to_MJy_sr_fac, label=band)
	plt.xlabel('Sample index')
	plt.ylabel('Background amplitude'+ylabel_unit)
	plt.legend()
	
	if show:
		plt.show()

	return f


def plot_bkg_sample_chain(bkg_samples, band='250 micron', title=True, show=False, convert_to_MJy_sr_fac=None, smooth_fac=None):

	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.
		ylabel_unit = ' [Jy/beam]'
	else:
		ylabel_unit = ' [MJy/sr]'

	f = plt.figure()
	if title:
		plt.title('Uniform background level - '+str(band))

	if smooth_fac is not None:
		bkg_samples = np.convolve(bkg_samples, np.ones((smooth_fac,))/smooth_fac, mode='valid')

	plt.plot(np.arange(len(bkg_samples)), bkg_samples/convert_to_MJy_sr_fac, label=band)
	plt.xlabel('Sample index')
	plt.ylabel('Amplitude'+ylabel_unit)
	plt.legend()
	
	if show:
		plt.show()

	return f

def plot_template_amplitude_sample_chain(template_samples, band='250 micron', template_name='sze', title=True, show=False, xlabel='Sample index', ylabel='Amplitude',\
									 convert_to_MJy_sr_fac=None, smooth_fac = None):

	ylabel_unit = None
	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.
		ylabel_unit = ' [Jy/beam]'
	else:
		ylabel_unit = ' [MJy/sr]'

	if template_name=='dust' or template_name == 'planck':
		ylabel_unit = None

	if smooth_fac is not None:
		template_samples = np.convolve(template_samples, np.ones((smooth_fac,))/smooth_fac, mode='valid')

	f = plt.figure()
	if title:
		plt.title(template_name +' template level - '+str(band))

	plt.plot(np.arange(len(template_samples)), template_samples, label=band)
	plt.xlabel(xlabel)
	plt.ylabel(ylabel)
	plt.legend()
	
	if show:
		plt.show()

	return f

def plot_template_median_std(template, template_samples, band='250 micron', template_name='cirrus dust', title=True, show=False, convert_to_MJy_sr_fac=None):


	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.
		xlabel_unit = ' [Jy/beam]'
	else:
		xlabel_unit = ' [MJy/sr]'

	f = plt.figure(figsize=(10, 5))

	if title:
		plt.suptitle(template_name)

	mean_t, std_t = np.mean(template_samples), np.std(template_samples)

	plt.subplot(1,2,1)
	plt.title('Median'+xlabel_unit)
	plt.imshow(mean_t*template/convert_to_MJy_sr_fac, origin='lower', cmap='Greys', interpolation=None, vmin=np.percentile(mean_t*template, 5)/convert_to_MJy_sr_fac, vmax=np.percentile(mean_t*template, 95)/convert_to_MJy_sr_fac)
	plt.colorbar()
	plt.subplot(1,2,2)
	plt.title('Standard deviation'+xlabel_unit)
	plt.imshow(std_t*np.abs(template)/convert_to_MJy_sr_fac, origin='lower', cmap='Greys', interpolation=None, vmin=np.percentile(std_t*np.abs(template), 5)/convert_to_MJy_sr_fac, vmax=np.percentile(std_t*np.abs(template), 95)/convert_to_MJy_sr_fac)
	plt.colorbar()

	if show:
		plt.show()
	return f

# fourier comps

def plot_fc_median_std(fourier_coeffs, imsz, ref_img=None, bkg_samples=None, fourier_templates=None, title=True, show=False, convert_to_MJy_sr_fac=None, psf_fwhm=None):
	
	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.
		xlabel_unit = ' [Jy/beam]'
	else:
		xlabel_unit = ' [MJy/sr]'

	n_terms = fourier_coeffs.shape[-2]

	all_temps = np.zeros((fourier_coeffs.shape[0], imsz[0], imsz[1]))
	if fourier_templates is None:
		fourier_templates = make_fourier_templates(imsz[0], imsz[1], n_terms, psf_fwhm=psf_fwhm)

	for i, fourier_coeff_state in enumerate(fourier_coeffs):
		all_temps[i] = generate_template(fourier_coeff_state, n_terms, fourier_templates=fourier_templates, N=imsz[0], M=imsz[1])
		if bkg_samples is not None:
			all_temps[i] += bkg_samples[i]

	mean_fc_temp = np.median(all_temps, axis=0)
	std_fc_temp = np.std(all_temps, axis=0)

	if ref_img is not None:
		f = plt.figure(figsize=(10, 10))
		if title:
			plt.suptitle('Best fit Fourier component model', y=1.02)

		plt.subplot(2,2,1)
		plt.title('Data')
		plt.imshow(ref_img/convert_to_MJy_sr_fac, origin='lower', cmap='Greys', interpolation=None, vmin=np.percentile(ref_img, 5)/convert_to_MJy_sr_fac, vmax=np.percentile(ref_img, 95)/convert_to_MJy_sr_fac)
		cb = plt.colorbar(orientation='horizontal')
		cb.set_label(xlabel_unit)
		plt.subplot(2,2,2)
		plt.title('Median background model')
		plt.imshow(mean_fc_temp/convert_to_MJy_sr_fac, origin='lower', cmap='Greys', interpolation=None, vmin=np.percentile(mean_fc_temp, 5)/convert_to_MJy_sr_fac, vmax=np.percentile(mean_fc_temp, 95)/convert_to_MJy_sr_fac)
		cb = plt.colorbar(orientation='horizontal')
		cb.set_label(xlabel_unit)		
		plt.subplot(2,2,3)
		plt.title('Data - median background model')
		plt.imshow((ref_img - mean_fc_temp)/convert_to_MJy_sr_fac, origin='lower', cmap='Greys', interpolation=None, vmin=np.percentile(ref_img, 5)/convert_to_MJy_sr_fac, vmax=np.percentile(ref_img, 95)/convert_to_MJy_sr_fac)
		# plt.imshow((ref_img - mean_fc_temp)/convert_to_MJy_sr_fac, origin='lower', cmap='Greys', interpolation=None, vmin=np.percentile(ref_img-mean_fc_temp, 5)/convert_to_MJy_sr_fac, vmax=np.percentile(ref_img-mean_fc_temp, 95)/convert_to_MJy_sr_fac)
		cb = plt.colorbar(orientation='horizontal')
		cb.set_label(xlabel_unit)
		plt.subplot(2,2,4)
		plt.title('Std. dev. of background model')
		plt.imshow(std_fc_temp/convert_to_MJy_sr_fac, origin='lower', cmap='Greys', interpolation=None, vmin=np.percentile(std_fc_temp, 5)/convert_to_MJy_sr_fac, vmax=np.percentile(std_fc_temp, 95)/convert_to_MJy_sr_fac)
		cb = plt.colorbar(orientation='horizontal')
		cb.set_label(xlabel_unit, fontsize='small')

	else:

		plt.subplot(1,2,1)
		plt.title('Median'+xlabel_unit)
		plt.imshow(mean_fc_temp/convert_to_MJy_sr_fac, origin='lower', cmap='Greys', interpolation=None, vmin=np.percentile(mean_fc_temp, 5)/convert_to_MJy_sr_fac, vmax=np.percentile(mean_fc_temp, 95)/convert_to_MJy_sr_fac)
		plt.colorbar()
		plt.subplot(1,2,2)
		plt.title('Standard deviation'+xlabel_unit)
		plt.imshow(std_fc_temp/convert_to_MJy_sr_fac, origin='lower', cmap='Greys', interpolation=None, vmin=np.percentile(std_fc_temp, 5)/convert_to_MJy_sr_fac, vmax=np.percentile(std_fc_temp, 95)/convert_to_MJy_sr_fac)
		plt.colorbar()

	plt.tight_layout()
	if show:
		plt.show()
	
	return f

def plot_last_fc_map(fourier_coeffs, imsz, ref_img=None, fourier_templates=None, title=True, show=False, convert_to_MJy_sr_fac=None, titlefontsize=18):
	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.
		xlabel_unit = ' [Jy/beam]'
	else:
		xlabel_unit = ' [MJy/sr]'

	n_terms = fourier_coeffs.shape[-2]


	if fourier_templates is None:
		fourier_templates = make_fourier_templates(imsz[0], imsz[1], n_terms)
	last_temp = generate_template(fourier_coeffs, n_terms, fourier_templates=fourier_templates, N=imsz[0], M=imsz[1])

	if ref_img is not None:
		f = plt.figure(figsize=(10, 5))
		plt.subplot(1,2,1)
		plt.title('Data', fontsize=titlefontsize)
		plt.imshow(ref_img, cmap='Greys', interpolation=None, vmin=np.percentile(ref_img, 5), vmax=np.percentile(ref_img, 95), origin='lower')
		plt.colorbar()
		plt.subplot(1,2,2)
		plt.title('Last fourier model realization', fontsize=titlefontsize)
		plt.imshow(last_temp/convert_to_MJy_sr_fac, cmap='Greys', interpolation=None, origin='lower', vmin=np.percentile(ref_img, 5), vmax=np.percentile(ref_img, 95))
		plt.colorbar()

	else:
		f = plt.figure()
		plt.title('Last fourier model realization', fontsize=titlefontsize)
		plt.imshow(last_temp/convert_to_MJy_sr_fac, cmap='Greys', interpolation=None, origin='lower')
		plt.colorbar()

	plt.tight_layout()
	if show:
		plt.show()

	return f


def plot_fourier_coeffs_covariance_matrix(fourier_coeffs, show=False):


	perkmode_data_matrix = np.mean(fourier_coeffs, axis=3)
	data_matrix = np.array([perkmode_data_matrix[i].ravel() for i in range(perkmode_data_matrix.shape[0])]).transpose()
	fc_covariance_matrix = np.cov(data_matrix)
	fc_corrcoef_matrix = np.corrcoef(data_matrix)
	f = plt.figure(figsize=(10,5))
	plt.subplot(1,2,1)
	plt.title('Covariance')
	plt.imshow(fc_covariance_matrix, vmin=np.percentile(fc_covariance_matrix, 5), vmax=np.percentile(fc_covariance_matrix, 95))
	plt.colorbar()
	plt.subplot(1,2,2)
	plt.title('Correlation coefficient')
	plt.imshow(fc_corrcoef_matrix, vmin=np.percentile(fc_corrcoef_matrix, 5), vmax=np.percentile(fc_corrcoef_matrix, 95))
	plt.colorbar()

	if show:
		plt.show()


	return f

def plot_fourier_coeffs_sample_chains(fourier_coeffs, show=False):
	
	norm = matplotlib.colors.Normalize(vmin=0, vmax=np.sqrt(2)*fourier_coeffs.shape[1])
	colormap = matplotlib.cm.ScalarMappable(norm=norm, cmap='jet')

	ravel_ks = [np.sqrt(i**2+j**2) for i in range(fourier_coeffs.shape[1]) for j in range(fourier_coeffs.shape[2])]

	colormap.set_array(ravel_ks/(np.sqrt(2)*fourier_coeffs.shape[1]))

	f, axes = plt.subplots(nrows=2, ncols=2, figsize=(10, 8))
	ax1, ax2, ax3, ax4 = axes.flatten()
	xvals = np.arange(fourier_coeffs.shape[0])

	for i in range(fourier_coeffs.shape[1]):
		for j in range(fourier_coeffs.shape[2]):
			ax1.plot(xvals, fourier_coeffs[:,i,j,0], alpha=0.5, linewidth=2, color=plt.cm.jet(np.sqrt(i**2+j**2)/(np.sqrt(2)*fourier_coeffs.shape[1])))
	ax1.set_xlabel('Thinned (post burn-in) samples')
	ax1.set_ylabel('$B_{ij,1}$', fontsize=18)

	for i in range(fourier_coeffs.shape[1]):
		for j in range(fourier_coeffs.shape[2]):
			ax2.plot(xvals, fourier_coeffs[:,i,j,1], alpha=0.5, linewidth=2, color=plt.cm.jet(np.sqrt(i**2+j**2)/(np.sqrt(2)*fourier_coeffs.shape[1])))
	ax2.set_xlabel('Thinned (post burn-in) samples')
	ax2.set_ylabel('$B_{ij,2}$', fontsize=18)

	for i in range(fourier_coeffs.shape[1]):
		for j in range(fourier_coeffs.shape[2]):
			ax3.plot(xvals, fourier_coeffs[:,i,j,2], alpha=0.5, linewidth=2, color=plt.cm.jet(np.sqrt(i**2+j**2)/(np.sqrt(2)*fourier_coeffs.shape[1])))
	ax3.set_xlabel('Thinned (post burn-in) samples')
	ax3.set_ylabel('$B_{ij,3}$', fontsize=18)

	for i in range(fourier_coeffs.shape[1]):
		for j in range(fourier_coeffs.shape[2]):
			ax4.plot(xvals, fourier_coeffs[:,i,j,3], alpha=0.5, linewidth=2, color=plt.cm.jet(np.sqrt(i**2+j**2)/(np.sqrt(2)*fourier_coeffs.shape[1])))
	ax4.set_xlabel('Thinned (post burn-in) samples')
	ax4.set_ylabel('$B_{ij,4}$', fontsize=18)

	f.colorbar(colormap, orientation='vertical', ax=ax1).set_label('$|k|$', fontsize=14)
	f.colorbar(colormap, orientation='vertical', ax=ax2).set_label('$|k|$', fontsize=14)
	f.colorbar(colormap, orientation='vertical', ax=ax3).set_label('$|k|$', fontsize=14)
	f.colorbar(colormap, orientation='vertical', ax=ax4).set_label('$|k|$', fontsize=14)


	plt.tight_layout()

	if show:
		plt.show()


	return f



def plot_posterior_fc_power_spectrum(fourier_coeffs, N, pixsize=6., show=False):

	n_terms = fourier_coeffs.shape[1]
	mesha, meshb = np.meshgrid(np.arange(1, n_terms+1) , np.arange(1, n_terms+1))
	kmags = np.sqrt(mesha**2+meshb**2)
	ps_bins = np.logspace(0, np.log10(n_terms+2), 6)

	twod_power_spectrum_realiz = []
	oned_ps_realiz = []
	kbin_masks = []
	for i in range(len(ps_bins)-1):
		kbinmask = (kmags >= ps_bins[i])*(kmags < ps_bins[i+1])
		kbin_masks.append(kbinmask)

	for i, fourier_coeff_state in enumerate(fourier_coeffs):
		av_2d_ps = np.mean(fourier_coeff_state**2, axis=2)
		oned_ps_realiz.append(np.array([np.mean(av_2d_ps[mask]) for mask in kbin_masks]))
		twod_power_spectrum_realiz.append(av_2d_ps)

	power_spectrum_realiz = np.array(twod_power_spectrum_realiz)
	oned_ps_realiz = np.array(oned_ps_realiz)


	f = plt.figure(figsize=(10, 5))
	plt.subplot(1,2,1)
	plt.imshow(np.median(power_spectrum_realiz, axis=0))
	plt.colorbar()
	plt.subplot(1,2,2)
	fov_in_rad = N*(pixsize/3600.)*(np.pi/180.)

	plt.errorbar(2*np.pi/(fov_in_rad/np.sqrt(ps_bins[1:]*ps_bins[:-1])), np.median(oned_ps_realiz,axis=0), yerr=np.std(oned_ps_realiz, axis=0))
	plt.xlabel('$2\\pi/\\theta$ [rad$^{-1}$]', fontsize=16)
	plt.ylabel('$C_{\\ell}$', fontsize=16)
	plt.yscale('log')
	plt.xscale('log')
	plt.tight_layout()
	if show:
		plt.show()

	return f

# TODO -- this will show whether the posteriors are converged on the coefficients
# def plot_fourier_coeff_posteriors(fourier_coeffs):
# 	f = plt.figure()

# 	return f


def plot_posterior_bkg_amplitude(bkg_samples, band='250 micron', title=True, show=False, xlabel='Amplitude', convert_to_MJy_sr_fac=None):
	
	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.
		xlabel_unit = ' [Jy/beam]'
	else:
		xlabel_unit = ' [MJy/sr]'

	f = plt.figure()
	if title:
		plt.title('Uniform background level - '+str(band))
		
	if len(bkg_samples)>50:
		binz = scotts_rule_bins(bkg_samples/convert_to_MJy_sr_fac)
	else:
		binz = 10

	plt.hist(np.array(bkg_samples)/convert_to_MJy_sr_fac, label=band, histtype='step', bins=binz)
	plt.xlabel(xlabel+xlabel_unit)
	plt.ylabel('$N_{samp}$')
	
	if show:
		plt.show()

	return f    

def plot_posterior_template_amplitude(template_samples, band='250 micron', template_name='sze', title=True, show=False, xlabel='Amplitude', convert_to_MJy_sr_fac=None, \
									mock_truth=None, xlabel_unit=None):
	
	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.

		if xlabel_unit is None:
			xlabel_unit = ' [Jy/beam]'
	else:
		if xlabel_unit is None:
			xlabel_unit = ' [MJy/sr]'

	if template_name=='dust' or template_name == 'planck':
		xlabel_unit = ''

	f = plt.figure()
	if title:
		plt.title(template_name +' template level - '+str(band))

	if len(template_samples)>50:
		binz = scotts_rule_bins(template_samples/convert_to_MJy_sr_fac)
	else:
		binz = 10
	plt.hist(np.array(template_samples)/convert_to_MJy_sr_fac, label=band, histtype='step', bins=binz)
	if mock_truth is not None:
		plt.axvline(mock_truth, linestyle='dashdot', color='r', label='Mock truth')
		plt.legend()
	plt.xlabel(xlabel+xlabel_unit)
	plt.ylabel('$N_{samp}$')
	
	if show:
		plt.show()

	return f


def plot_posterior_flux_dist(logSv, raw_number_counts, band='250 micron', title=True, show=False):

	mean_number_cts = np.mean(raw_number_counts, axis=0)
	lower = np.percentile(raw_number_counts, 16, axis=0)
	upper = np.percentile(raw_number_counts, 84, axis=0)
	f = plt.figure()
	if title:
		plt.title('Posterior Flux Density Distribution - ' +str(band))

	plt.errorbar(logSv+3, mean_number_cts, yerr=np.array([np.abs(mean_number_cts-lower), np.abs(upper - mean_number_cts)]),fmt='.', label='Posterior')
	
	plt.legend()
	plt.yscale('log', nonposy='clip')
	plt.xlabel('log10(Flux density) - ' + str(band))
	plt.ylim(5e-1, 5e2)

	if show:
		plt.show()

	return f


def plot_posterior_number_counts(logSv, lit_number_counts, trueminf=0.001, band='250 micron', title=True, show=False):

	mean_number_cts = np.mean(lit_number_counts, axis=0)
	lower = np.percentile(lit_number_counts, 16, axis=0)
	upper = np.percentile(lit_number_counts, 84, axis=0)
	f = plt.figure()
	if title:
		plt.title('Posterior Flux Density Distribution - ' +str(band))

	plt.errorbar(logSv+3, mean_number_cts, yerr=np.array([np.abs(mean_number_cts-lower), np.abs(upper - mean_number_cts)]), marker='.', label='Posterior')
	
	plt.yscale('log')
	plt.legend()
	plt.xlabel('log($S_{\\nu}$) (mJy)')
	plt.ylabel('dN/dS.$S^{2.5}$ ($Jy^{1.5}/sr$)')
	plt.ylim(1e-1, 1e5)
	plt.xlim(np.log10(trueminf)+3.-0.5-1.0, 2.5)
	plt.tight_layout()

	if show:
		plt.show()


	return f



def plot_flux_color_posterior(fsrcs, colors, band_strs, title='Posterior Flux-density Color Distribution', titlefontsize=14, show=False, xmin=0.005, xmax=4e-1, ymin=1e-2, ymax=40, fmin=0.005, colormax=40, \
								flux_sizes=None):

	print('fmin here is', fmin)
	
	xlims=[xmin, xmax]
	ylims=[ymin, ymax]

	f_str = band_strs[0]
	col_str = band_strs[1]

	nanmask = ~np.isnan(colors)

	if flux_sizes is not None:
		zeromask = (flux_sizes > fmin)
	else:
		zeromask = (fsrcs > fmin)

	colormask = (colors < colormax)

	print('lennanmask:', len(nanmask))
	print('zeromask:', zeromask)

	print('sums are ', np.sum(nanmask), np.sum(zeromask), np.sum(colormask))

	f = plt.figure()
	if title:
		plt.title(title, fontsize=titlefontsize)

	if flux_sizes is not None:
		pt_sizes = (2e2*flux_sizes[nanmask*zeromask*colormask])**2
		print('pt sizes heere is ', pt_sizes)
		c = np.log10(flux_sizes[nanmask*zeromask*colormask])

		print('minimum c is ', np.min(flux_sizes[nanmask*zeromask*colormask]))
		# c = flux_sizes[nanmask*zeromask*colormask]

		alpha=0.1

		ylims = [0, 3.0]
		xlims = [0, 3.0]

	else:
		pt_sizes = 10
		c = 'k'
		alpha=0.01


	# bright_src_mask = (flux_sizes > 0.05)
	# not_bright_src_mask = ~bright_src_mask

	if flux_sizes is not None:
		# plt.scatter(colors[nanmask*zeromask*colormask*not_bright_src_mask], fsrcs[nanmask*zeromask*colormask*not_bright_src_mask], alpha=alpha, c=np.log10(flux_sizes[nanmask*zeromask*colormask*not_bright_src_mask]), s=(2e2*flux_sizes[nanmask*zeromask*colormask*not_bright_src_mask])**2, marker='+', label='PCAT ($F_{250} > 5$ mJy')
		# plt.scatter(colors[nanmask*zeromask*colormask*bright_src_mask], fsrcs[nanmask*zeromask*colormask*bright_src_mask], alpha=0.5, c=np.log10(flux_sizes[nanmask*zeromask*colormask*bright_src_mask]), s=(2e2*flux_sizes[nanmask*zeromask*colormask*bright_src_mask])**2, marker='+')
		plt.scatter(colors[nanmask*zeromask*colormask], fsrcs[nanmask*zeromask*colormask], alpha=alpha, c=c, s=pt_sizes, marker='.', label='PCAT ($F_{250} > 5$ mJy)')

	else:
		plt.scatter(colors[nanmask*zeromask*colormask], fsrcs[nanmask*zeromask*colormask], alpha=alpha, c=c, cmap='viridis_r', s=pt_sizes, marker='+', label='PCAT ($F_{250} > 5$ mJy)')


	if flux_sizes is not None:

		plt.scatter(0.*colors[nanmask*zeromask*colormask], fsrcs[nanmask*zeromask*colormask], alpha=1.0, c=c, s=pt_sizes, marker='+')

		cbar = plt.colorbar()
		cbar.ax.set_ylabel("$\\log_{10} S_{250}\\mu m$")
	plt.ylabel(f_str, fontsize=14)
	plt.xlabel(col_str, fontsize=14)

	plt.ylim(ylims)
	plt.xlim(xlims)

	if flux_sizes is None:
		plt.yscale('log')
		plt.xscale('log')
		plt.xlim(0, 5)

	plt.legend()

	if show:
		plt.show()

	return f

def plot_color_posterior(fsrcs, band0, band1, lam_dict, mock_truth_fluxes=None, title=True, titlefontsize=14, show=False):

	f = plt.figure()
	if title:
		plt.title('Posterior Color Distribution', fontsize=titlefontsize)

	_, bins, _ = plt.hist(fsrcs[band0].ravel()/fsrcs[band1].ravel(), histtype='step', label='Posterior', bins=np.linspace(0.01, 5, 50), density=True)
	if mock_truth_fluxes is not None:
		plt.hist(mock_truth_fluxes[band0,:].ravel()/mock_truth_fluxes[band1,:].ravel(), bins=bins, density=True, histtype='step', label='Mock Truth')

	plt.legend()
	plt.ylabel('PDF')
	plt.xlabel('$S_{'+str(lam_dict[band0])+'}\\mu m/S_{'+str(lam_dict[band1])+'} \\mu m$', fontsize=14)

	if show:
		plt.show()


	return f


def plot_residual_map(resid, mode='median', band='S', titlefontsize=14, smooth=True, smooth_sigma=3, \
					minmax_smooth=None, minmax=None, show=False, plot_refcat=False, convert_to_MJy_sr_fac=None):


	# TODO - overplot reference catalog on image

	if minmax_smooth is None:
		minmax_smooth = [-0.005, 0.005]
		minmax = [-0.005, 0.005]

	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.
		title_unit = ' [Jy/beam]'
	else:
		title_unit = ' [MJy/sr]'

	minmax_smooth = np.array(minmax_smooth)/convert_to_MJy_sr_fac
	minmax = np.array(minmax)/convert_to_MJy_sr_fac

	if mode=='median':
		title_mode = 'Median residual'
	elif mode=='last':
		title_mode = 'Last residual'

	if smooth:
		f = plt.figure(figsize=(10, 5))
	else:
		f = plt.figure(figsize=(8,8))
	
	if smooth:
		plt.subplot(1,2,1)

	plt.title(title_mode+' -- '+band+title_unit, fontsize=titlefontsize)
	plt.imshow(resid/convert_to_MJy_sr_fac, cmap='Greys', interpolation=None, vmin=minmax[0], vmax=minmax[1], origin='lower')
	plt.colorbar()

	if smooth:
		plt.subplot(1,2,2)
		plt.title('Smoothed Residual'+title_unit, fontsize=titlefontsize)
		plt.imshow(gaussian_filter(resid, sigma=smooth_sigma)/convert_to_MJy_sr_fac, interpolation=None, cmap='Greys', vmin=minmax_smooth[0], vmax=minmax_smooth[1], origin='lower')
		plt.colorbar()

	if show:
		plt.show()


	return f

def plot_residual_1pt_function(resid, mode='median', band='S', noise_model=None, show=False, binmin=-0.02, binmax=0.02, nbin=50, convert_to_MJy_sr_fac=None):

	if noise_model is not None:
		noise_model *= np.random.normal(0, 1, noise_model.shape)
		density=True
	else:
		density=False



	if convert_to_MJy_sr_fac is None:
		convert_to_MJy_sr_fac = 1.
		xlabel_unit = '[Jy/beam]'
	else:
		xlabel_unit = '[MJy/sr]'
		binmin /= convert_to_MJy_sr_fac
		binmax /= convert_to_MJy_sr_fac

	if len(resid.shape) > 1:
		median_resid_rav = resid.ravel()/convert_to_MJy_sr_fac
	else:
		median_resid_rav = resid/convert_to_MJy_sr_fac

	if mode=='median':
		title_mode = 'Median residual'
	elif mode=='last':
		title_mode = 'Last residual'
	
	f = plt.figure()
	plt.title(title_mode+' 1pt function -- '+band)
	plt.hist(median_resid_rav, bins=np.linspace(binmin, binmax, nbin), histtype='step', density=density)

	if noise_model is not None:
		plt.hist(noise_model.ravel(), bins=np.linspace(binmin, binmax, nbin), histtype='step', color='r', label='Noise model (Gaussian draw)', density=density)

	plt.axvline(np.median(median_resid_rav), label='Median='+str(np.round(np.median(median_resid_rav), 5))+'\n $\\sigma=$'+str(np.round(np.std(median_resid_rav), 5)))
	plt.legend(frameon=False)

	if density:
		plt.ylabel('PDF')
	else:
		plt.ylabel('$N_{pix}$')

	plt.xlabel('data - model '+xlabel_unit)

	if show:
		plt.show()

	return f


def plot_chi_squared(chi2, sample_number, band='S', show=False):

	burn_in = sample_number[0]
	f = plt.figure()
	plt.plot(sample_number, chi2[burn_in:], label=band)
	plt.axhline(np.min(chi2[burn_in:]), linestyle='dashed',alpha=0.5, label=str(np.min(chi2[burn_in:]))+' (' + str(band) + ')')
	plt.xlabel('Sample')
	plt.ylabel('Chi-Squared')
	plt.legend()
	
	if show:
		plt.show()

	return f


def plot_comp_resources(timestats, nsamp, labels=['Proposal', 'Likelihood', 'Implement'], show=False):
	time_array = np.zeros(3, dtype=np.float32)
	
	for samp in range(nsamp):
		time_array += np.array([timestats[samp][2][0], timestats[samp][3][0], timestats[samp][4][0]])
	
	f = plt.figure()
	plt.title('Computational Resources')
	plt.pie(time_array, labels=labels, autopct='%1.1f%%', shadow=True)
	
	if show:
		plt.show()
	
	return f

def plot_acceptance_fractions(accept_stats, proposal_types=['All', 'Move', 'Birth/Death', 'Merge/Split', 'Templates'], show=False, smooth_fac=None):

	f = plt.figure()
	
	samp_range = np.arange(accept_stats.shape[0])
	for x in range(len(proposal_types)):
		print(accept_stats[0,x])
		accept_stats[:,x][np.isnan(accept_stats[:,x])] = 0.

	# if smooth_fac is not None:
		# bkg_samples = np.convolve(bkg_samples, np.ones((smooth_fac,))/smooth_fac, mode='valid')
		if smooth_fac is not None:
			accept_stat_chain = np.convolve(accept_stats[:,x], np.ones((smooth_fac,))/smooth_fac, mode='valid')
		else:
			accept_stat_chain = accept_stats[:,x]
		# plt.plot(samp_range, accept_stats[:,x], label=proposal_types[x])

		plt.plot(np.arange(len(accept_stat_chain)), accept_stat_chain, label=proposal_types[x])
	plt.legend()
	plt.xlabel('Sample number')
	plt.ylabel('Acceptance fraction')
	if show:
		plt.show()

	return f


def plot_src_number_posterior(nsrc_fov, show=False, title=False):

	f = plt.figure()
	
	if title:
		plt.title('Posterior Source Number Histogram')
	
	plt.hist(nsrc_fov, histtype='step', label='Posterior', color='b', bins=15)
	plt.axvline(np.median(nsrc_fov), label='Median=' + str(np.median(nsrc_fov)), color='b', linestyle='dashed')
	plt.xlabel('$N_{src}$', fontsize=16)
	plt.ylabel('Number of samples', fontsize=16)
	plt.legend()
		
	if show:
		plt.show()
	
	return f


def plot_src_number_trace(nsrc_fov, show=False, title=False):

	f = plt.figure()
	
	if title:
		plt.title('Source number trace plot (post burn-in)')
	
	plt.plot(np.arange(len(nsrc_fov)), nsrc_fov)

	plt.xlabel('Sample index', fontsize=16)
	plt.ylabel('$N_{src}$', fontsize=16)
	plt.legend()
	
	if show:
		plt.show()

	return f



def plot_grap(verbtype=0):

	'''
	Makes plot of probabilistic graphical model for SPIRE
	'''
		
	figr, axis = plt.subplots(figsize=(6, 6))

	grap = nx.DiGraph()   
	grap.add_edges_from([('muS', 'svec'), ('sigS', 'svec'), ('alpha', 'f0'), ('beta', 'nsrc')])
	grap.add_edges_from([('back', 'modl'), ('xvec', 'modl'), ('f0', 'modl'), ('svec', 'modl'), ('PSF', 'modl'), ('ASZ', 'modl')])
	grap.add_edges_from([('modl', 'data')])
	listcolr = ['black' for i in range(7)]
	
	labl = {}

	nameelem = r'\rm{pts}'


	labl['beta'] = r'$\beta$'
	labl['alpha'] = r'$\alpha$'
	labl['muS'] = r'$\vec{\mu}_S$'
	labl['sigS'] = r'$\vec{\sigma}_S$'
	labl['xvec'] = r'$\vec{x}$'
	labl['f0'] = r'$F_0$'
	labl['svec'] = r'$\vec{s}$'
	labl['PSF'] = r'PSF'
	labl['modl'] = r'$M_D$'
	labl['data'] = r'$D$'
	labl['back'] = r'$\vec{A_{sky}}$'
	labl['nsrc'] = r'$N_{src}$'
	labl['ASZ'] = r'$\vec{A_{SZ}}$'
	
	
	posi = nx.circular_layout(grap)
	posi['alpha'] = np.array([-0.025, 0.15])
	posi['muS'] = np.array([0.025, 0.15])
	posi['sigS'] = np.array([0.075, 0.15])
	posi['beta'] = np.array([0.12, 0.15])

	posi['xvec'] = np.array([-0.075, 0.05])
	posi['f0'] = np.array([-0.025, 0.05])
	posi['svec'] = np.array([0.025, 0.05])
	posi['PSF'] = np.array([0.07, 0.05])
	posi['back'] = np.array([-0.125, 0.05])
	
	posi['modl'] = np.array([-0.05, -0.05])
	posi['data'] = np.array([-0.05, -0.1])
	posi['nsrc'] = np.array([0.08, 0.01])
	
	posi['ASZ'] = np.array([-0.175, 0.05])


	rect = patches.Rectangle((-0.10,0.105),0.2,-0.11,linewidth=2, facecolor='none', edgecolor='k')

	axis.add_patch(rect)

	size = 1000
	nx.draw(grap, posi, labels=labl, ax=axis, edgelist=grap.edges())
	nx.draw_networkx_nodes(grap, posi, ax=axis, labels=labl, nodelist=['nsrc'], node_color='white', node_size=500)

	nx.draw_networkx_nodes(grap, posi, ax=axis, labels=labl, nodelist=['modl'], node_color='xkcd:sky blue', node_size=1000)
	nx.draw_networkx_nodes(grap, posi, ax=axis, labels=labl, nodelist=['beta'], node_shape='d', node_color='y', node_size=size)
	
	nx.draw_networkx_nodes(grap, posi, ax=axis, labels=labl, nodelist=['data'],  node_color='grey', node_shape='s', node_size=size)
	nx.draw_networkx_nodes(grap, posi, ax=axis, labels=labl, nodelist=['xvec', 'f0', 'svec'], node_color='orange', node_size=size)
	nx.draw_networkx_nodes(grap, posi, ax=axis, labels=labl, nodelist=['PSF'], node_shape='d', node_color='orange', node_size=size)
	
	nx.draw_networkx_nodes(grap, posi, ax=axis, labels=labl, nodelist=['back'], node_color='orange', node_size=size)
	
	nx.draw_networkx_nodes(grap, posi, ax=axis, labels=labl, nodelist=['ASZ'], node_color='violet', node_size=size)

	nx.draw_networkx_nodes(grap, posi, ax=axis, labels=labl, nodelist=['alpha', 'muS', 'sigS'], node_shape='d', node_color='y', node_size=size)

	
	plt.tight_layout()
	plt.show()
	
	return figr

def grab_atcr(timestr, paramstr='template_amplitudes', band=0, result_dir=None, nsamp=500, template_idx=0, return_fig=True):
	
	band_dict = dict({0:'250 micron', 1:'350 micron', 2:'500 micron'})
	lam_dict = dict({0:250, 1:350, 2:500})

	if result_dir is None:
		result_dir = '/Users/richardfeder/Documents/multiband_pcat/spire_results/'
		print('Result directory assumed to be '+result_dir)
		
	chain = np.load(result_dir+str(timestr)+'/chain.npz')
	if paramstr=='template_amplitudes':
		listsamp = chain[paramstr][-nsamp:, band, template_idx]
	else:
		listsamp = chain[paramstr][-nsamp:, band]
		
	f = plot_atcr(listsamp, title=paramstr+', '+band_dict[band])

	if return_fig:
		return f


	



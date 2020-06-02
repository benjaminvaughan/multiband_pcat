from fast_astrom import *
import numpy as np
from astropy.convolution import Gaussian2DKernel
from image_eval import psf_poly_fit, image_model_eval
import pickle
import matplotlib
import matplotlib.pyplot as plt

class objectview(object):
	def __init__(self, d):
		self.__dict__ = d

def get_gaussian_psf_template_3_5_20(pixel_fwhm = 3., nbin=5):
	nc = nbin**2
	psfnew = Gaussian2DKernel((pixel_fwhm/2.355)*nbin, x_size=125, y_size=125).array.astype(np.float32)
	cf = psf_poly_fit(psfnew, nbin=nbin)
	return psfnew, cf, nc, nbin

def get_gaussian_psf_template(pixel_fwhm=3., nbin=5, normalization='max'):
	nc = 25
	psfnew = Gaussian2DKernel((pixel_fwhm/2.355)*nbin, x_size=125, y_size=125).array.astype(np.float32)
	print('psfmax is ', np.max(psfnew))

	if normalization == 'max':
		print('Normalizing PSF by kernel maximum')
		psfnew /= np.max(psfnew)
		psfnew /= 4*np.pi*(pixel_fwhm/2.355)**2
	else:
		print('Normalizing PSF by kernel sum')
		psfnew *= nc
	cf = psf_poly_fit(psfnew, nbin=nbin)
	return psfnew, cf, nc, nbin


def load_in_map(gdat, band=0, astrom=None):

	if gdat.file_path is None:
		# file_path = gdat.data_path+gdat.dataname+'/'+gdat.dataname+'_'+gdat.tail_name+'.fits'
		file_path = gdat.data_path+gdat.dataname+'/'+gdat.tail_name+'.fits'

	else:
		file_path = gdat.file_path

	print('band is ', gdat.band_dict[band])
	file_path = file_path.replace('PSW', 'P'+str(gdat.band_dict[band])+'W')


	print('file_path:', file_path)

	if astrom is not None:
		print('loading from ', gdat.band_dict[band])
		astrom.load_wcs_header_and_dim(file_path)

	spire_dat = fits.open(file_path)

	image = np.nan_to_num(spire_dat[0].data)
	# error = np.nan_to_num(spire_dat[1].data)
	# exposure = spire_dat[2].data
	# mask = spire_dat[3].data
	error = np.nan_to_num(spire_dat[2].data) # temporary for sims_for_richard dataset
	exposure = spire_dat[3].data
	mask = spire_dat[4].data

	# plt.figure()
	# plt.title('early mask')
	# plt.imshow(mask)
	# plt.show()

	print(get_rect_mask_bounds(mask))


	# image = np.nan_to_num(spire_dat[1].data)
	# error = np.nan_to_num(spire_dat[2].data)
	# exposure = spire_dat[3].data

	# temporary file grab while bolocam mask is not part of .fits file
	# if gdat.bolocam_mask:
	# 	print('loading bolocam mask temporarily as separate file..')
	# 	mask_fits = fits.open(gdat.data_path+'bolocam_mask_P'+str(gdat.band_dict[band])+'W.fits')
	# 	mask = mask_fits[0].data
	# else:
	# 	mask = spire_dat[4].data

	return image, error, exposure, mask, file_path


def load_param_dict(timestr, result_path='/Users/luminatech/Documents/multiband_pcat/spire_results/'):
	
	filepath = result_path + timestr
	filen = open(filepath+'/params.txt','rb')
	print('filename is ', filen)
	pdict = pickle.load(filen)
	print(pdict)
	opt = objectview(pdict)

	print('param dict load')
	return opt, filepath, result_path


def get_rect_mask_bounds(mask):
	''' this function assumes the mask is rectangular in shape, with ones in the desired region and zero otherwise. '''

	idxs = np.argwhere(mask == 1.0)
	bounds = np.array([[np.min(idxs[:,0]), np.max(idxs[:,0])], [np.min(idxs[:,1]), np.max(idxs[:,1])]])

	return bounds


''' This class sets up the data structures for data/data-related information. 
load_in_data() loads in data, generates the PSF template and computes weights from the noise model
'''
class pcat_data():

	template_bands = dict({'sze':['M', 'L'], 'lensing':['S', 'M', 'L']})

	def __init__(self, auto_resize=False, nregion=1):
		self.ncs = []
		self.nbins = []
		self.psfs = []
		self.cfs = []
		self.biases = []
		self.data_array = []
		self.weights = []
		self.masks = []
		self.exposures = []
		self.errors = []
		self.fast_astrom = wcs_astrometry(auto_resize, nregion=nregion)
		self.widths = []
		self.heights = []
		self.fracs = []
		self.template_array = []

	def load_in_data(self, gdat, map_object=None, tail_name=None):

		gdat.imszs = []
		gdat.regsizes = []
		gdat.margins = []
		gdat.bounds = []

		for i, band in enumerate(gdat.bands):
			print('band:', band)

			if map_object is not None:

				obj = map_object[band]
				image = np.nan_to_num(obj['signal'])
				error = np.nan_to_num(obj['error'])

				exposure = obj['exp'].data
				mask = obj['mask']
				gdat.psf_pixel_fwhm = obj['widtha']/obj['pixsize']# gives it in arcseconds and neet to convert to pixels
				self.fast_astrom.load_wcs_header_and_dim(head=obj['shead'], round_up_or_down=gdat.round_up_or_down)
				gdat.dataname = obj['name']
				print('gdat.dataname:', gdat.dataname)
				if i > 0:
					self.fast_astrom.fit_astrom_arrays(0, i)


			elif gdat.mock_name is None:

				image, error, exposure, mask, file_name = load_in_map(gdat, band, astrom=self.fast_astrom)

				# plt.figure()
				# plt.title('mask')
				# plt.imshow(mask)
				# plt.show()


				# plt.figure()
				# plt.title('imaage')
				# plt.imshow(image)
				# plt.show()
				bounds = get_rect_mask_bounds(mask) if gdat.bolocam_mask else None

				# plt.figure()
				# plt.title('mask')
				# plt.imshow(mask)
				# plt.show()


				print('bounds for band ', i, 'are ', bounds)

				if bounds is not None:
					if gdat.round_up_or_down == 'up':
						big_dim = np.maximum(find_nearest_upper_mod(bounds[0,1]-bounds[0,0], gdat.nregion), find_nearest_upper_mod(bounds[1,1]-bounds[1,0], gdat.nregion))
					else:
						big_dim = np.maximum(find_lowest_mod(bounds[0,1]-bounds[0,0], gdat.nregion), find_lowest_mod(bounds[1,1]-bounds[1,0], gdat.nregion))


					print('big dim at thiiiiis point is ', big_dim)
					self.fast_astrom.dims[i] = (big_dim, big_dim)


				gdat.bounds.append(bounds)

				template_list = [] 

				temp_mock_amps = [None, 0.3, 0.5] # MJy/sr
				flux_density_conversion_facs = [86.29e-4, 16.65e-3, 34.52e-3]

				if gdat.n_templates > 0:

					for t, template_name in enumerate(gdat.template_names):
						print('template name is ', template_name)
						if gdat.band_dict[band] in self.template_bands[template_name]:
							print('were in business, ', gdat.band_dict[band], self.template_bands[template_name])

							if gdat.template_filename is not None:
								temp_name = gdat.template_filename[t]
								template_file_name = temp_name.replace('PSW', 'P'+str(gdat.band_dict[band])+'W')

							else:
								template_file_name = file_name.replace('.fits', '_'+template_name+'.fits')
							
							print('template file name is ', template_file_name)

							template = fits.open(template_file_name)[0].data



							if gdat.inject_sz_frac > 0.:
								print('injecting SZ frac of ', gdat.inject_sz_frac)

								plt.figure()
								plt.title('template here, injected amplitude is '+str(gdat.inject_sz_frac*temp_mock_amps[i]*flux_density_conversion_facs[i]))
								plt.imshow(template, origin=[0,0])
								plt.colorbar()
								plt.show()


								image += gdat.inject_sz_frac*template*temp_mock_amps[i]*flux_density_conversion_facs[i]

								plt.figure()
								plt.title('image here ')
								plt.imshow(image, origin=[0,0])
								plt.colorbar()
								plt.show()


						else:

							template = None

						template_list.append(template)


				if i > 0:
					print('we have more than one band:', gdat.bands[0], band)
					self.fast_astrom.fit_astrom_arrays(0, i, bounds0=gdat.bounds[0], bounds1=gdat.bounds[i])


				if gdat.noise_thresholds is not None:
					error[error > gdat.noise_thresholds[i]] = 0 # this equates to downweighting the pixels


			else:
				image, error, exposure, mask = load_in_mock_map(gdat.mock_name, band)
			
			if gdat.auto_resize:

				if gdat.bolocam_mask:

					error = error[bounds[0,0]:bounds[0,1], bounds[1,0]:bounds[1,1]]
					image = image[bounds[0,0]:bounds[0,1], bounds[1,0]:bounds[1,1]]
					exposure = exposure[bounds[0,0]:bounds[0,1], bounds[1,0]:bounds[1,1]]
					smaller_dim = np.min(image.shape)
					larger_dim = np.max(image.shape)

				else:

					smaller_dim = np.min([image.shape[0]-gdat.x0, image.shape[1]-gdat.y0]) # option to include lower left corner
					larger_dim = np.max([image.shape[0]-gdat.x0, image.shape[1]-gdat.y0])

				print('smaller dim is', smaller_dim)
				print('larger dim is ', larger_dim)
				
				if gdat.round_up_or_down=='up':
					gdat.width = find_nearest_upper_mod(larger_dim, gdat.nregion)
				else:
					gdat.width = find_lowest_mod(smaller_dim, gdat.nregion)
				
				gdat.height = gdat.width
				image_size = (gdat.width, gdat.height)

				resized_image = np.zeros(shape=(gdat.width, gdat.height))
				resized_error = np.zeros(shape=(gdat.width, gdat.height))
				resized_exposure = np.zeros(shape=(gdat.width, gdat.height))
				resized_mask = np.zeros(shape=(gdat.width, gdat.height))


				crop_size_x = np.minimum(gdat.width, image.shape[0])
				crop_size_y = np.minimum(gdat.height, image.shape[1])


				resized_image[:image.shape[0]-gdat.x0, : image.shape[1]-gdat.y0] = image[gdat.x0:crop_size_x, gdat.y0:crop_size_y]
				resized_error[:image.shape[0]-gdat.x0, : image.shape[1]-gdat.y0] = error[gdat.x0:crop_size_x, gdat.y0:crop_size_y]
				resized_exposure[:image.shape[0]-gdat.x0, : image.shape[1]-gdat.y0] = exposure[gdat.x0:crop_size_x, gdat.y0:crop_size_y]

				resized_template_list = []
				for template in template_list:
					if template is not None:

						resized_template = np.zeros(shape=(gdat.width, gdat.height))

						if gdat.bolocam_mask:
							template = template[bounds[0,0]:bounds[0,1], bounds[1,0]:bounds[1,1]]


						resized_template[:image.shape[0]-gdat.x0, : image.shape[1]-gdat.y0] = template[gdat.x0:crop_size_x, gdat.y0:crop_size_y]

						resized_template_list.append(resized_template.astype(np.float32))
					else:
						resized_template_list.append(None)


				variance = resized_error**2

				variance[variance==0.]=np.inf
				weight = 1. / variance

				self.weights.append(weight.astype(np.float32))
				self.errors.append(resized_error.astype(np.float32))
				self.data_array.append(resized_image.astype(np.float32)-gdat.mean_offsets[i]) # constant offset, will need to change
				self.exposures.append(resized_exposure.astype(np.float32))
				self.template_array.append(resized_template_list)


				# print(self.template_array)
				# if i==1:
				# 	plt.figure()
				# 	plt.title('template')
				# 	plt.imshow(self.template_array[i-1][0], origin=[0,0], cmap='Greys')
				# 	plt.show()


			elif gdat.width > 0:
				print('were here now')
				image = image[gdat.x0:gdat.x0+gdat.width,gdat.y0:gdat.y0+gdat.height]
				error = error[gdat.x0:gdat.x0+gdat.width,gdat.y0:gdat.y0+gdat.height]
				exposure = exposure[gdat.x0:gdat.x0+gdat.width,gdat.y0:gdat.y0+gdat.height]
				cropped_template_list = []
				for template in template_list:
					if template is not None:
						cropped_template = template[gdat.x0:gdat.x0+gdat.width, gdat.y0:gdat.y0+gdat.height]
						cropped_template /= np.max(cropped_template)

						print('cropped_template here has sum ', np.max(cropped_template))
						cropped_template_list.append(cropped_template.astype(np.float32))
					else:
						cropped_template_list.append(None)
				
				image_size = (gdat.width, gdat.height)
				variance = error**2
				variance[variance==0.]=np.inf
				weight = 1. / variance

				
				self.weights.append(weight.astype(np.float32))
				self.errors.append(error.astype(np.float32))
				self.data_array.append(image.astype(np.float32)-gdat.mean_offsets[i]) # constant offset, will need to change
				self.exposures.append(exposure.astype(np.float32))
				self.template_array.append(cropped_template_list)

			else:
				image_size = (image.shape[0], image.shape[1])
				variance = error**2
				variance[variance==0.]=np.inf
				weight = 1. / variance

				self.weights.append(weight.astype(np.float32))
				self.errors.append(error.astype(np.float32))
				self.data_array.append(image.astype(np.float32)-gdat.mean_offsets[i]) 
				self.exposures.append(exposure.astype(np.float32))

				self.template_array.append(template_list)



			if i==0:
				gdat.imsz0 = image_size

			
			# plt.figure()
			# plt.title('data')
			# plt.imshow(self.data_array[i], cmap='Greys', origin=[0,0])
			# plt.colorbar()
			# plt.show()

			# plt.figure()
			# plt.title('errors')
			# plt.imshow(self.errors[i], cmap='Greys', origin=[0,0])
			# plt.colorbar()
			# plt.show()

			gdat.imszs.append(image_size)
			gdat.regsizes.append(image_size[0]/gdat.nregion)

			print('image maximum is ', np.max(self.data_array[0]))

			gdat.frac = np.count_nonzero(weight)/float(gdat.width*gdat.height)
			print('gdat.frac is ', gdat.frac)
			# psf, cf, nc, nbin = get_gaussian_psf_template(pixel_fwhm=gdat.psf_pixel_fwhm, normalization=gdat.normalization)
			psf, cf, nc, nbin = get_gaussian_psf_template_3_5_20(pixel_fwhm=gdat.psf_pixel_fwhm)

			print('sum of PSF is ', np.sum(psf))
			self.psfs.append(psf)
			self.cfs.append(cf)
			self.ncs.append(nc)
			self.nbins.append(nbin)
			self.biases.append(gdat.bias)
			self.fracs.append(gdat.frac)




		gdat.regions_factor = 1./float(gdat.nregion**2)
		print(gdat.imsz0[0], gdat.regsizes[0], gdat.regions_factor)
		assert gdat.imsz0[0] % gdat.regsizes[0] == 0 
		assert gdat.imsz0[1] % gdat.regsizes[0] == 0 

		pixel_variance = np.median(self.errors[0]**2)
		print('pixel_variance:', pixel_variance)
		print('self.dat.fracs is ', self.fracs)
		gdat.N_eff = 4*np.pi*(gdat.psf_pixel_fwhm/2.355)**2 # 2 instead of 4 for spire beam size
		gdat.err_f = np.sqrt(gdat.N_eff * pixel_variance)/10



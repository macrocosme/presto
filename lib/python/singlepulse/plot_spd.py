#! /usr/bin/env python

import numpy as np
import optparse
import tarfile 
from subprocess import Popen, PIPE
import sp_pgplot
import read_spd
import spio

def plot(spdfile, singlepulsefiles, xwin, outfile, just_waterfall, integrate_spec, integrate_ts, disp_pulse, tar):
    if not spdfile.endswith(".spd"):
	    raise ValueError("The first file must be a .spd file")
    #npzfile = np.load(spdfile)
    spdobj = read_spd.spd(spdfile) 
    ##### Read in the header information and other required variables for the plots. ######
    #text_array = npzfile['text_array']
    man_params = spdobj.man_params
    fn = spdobj.filename
    telescope = spdobj.telescope
    RA = spdobj.ra
    dec = spdobj.dec
    MJD = spdobj.mjd
    mjd = Popen(["mjd2cal", "%f"%MJD], stdout=PIPE, stderr=PIPE)
    date, err = mjd.communicate()
    date = date.split()[2:5]
    rank = spdobj.rank
    nsub = spdobj.waterfall_nsubs
    nbins = spdobj.nsamp
    subdm = dm = sweep_dm = spdobj.best_dm
    sigma = spdobj.sigma
    sample_number = spdobj.pulse_peak_sample
    duration = spdobj.waterfall_duration
    width_bins = spdobj.pulsewidth_bins
    pulse_width = spdobj.pulsewidth_seconds
    tsamp = spdobj.tsamp
    Total_observed_time = spdobj.total_obs_time
    topo_start = spdobj.pulse_peak_time
    start = topo_start - 0.25*duration
    datastart = spdobj.waterfall_start_time
    datasamp = spdobj.waterfall_tsamp
    datanumspectra = spdobj.waterfall_prededisp_nbins
    min_freq = spdobj.min_freq
    max_freq = spdobj.max_freq
    sweep_duration = spdobj.sweep_duration
    sweeped_start = spdobj.sweep_start_time
    bary_start = spdobj.bary_pulse_peak_time
    downsamp = datasamp/tsamp
    if xwin:
        pgplot_device = "/XWIN"
    else:
        pgplot_device = ""
    if pgplot_device:
        sp_pgplot.ppgplot.pgopen(pgplot_device)
    else:
        if (outfile == "spdplot"): # default filename
            if rank:
                sp_pgplot.ppgplot.pgopen(fn[:-5]+'_DM%.1f_%.1fs_rank_%i.spd.ps/VPS'%(subdm, (start+0.25*duration), rank))
            else:
                sp_pgplot.ppgplot.pgopen(fn[:-5]+'_DM%.1f_%.1fs.spd.ps/VPS'%(subdm, (start+0.25*duration)))
        else:
            if rank:
                sp_pgplot.ppgplot.pgopen(outfile+'_DM%.1f_%.1fs_rank_%i.spd.ps/VPS'%(subdm, (start+0.25*duration), rank))
            else:
                sp_pgplot.ppgplot.pgopen(outfile+'_DM%.1f_%.1fs.spd.ps/VPS'%(subdm, (start+0.25*duration)))
    if (just_waterfall == False):
        sp_pgplot.ppgplot.pgpap(10.25, 8.5/11.0)
        # Dedispersed waterfall plot - zerodm - OFF
        array = spdobj.data_nozerodm_dedisp.astype(np.float64)
        sp_pgplot.ppgplot.pgsvp(0.07, 0.40, 0.50, 0.80)
        sp_pgplot.ppgplot.pgswin(datastart - start, datastart -start+datanumspectra*datasamp, min_freq, max_freq)
        sp_pgplot.ppgplot.pgsch(0.8)
        sp_pgplot.ppgplot.pgslw(3)
        sp_pgplot.ppgplot.pgbox("BCST", 0, 0, "BCNST", 0, 0)
        sp_pgplot.ppgplot.pgslw(3)
        sp_pgplot.ppgplot.pgmtxt('L', 1.8, 0.5, 0.5, "Observing Frequency (MHz)")
        if not integrate_spec:
            sp_pgplot.ppgplot.pgmtxt('R', 1.8, 0.5, 0.5, "Zero-dm filtering - Off")
        sp_pgplot.plot_waterfall(array,rangex = [datastart-start, datastart-start+datanumspectra*datasamp], rangey = [min_freq, max_freq], image = 'apjgrey')
        
         #### Plot Dedispersed Time series - Zerodm filter - Off
        Dedisp_ts = array[::-1].sum(axis = 0)
        times = np.arange(datanumspectra)*datasamp
        if integrate_ts: 
            sp_pgplot.ppgplot.pgsvp(0.07, 0.40, 0.80, 0.90)
            sp_pgplot.ppgplot.pgswin(datastart - start, datastart-start+duration, np.min(Dedisp_ts), 1.05*np.max(Dedisp_ts))
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BC", 0, 0, "BC", 0, 0)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgline(times,Dedisp_ts)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgsci(1)
            
            errx1 = np.array([0.60 * (datastart-start+duration)])
            erry1 = np.array([0.60 * np.max(Dedisp_ts)])
            erry2 = np.array([np.std(Dedisp_ts)])
            errx2 = np.array([pulse_width])
            sp_pgplot.ppgplot.pgerrb(5, errx1, erry1, errx2, 1.0)
            sp_pgplot.ppgplot.pgpt(errx1, erry1, -1)
        
        #### Plot Spectrum - Zerodm filter - Off
        spectrum_window = 0.05*duration
        window_width = int(spectrum_window/datasamp)
        burst_bin = datanumspectra/downsamp/4
        on_spec = array[..., burst_bin-window_width:burst_bin+window_width]
        Dedisp_spec = on_spec.sum(axis=1)
        freqs = np.linspace(min_freq, max_freq, len(Dedisp_spec)) 
        if integrate_spec:
            sp_pgplot.ppgplot.pgsvp(0.4, 0.47, 0.5, 0.8)
            sp_pgplot.ppgplot.pgswin(np.min(Dedisp_spec), 1.05*np.max(Dedisp_spec), min_freq, max_freq)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BC", 0, 0, "BC", 0, 0)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgline(Dedisp_spec,freqs)
            sp_pgplot.ppgplot.pgmtxt('R', 1.8, 0.5, 0.5, "Zero-dm filtering - Off")
            sp_pgplot.ppgplot.pgsch(0.7)
            sp_pgplot.ppgplot.pgmtxt('T', 1.8, 0.5, 0.5, "Spectrum")
            sp_pgplot.ppgplot.pgsch(0.8)
        
        #Dedispersed waterfall plot - Zerodm ON
        sp_pgplot.ppgplot.pgsvp(0.07, 0.40, 0.1, 0.40)
        sp_pgplot.ppgplot.pgswin(datastart-start , datastart-start+datanumspectra*datasamp, min_freq, max_freq)
        sp_pgplot.ppgplot.pgsch(0.8)
        sp_pgplot.ppgplot.pgslw(3)
        sp_pgplot.ppgplot.pgbox("BCNST", 0, 0, "BCNST", 0, 0)
        sp_pgplot.ppgplot.pgmtxt('B', 2.5, 0.5, 0.5, "Time - %.2f s"%datastart)
        sp_pgplot.ppgplot.pgmtxt('L', 1.8, 0.5, 0.5, "Observing Frequency (MHz)")
        if not integrate_spec:
            sp_pgplot.ppgplot.pgmtxt('R', 1.8, 0.5, 0.5, "Zero-dm filtering - On")
        array = spdobj.data_zerodm_dedisp.astype(np.float64)
        sp_pgplot.plot_waterfall(array,rangex = [datastart-start, datastart-start+datanumspectra*datasamp],rangey = [min_freq, max_freq],image = 'apjgrey')
        #### Plot Dedispersed Time series - Zerodm filter - On
        dedisp_ts = array[::-1].sum(axis = 0)
        times = np.arange(datanumspectra)*datasamp
        if integrate_ts:
            sp_pgplot.ppgplot.pgsvp(0.07, 0.40, 0.40, 0.50)
            sp_pgplot.ppgplot.pgswin(datastart - start, datastart-start+duration, np.min(dedisp_ts), 1.05*np.max(dedisp_ts))
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BC", 0, 0, "BC", 0, 0)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgline(times,dedisp_ts)
            errx1 = np.array([0.60 * (datastart-start+duration)])
            erry1 = np.array([0.60 * np.max(dedisp_ts)])
            erry2 = np.array([np.std(dedisp_ts)])
            errx2 = np.array([pulse_width])
            sp_pgplot.ppgplot.pgerrb(5, errx1, erry1, errx2, 1.0)
            sp_pgplot.ppgplot.pgpt(errx1, erry1, -1)
        
        #### Plot Spectrum - Zerodm filter - On
        spectrum_window = 0.05*duration
        window_width = int(spectrum_window/datasamp)
        burst_bin = datanumspectra/downsamp/4
        on_spec = array[..., burst_bin-window_width:burst_bin+window_width]
        Dedisp_spec = on_spec.sum(axis=1)
        freqs = np.linspace(min_freq, max_freq, len(Dedisp_spec)) 
        if integrate_spec:
            sp_pgplot.ppgplot.pgsvp(0.4, 0.47, 0.1, 0.4)
            sp_pgplot.ppgplot.pgswin(np.min(Dedisp_spec), 1.05*np.max(Dedisp_spec), min_freq, max_freq)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BC", 0, 0, "BC", 0, 0)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgline(Dedisp_spec,freqs)
            sp_pgplot.ppgplot.pgmtxt('R', 1.8, 0.5, 0.5, "Zero-dm filtering - On")
            sp_pgplot.ppgplot.pgsch(0.7)
            sp_pgplot.ppgplot.pgmtxt('T', 1.8, 0.5, 0.5, "Spectrum")
            sp_pgplot.ppgplot.pgsch(0.8)
        
        if disp_pulse:
            # Sweeped waterfall plot Zerodm - OFF
            array = spdobj.data_nozerodm.astype(np.float64)
            sp_pgplot.ppgplot.pgsvp(0.20, 0.40, 0.50, 0.70)
            sp_pgplot.ppgplot.pgswin(sweeped_start, sweeped_start+sweep_duration, min_freq, max_freq)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(4)
            sp_pgplot.ppgplot.pgbox("BCST", 0, 0, "BCST", 0, 0)
            sp_pgplot.ppgplot.pgsch(3)
            sp_pgplot.plot_waterfall(array,rangex = [sweeped_start, sweeped_start+sweep_duration],rangey = [min_freq, max_freq],image = 'apjgrey')
            delays = spdobj.dmsweep_delays
            freqs = spdobj.dmsweep_freqs
            sp_pgplot.ppgplot.pgslw(5)
            sweepstart = sweeped_start- 0.2*sweep_duration
            sp_pgplot.ppgplot.pgsci(0)
            sp_pgplot.ppgplot.pgline(delays+sweepstart, freqs)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgslw(3)
            
            # Sweeped waterfall plot Zerodm - ON
            array = spdobj.data_zerodm.astype(np.float64)
            sp_pgplot.ppgplot.pgsvp(0.20, 0.40, 0.1, 0.3)
            sp_pgplot.ppgplot.pgswin(sweeped_start, sweeped_start+sweep_duration, min_freq, max_freq)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(4)
            sp_pgplot.ppgplot.pgbox("BCST", 0, 0, "BCST", 0, 0)
            sp_pgplot.ppgplot.pgsch(3)
            sp_pgplot.plot_waterfall(array,rangex = [sweeped_start, sweeped_start+sweep_duration],rangey = [min_freq, max_freq],image = 'apjgrey')
            sp_pgplot.ppgplot.pgslw(5)
            sweepstart = sweeped_start- 0.2*sweep_duration
            sp_pgplot.ppgplot.pgsci(0)
            sp_pgplot.ppgplot.pgline(delays+sweepstart, freqs)
            sp_pgplot.ppgplot.pgsci(1)
        
        #### Figure texts 
        if integrate_spec:
            sp_pgplot.ppgplot.pgsvp(0.81, 0.97, 0.64, 0.909)
            sp_pgplot.ppgplot.pgsch(0.62)
        else:
            sp_pgplot.ppgplot.pgsvp(0.745, 0.97, 0.64, 0.909)
            sp_pgplot.ppgplot.pgsch(0.7)
        sp_pgplot.ppgplot.pgslw(3)
        sp_pgplot.ppgplot.pgmtxt('T', -1.1, 0.01, 0.0, "RA: %s" %RA)
        sp_pgplot.ppgplot.pgmtxt('T', -2.6, 0.01, 0.0, "DEC: %s" %dec)
        sp_pgplot.ppgplot.pgmtxt('T', -4.1, 0.01, 0.0, "MJD: %f" %MJD)
        sp_pgplot.ppgplot.pgmtxt('T', -5.6, 0.01, 0.0, "Obs date: %s %s %s" %(date[0], date[1], date[2]))
        sp_pgplot.ppgplot.pgmtxt('T', -7.1, 0.01, 0.0, "Telescope: %s" %telescope)
        sp_pgplot.ppgplot.pgmtxt('T', -8.6, 0.01, 0.0, "DM: %.2f pc cm\u-3\d" %dm)
        if sigma:
            sp_pgplot.ppgplot.pgmtxt('T', -10.1, 0.01, 0.0, "S/N\dMAX\u: %.2f" %sigma)
        else:
            sp_pgplot.ppgplot.pgmtxt('T', -10.1, 0.01, 0.0, "S/N\dMAX\u: N/A")
        sp_pgplot.ppgplot.pgmtxt('T', -11.6, 0.01, 0.0, "Number of samples: %i" %nbins)
        sp_pgplot.ppgplot.pgmtxt('T', -13.1, 0.01, 0.0, "Number of subbands: %i" %nsub)
        sp_pgplot.ppgplot.pgmtxt('T', -14.6, 0.01, 0.0, "Pulse width: %.2f ms" %(pulse_width*1e3))
        sp_pgplot.ppgplot.pgmtxt('T', -16.1, 0.01, 0.0, "Sampling time: %.3f \gms" %(tsamp*1e6))
        sp_pgplot.ppgplot.pgmtxt('T', -17.6, 0.0, 0.0, "Bary pulse peak time: %.2f s" %(bary_start))
        sp_pgplot.ppgplot.pgsvp(0.07, 0.7, 0.01, 0.05)
        sp_pgplot.ppgplot.pgmtxt('T', -2.1, 0.01, 0.0, "%s" %fn)
        
        #DM vs SNR
        if not man_params:
            dm_arr = np.float32(spdobj.dmVt_this_dms)
            sigma_arr = np.float32 (spdobj.dmVt_this_sigmas)
            if integrate_spec:
                sp_pgplot.ppgplot.pgsvp(0.55, 0.80, 0.65, 0.90)
            else:
                sp_pgplot.ppgplot.pgsvp(0.48, 0.73, 0.65, 0.90)
            sp_pgplot.ppgplot.pgswin(np.min(dm_arr), np.max(dm_arr), 0.95*np.min(sigma_arr), 1.05*np.max(sigma_arr))
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BCNST", 0, 0, "BCNST", 0, 0)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgmtxt('B', 2.5, 0.5, 0.5, "DM (pc cm\u-3\d)")
            sp_pgplot.ppgplot.pgmtxt('L', 1.8, 0.5, 0.5, "Signal-to-noise")
            sp_pgplot.ppgplot.pgpt(dm_arr, sigma_arr, 20)
        else:
            if integrate_spec:
                sp_pgplot.ppgplot.pgsvp(0.55, 0.80, 0.65, 0.90)
            else:
                sp_pgplot.ppgplot.pgsvp(0.48, 0.73, 0.65, 0.90)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BCNST", 0, 0, "BCNST", 0, 0)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgmtxt('B', 2.5, 0.5, 0.5, "DM (pc cm\u-3\d)")
            sp_pgplot.ppgplot.pgmtxt('L', 1.8, 0.5, 0.5, "Signal-to-noise")

        # DM vs Time
        print "Making arrays for DM vs time plot"
        spfiles = singlepulsefiles
        threshold = 5.0
        dm_list = map(np.float32, list(dm_arr))
        time_list = map(np.float32, list(spdobj.dmVt_this_times))
        if len(spfiles) > 2:
            if integrate_spec:
                sp_pgplot.ppgplot.pgsvp(0.55, 0.97, 0.1, 0.54)
            else:
                sp_pgplot.ppgplot.pgsvp(0.48, 0.97, 0.1, 0.54)
            dms, times, sigmas, widths, filelist = spio.gen_arrays(dm_arr, spfiles, tar, threshold)
            sp_pgplot.dm_time_plot(dms, times, sigmas, dm_list, sigma_arr, time_list, Total_observed_time, xwin)
        else:
            print "You need a .singlepulse.tgz file to plot DM vs Time plot."
            if integrate_spec:
                sp_pgplot.ppgplot.pgsvp(0.55, 0.97, 0.1, 0.54)
            else:
                sp_pgplot.ppgplot.pgsvp(0.48, 0.97, 0.1, 0.54)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BCNST", 0, 0, "BCNST", 0, 0)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgmtxt('B', 2.5, 0.5, 0.5, "Time (s)")
            sp_pgplot.ppgplot.pgmtxt('L', 1.8, 0.5, 0.5, "DM (pc cm\u-3\d)")
    else:
        #sp_pgplot.ppgplot.pgpap(10.25, 10.0/5.0)
        sp_pgplot.ppgplot.pgpap(8.0, 1.5)
        # Dedispersed waterfall plot - zerodm - OFF
        array = spdobj.data_nozerodm_dedisp.astype(np.float64)
        sp_pgplot.ppgplot.pgsvp(0.1, 0.70, 0.44, 0.75)
        sp_pgplot.ppgplot.pgswin(datastart - start, datastart -start+datanumspectra*datasamp, min_freq, max_freq)
        sp_pgplot.ppgplot.pgsch(0.8)
        sp_pgplot.ppgplot.pgslw(3)
        sp_pgplot.ppgplot.pgbox("BCST", 0, 0, "BCNST", 0, 0)
        sp_pgplot.ppgplot.pgslw(3)
        sp_pgplot.ppgplot.pgmtxt('L', 1.8, 0.5, 0.5, "Observing Frequency (MHz)")
        sp_pgplot.plot_waterfall(array,rangex = [datastart-start, datastart-start+datanumspectra*datasamp], rangey = [min_freq, max_freq], image = 'apjgrey')
         
        #### Plot Dedispersed Time series - Zerodm filter - Off
        Dedisp_ts = array[::-1].sum(axis = 0)
        times = np.arange(datanumspectra)*datasamp
        if integrate_ts:
            sp_pgplot.ppgplot.pgsvp(0.1, 0.70, 0.75, 0.83)
            sp_pgplot.ppgplot.pgswin(datastart - start, datastart-start+duration, np.min(Dedisp_ts), 1.05*np.max(Dedisp_ts))
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BC", 0, 0, "BC", 0, 0)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgline(times,Dedisp_ts)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgsci(1)
            errx1 = np.array([0.60 * (datastart-start+duration)])
            erry1 = np.array([0.60 * np.max(Dedisp_ts)])
            erry2 = np.array([np.std(Dedisp_ts)])
            errx2 = np.array([pulse_width])
            sp_pgplot.ppgplot.pgerrb(5, errx1, erry1, errx2, 1.0)
            sp_pgplot.ppgplot.pgpt(errx1, erry1, -1)
        
        #### Plot Spectrum - Zerodm filter - Off
        spectrum_window = 0.05*duration
        window_width = int(spectrum_window/datasamp)
        burst_bin = datanumspectra/downsamp/4
        on_spec = array[..., burst_bin-window_width:burst_bin+window_width]
        Dedisp_spec = on_spec.sum(axis=1)
        freqs = np.linspace(min_freq, max_freq, len(Dedisp_spec)) 
        if integrate_spec:
            sp_pgplot.ppgplot.pgsvp(0.7, 0.9, 0.44, 0.75)
            sp_pgplot.ppgplot.pgswin(np.min(Dedisp_spec), 1.05*np.max(Dedisp_spec), min_freq, max_freq)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BC", 0, 0, "BC", 0, 0)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgline(Dedisp_spec,freqs)
            sp_pgplot.ppgplot.pgmtxt('R', 1.8, 0.5, 0.5, "Zero-dm filtering - Off")
            sp_pgplot.ppgplot.pgsch(0.7)
            sp_pgplot.ppgplot.pgmtxt('T', 1.8, 0.5, 0.5, "Spectrum")
            sp_pgplot.ppgplot.pgsch(0.8)
        
        #Dedispersed waterfall plot - Zerodm ON
        array = spdobj.data_zerodm_dedisp.astype(np.float64)
        sp_pgplot.ppgplot.pgsvp(0.1, 0.70, 0.05, 0.36)
        sp_pgplot.ppgplot.pgswin(datastart-start , datastart-start+datanumspectra*datasamp, min_freq, max_freq)
        sp_pgplot.ppgplot.pgsch(0.8)
        sp_pgplot.ppgplot.pgslw(3)
        sp_pgplot.ppgplot.pgbox("BCNST", 0, 0, "BCNST", 0, 0)
        sp_pgplot.ppgplot.pgmtxt('B', 2.5, 0.5, 0.5, "Time - %.2f s"%datastart)
        sp_pgplot.ppgplot.pgmtxt('L', 1.8, 0.5, 0.5, "Observing Frequency (MHz)")
        sp_pgplot.plot_waterfall(array,rangex = [datastart-start, datastart-start+datanumspectra*datasamp],rangey = [min_freq, max_freq],image = 'apjgrey')
        
        
        #### Plot Dedispersed Time series - Zerodm filter - On
        dedisp_ts = array[::-1].sum(axis = 0)
        times = np.arange(datanumspectra)*datasamp
        if integrate_ts:
            sp_pgplot.ppgplot.pgsvp(0.1, 0.7, 0.36, 0.44)
            sp_pgplot.ppgplot.pgswin(datastart - start, datastart-start+duration, np.min(dedisp_ts), 1.05*np.max(dedisp_ts))
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BC", 0, 0, "BC", 0, 0)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgline(times,dedisp_ts)
            errx1 = np.array([0.60 * (datastart-start+duration)])
            erry1 = np.array([0.60 * np.max(dedisp_ts)])
            erry2 = np.array([np.std(dedisp_ts)])
            errx2 = np.array([pulse_width])
            sp_pgplot.ppgplot.pgerrb(5, errx1, erry1, errx2, 1.0)
            sp_pgplot.ppgplot.pgpt(errx1, erry1, -1)
        
        #### Plot Spectrum - Zerodm filter - On
        spectrum_window = 0.05*duration
        window_width = int(spectrum_window/datasamp)
        burst_bin = datanumspectra/downsamp/4
        on_spec = array[..., burst_bin-window_width:burst_bin+window_width]
        Dedisp_spec = on_spec.sum(axis=1)
        freqs = np.linspace(min_freq, max_freq, len(Dedisp_spec)) 
        if integrate_spec:
            sp_pgplot.ppgplot.pgsvp(0.70, 0.90, 0.05, 0.36)
            sp_pgplot.ppgplot.pgswin(np.min(Dedisp_spec), 1.05*np.max(Dedisp_spec), min_freq, max_freq)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(3)
            sp_pgplot.ppgplot.pgbox("BC", 0, 0, "BC", 0, 0)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgline(Dedisp_spec,freqs)
            sp_pgplot.ppgplot.pgmtxt('R', 1.8, 0.5, 0.5, "Zero-dm filtering - On")
            sp_pgplot.ppgplot.pgsch(0.7)
            sp_pgplot.ppgplot.pgmtxt('T', 1.8, 0.5, 0.5, "Spectrum")
            sp_pgplot.ppgplot.pgsch(0.8)
        if disp_pulse: 
            # Sweeped waterfall plot Zerodm - OFF
            array = spdobj.data_nozerodm.astype(np.float64)
            sp_pgplot.ppgplot.pgsvp(0.3, 0.70, 0.44, 0.65)
            sp_pgplot.ppgplot.pgswin(sweeped_start, sweeped_start+sweep_duration, min_freq, max_freq)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(4)
            sp_pgplot.ppgplot.pgbox("BCST", 0, 0, "BCST", 0, 0)
            sp_pgplot.ppgplot.pgsch(3)
            sp_pgplot.plot_waterfall(array,rangex = [sweeped_start, sweeped_start+sweep_duration],rangey = [min_freq, max_freq],image = 'apjgrey')
            delays = spdobj.dmsweep_delays
            freqs = spdobj.dmsweep_freqs
            sp_pgplot.ppgplot.pgslw(5)
            sweepstart = sweeped_start- 0.2*sweep_duration
            sp_pgplot.ppgplot.pgsci(0)
            sp_pgplot.ppgplot.pgline(delays+sweepstart, freqs)
            sp_pgplot.ppgplot.pgsci(1)
            sp_pgplot.ppgplot.pgslw(3)
            
            # Sweeped waterfall plot Zerodm - ON
            array = spdobj.data_zerodm.astype(np.float64)
            sp_pgplot.ppgplot.pgsvp(0.3, 0.70, 0.05, 0.25)
            sp_pgplot.ppgplot.pgswin(sweeped_start, sweeped_start+sweep_duration, min_freq, max_freq)
            sp_pgplot.ppgplot.pgsch(0.8)
            sp_pgplot.ppgplot.pgslw(4)
            sp_pgplot.ppgplot.pgbox("BCST", 0, 0, "BCST", 0, 0)
            sp_pgplot.ppgplot.pgsch(3)
            sp_pgplot.plot_waterfall(array,rangex = [sweeped_start, sweeped_start+sweep_duration],rangey = [min_freq, max_freq],image = 'apjgrey')
            sp_pgplot.ppgplot.pgslw(5)
            sweepstart = sweeped_start- 0.2*sweep_duration
            sp_pgplot.ppgplot.pgsci(0)
            sp_pgplot.ppgplot.pgline(delays+sweepstart, freqs)
            sp_pgplot.ppgplot.pgsci(1)
        
        #### Figure texts 
        sp_pgplot.ppgplot.pgsvp(0.05, 0.95, 0.8, 0.9)
        sp_pgplot.ppgplot.pgsch(0.65)
        sp_pgplot.ppgplot.pgslw(3)
        sp_pgplot.ppgplot.pgmtxt('T', -1.1, 0.01, 0.0, "RA: %s" %RA)
        sp_pgplot.ppgplot.pgmtxt('T', -2.5, 0.01, 0.0, "DEC: %s" %dec)
        sp_pgplot.ppgplot.pgmtxt('T', -3.9, 0.01, 0.0, "MJD: %f" %MJD)
        sp_pgplot.ppgplot.pgmtxt('T', -5.3, 0.01, 0.0, "Obs date: %s %s %s" %(date[0], date[1], date[2]))
        sp_pgplot.ppgplot.pgmtxt('T', -1.1, 0.35, 0.0, "Telescope: %s" %telescope)
        sp_pgplot.ppgplot.pgmtxt('T', -2.5, 0.35, 0.0, "DM: %.2f pc cm\u-3\d" %dm)
        if sigma:
            sp_pgplot.ppgplot.pgmtxt('T', -3.9, 0.35, 0.0, "S/N\dMAX\u: %.2f" %sigma)
        else:
            sp_pgplot.ppgplot.pgmtxt('T', -3.9, 0.35, 0.0, "S/N\dMAX\u: N/A")
        sp_pgplot.ppgplot.pgmtxt('T', -5.3, 0.35, 0.0, "Number of samples: %i" %nbins)
        sp_pgplot.ppgplot.pgmtxt('T', -1.1, 0.65, 0.0, "Number of subbands: %i" %nsub)
        sp_pgplot.ppgplot.pgmtxt('T', -2.5, 0.65, 0.0, "Pulse width: %.2f ms" %(pulse_width*1e3))
        sp_pgplot.ppgplot.pgmtxt('T', -3.9, 0.65, 0.0, "Sampling time: %.3f \gms" %(tsamp*1e6))
        sp_pgplot.ppgplot.pgmtxt('T', -5.3, 0.65, 0.0, "Bary pulse peak time: %.2f s" %(bary_start))
    sp_pgplot.ppgplot.pgiden()
    sp_pgplot.ppgplot.pgclos()

def main():
    parser = optparse.OptionParser(prog="plot_spd.py", \
				   usage = "%prog [OPTIONS] INFILE (.spd file) INFILES (.singlepulse files)")
    parser.add_option("-x", "--xwin", action="store_true", dest="xwin",
                      default=False, help="Don't make a postscript plot, just use an X-window")
    parser.add_option("-o", dest= "outfile", type = "string", default = "spdplot", \
                      help= "give a base name to the saved plot. DM, time and" \
                            "rank values will be added automatically" )
    parser.add_option("--just-waterfall", action="store_true", dest="just_waterfall",
                      default=False, help="Just produce the waterfall plots.")
    parser.add_option("--show-spec", action="store_true", dest="integrate_spec",
                      default=False, help="Show spectrum.(Default: Show spectrum)")
    parser.add_option("--show-ts", action="store_true", dest="integrate_ts",
                      default=False, help="Show time series.(Default: Don't show time series)")
    parser.add_option("--show-sweep", action="store_true", dest="disp_pulse",
                      default=False, help="Show dispersed pulse.(Default: Don't show dispersed pulse)")
    (options, args) = parser.parse_args()
   
    if len(args) == 0:
        raise ValueError("need a .spd file and .singlepulse files in that order.")
    if not args[0].endswith(".spd"):
        raise ValueError("the first file must be a .spd file")
    if len(args) == 2:
        tar = tarfile.open(args[1], "r:gz")# read in the tarball
        filenames = tar.getnames()# get the filenames
        plot(args[0], filenames, options.xwin, options.outfile, options.just_waterfall, \
             options.integrate_spec, options.integrate_ts, options.disp_pulse, tar)# make the sp plots   
        tar.close()
    else:
        plot(args[0], args[1:], options.xwin, options.outfile, options.just_waterfall, \
             options.integrate_spec, options.integrate_ts, options.disp_pulse, tar = None)# make the sp plots   

if __name__ == '__main__':
    main() 

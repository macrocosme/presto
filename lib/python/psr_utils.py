import numpy as Num
import numpy.fft as FFT
import Pgplot, ppgplot, bisect, sinc_interp
from scipy.stats import mean, std, histogram
from scipy.special import ndtr, ndtri, chdtrc, chdtri, i0, kolmogorov
from scipy.optimize import leastsq
from scipy.optimize.minpack import bisection
from psr_constants import *

isintorlong = lambda x: type(x) == type(0) or type(x) == type(0L)

def span(Min, Max, Number):
    """
    span(Min, Max, Number):
        Create a range of 'Num' floats given inclusive 'Min' and 'Max' values.
    """
    assert isintorlong(Number)
    if isintorlong(Min) and isintorlong(Max) and \
       (Max-Min) % (Number-1) != 0:
        Max = float(Max) # force floating points
    return Min+(Max-Min)*Num.arange(Number)/(Number-1)

def distance(width):
    """
    distance(width):
        Return a 'width' x 'width' Num Python array with each
            point set to the geometric distance from the array's center.
    """
    x = Num.arange(-width/2.0+0.5, width/2.0+0.5, 1.0)**2
    x = Num.resize(x, (width,width))
    return Num.sqrt(x + Num.transpose(x))

def running_avg(arr, navg):
    """
    running_avg(arr, navg):
        Return an array of the running average of 'navg' bins from the
        input array 'arr'.
    """
    a = Num.asarray(arr, 'd')
    a.shape = (len(a) / navg, navg)
    return Num.add.reduce(Num.transpose(a)) / navg

def hist(data, bins, range=None, labx="", laby="Number", color=1, line=1,
         width=2, aspect=0.7727, device='/XWIN'):
    """
    hist(data, bins, range=None):
    Return and plot a histogram in one variable.
      data  -- a sequence of data points
      bins  -- the number of bins into which the data is to be sorted
      range -- a tuple of two values, specifying the lower and
               the upper end of the interval spanned by the bins.
               Any data point outside this interval will be ignored.
               If no range is given, the smallest and largest
               data values are used to define the interval.
    Note:  This command also accepts some basic flags for the plot,
           like labx, laby, aspect, color, line, width, and device.
    """
    (ys, lox, dx, out) = histogram(data, bins, range)
    xs = Num.arange(bins, dtype='d')*dx + lox + 0.5*dx
    maxy = int(1.1*max(ys))
    if maxy < max(ys):
        maxy = max(ys) + 1.0
    Pgplot.plotbinned(ys, xs, rangey=[0,maxy], width=width,
                      labx=labx, laby=laby, color=color, line=line,
                      aspect=aspect, device=device)
    return (xs, ys)

def KS_test(data, cumdist, output=0):
    """
    KS_test(data, cumdist, output=0):
        Perform a Kolmogorov-Smirnov test on data compared to the
            cumulative-distribution function cumdist.
    """
    nn = len(data)
    sdata = Num.sort(Num.asarray(data))
    D1 = Num.maximum.reduce(Num.absolute(cumdist(sdata)-
                                         Num.arange(nn, dtype='d')/nn))
    D2 = Num.maximum.reduce(Num.absolute(cumdist(sdata)-
                                         Num.arange(1,nn+1, dtype='d')/nn))
    D = max((D1, D2))
    P = kolmogorov(Num.sqrt(nn)*D)
    if (output):
        print "Max distance between the cumulative distributions (D) = %.5g" % D
        print "Prob the data is from the specified distrbution   (P) = %.3g" % P
    return (D, P)


def MJD_to_JD(MJD):
    """
    MJD_to_JD(MJD):
       Convert Modified Julian Date (MJD) to Julian Date (JD)
    """
    return MJD+2400000.5

def JD_to_MJD(JD):
    """
    JD_to_MJD(JD):
       Convert Julian Date (JD) to Modified Julian Date (MJD)
    """
    return JD-2400000.5

def MJD_to_Julian_Epoch(MJD):
    """
    MJD_to_Julian_Epoch(MJD):
       Convert Modified Julian Date (MJD) to Julian Epoch
    """
    return 2000.0 + (MJD-51544.5)/365.25

def Julian_Epoch_to_MJD(jepoch):
    """
    Julian_Epoch_to_MJD(jepoch):
       Convert Julian Epoch to Modified Julian Date (MJD)
    """
    return 51544.5 + (jepoch-2000.0)*365.25

def MJD_to_Besselian_Epoch(MJD):
    """
    MJD_to_Besselian_Epoch(MJD):
       Convert Modified Julian Date (MJD) to Besselian Epoch
    """
    return 1900.0 + (MJD-15019.81352)/365.242198781

def Besselian_Epoch_to_MJD(bepoch):
    """
    Besselian_Epoch_to_MJD(bepoch):
       Convert Besselian Epoch to Modified Julian Date (MJD)
    """
    return 15019.81352 + (bepoch-1900.0)*365.242198781

def rad_to_dms(rad):
    """
    rad_to_dms(rad):
       Convert radians to degrees, minutes, and seconds of arc.
    """
    if (rad < 0.0): sign = -1
    else: sign = 1
    arc = RADTODEG * Num.fmod(Num.fabs(rad), PI)
    d = int(arc)
    arc = (arc - d) * 60.0
    m = int(arc)
    s = (arc - m) * 60.0
    return (sign * d, m, s)

def dms_to_rad(deg, min, sec):
    """
    dms_to_rad(deg, min, sec):
       Convert degrees, minutes, and seconds of arc to radians.
    """
    if (deg < 0.0): sign = -1
    else: sign = 1
    return sign * ARCSECTORAD * \
           (60.0 * (60.0 * Num.fabs(deg) +
                    Num.fabs(min)) + Num.fabs(sec))

def dms_to_deg(deg, min, sec):
    """
    dms_to_deg(deg, min, sec):
       Convert degrees, minutes, and seconds of arc to degrees.
    """
    return RADTODEG * dms_to_rad(deg, min, sec)

def rad_to_hms(rad):
    """
    rad_to_hms(rad):
       Convert radians to hours, minutes, and seconds of arc.
    """
    rad = Num.fmod(rad, TWOPI)
    if (rad < 0.0): rad = rad + TWOPI
    arc = RADTOHRS * rad
    h = int(arc)
    arc = (arc - h) * 60.0
    m = int(arc)
    s = (arc - m) * 60.0
    return (h, m, s)

def hms_to_rad(hour, min, sec):
    """
    hms_to_rad(hour, min, sec):
       Convert hours, minutes, and seconds of arc to radians
    """
    if (hour < 0.0): sign = -1
    else: sign = 1
    return sign * SECTORAD * \
           (60.0 * (60.0 * Num.fabs(hour) +
                    Num.fabs(min)) + Num.fabs(sec))

def hms_to_hrs(hour, min, sec):
    """
    hms_to_hrs(hour, min, sec):
       Convert hours, minutes, and seconds of arc to hours.
    """
    return RADTOHRS * hms_to_rad(hour, min, sec)

def coord_to_string(h_or_d, m, s):
    """
    coord_to_string(h_or_d, m, s):
       Return a formatted string of RA or DEC values as
       'hh:mm:ss.ssss' if RA, or 'dd:mm:ss.ssss' if DEC.
    """
    if (s >= 9.9995):
        return "%.2d:%.2d:%.4f" % (h_or_d, m, s)
    else:
        return "%.2d:%.2d:0%.4f" % (h_or_d, m, s)

def ra_to_rad(ra_string):
    """
    ra_to_rad(ar_string):
       Given a string containing RA information as
       'hh:mm:ss.ssss', return the equivalent decimal
       radians.
    """
    h, m, s = ra_string.split(":")
    return hms_to_rad(int(h), int(m), float(s))

def dec_to_rad(dec_string):
    """
    dec_to_rad(dec_string):
       Given a string containing DEC information as
       'dd:mm:ss.ssss', return the equivalent decimal
       radians.
    """
    d, m, s = dec_string.split(":")
    return dms_to_rad(int(d), int(m), float(s))

def delta_m(flux_factor):
    """
    delta_m(flux_factor):
        Return the change in magnitudes caused by a change
            in flux of flux_factor.
    """
    return -2.5*Num.log10(flux_factor)

def flux_factor(delta_m):
    """
    flux_factor(delta_m):
        Return the change in flux caused by a change
            in magnitude of delta_m magnitudes
    """
    return 10.0**(delta_m/-2.5)

def distance_modulus_to_distance(dm, absorption=0.0):
    """
    distance_modulus_to_distance(dm, absorption=0.0):
        Return the distance (kpc) given a distance modulus dm and
            an optional absorption.
    """
    return 10.0**(((dm-absorption)+5.0)/5.0)/1000.0

def distance_to_distance_modulus(d, absorption=0.0):
    """
    distance_to_distance_modulus(d, absorption=0.0):
        Return the distance modulus given a distance d and
            an optional absorption.
    """
    return 5.0*Num.log10(d*1000.0)-5.0+absorption

def true_anomaly(E, ecc):
    """
    true_anomaly(E, ecc):
        Return the True Anomaly (in radians) given the Eccentric anomaly
            (E in radians) and the eccentricity (ecc)
    """
    return 2.0*Num.arctan(Num.sqrt((1.0+ecc)/(1.0-ecc))*Num.tan(E/2.0))

def mass_funct(pb, x):
    """
    mass_funct(pb, x):
        Return the mass function of an orbit given the following:
            'pb' is the binary period in sec.
            'x' is the projected semi-major axis in lt-sec.
    """
    return 8015123.37129 * x**3.0 / (pb * pb)

def mass_funct2(mp, mc, i):
    """
    mass_funct2(mp, mc, i):
        Return the mass function of an orbit given the following:
            'mp' is the mass of the primary in solar masses.
            'mc' is the mass of the companion in solar masses.
            'i' is the orbital inclination (rad).
        Note:  An 'average' orbit has cos(i) = 0.5, or i = 60 deg
    """
    return (mc * Num.sin(i))**3 / (mc + mp)**2

def asini_c(pb, mf):
    """
    asini_c(pb, mf):
        Return the orbital projected semi-major axis (lt-sec) given:
            'pb' is the binary period in sec.
            'mf' is the mass function of the orbit.
    """
    return (mf * pb * pb / 8015123.37129)**(1.0 / 3.0)


def bins_to_accel(rdot, T, f=[1.0, 1000.0], device="/XWIN"):
    """
    bins_to_accel(rdot, T, f=[1.0, 1000.0], device="/XWIN"):
        Make a plot showing the acceleration which corresponds
        to a certain number of Fourier bins drifted 'rdot' during
        an observation of length 'T'.
    """
    fs = span(Num.log10(f[0]), Num.log10(f[1]), 1000)
    accels = rdot * SOL / (T * T * 10.0**fs)
    if (device):
        Pgplot.plotxy(Num.log10(accels), fs, logx=1, logy=1,
                      labx="Frequency (Hz)",
                      laby="Acceleration (m/s\u2\d)", device=device)
        ppgplot.pgmtxt("T", -2.0, 0.75, 0.0, "T = %.0f sec"%T)
        ppgplot.pgmtxt("T", -3.5, 0.75, 0.0, "r\B\u\.\d = %.1f bins"%rdot)
        if (device != '/XWIN'):
            Pgplot.closeplot()
    else:
        return accels

def companion_mass(pb, x, inc=60.0, mpsr=1.4):
    """
    companion_mass(pb, x, inc=60.0, mpsr=1.4):
        Return the companion mass (in solar mass units) for a binary
        system with the following characteristics:
            'pb' is the binary period in sec.
            'x' is the projected semi-major axis in lt-sec.
            'inc' is the orbital inclination in degrees.
            'mpsr' is the mass of the pulsar in solar mass units.
    """
    massfunct = mass_funct(pb, x)
    def localmf(mc, mp=mpsr, mf=massfunct, i=inc*DEGTORAD):
        return (mc*Num.sin(i))**3.0/(mp + mc)**2.0 - mf
    return bisection(localmf, 0.0, 1000.0)
        
def companion_mass_limit(pb, x, mpsr=1.4):
    """
    companion_mass_limit(pb, x, mpsr=1.4):
        Return the lower limit (corresponding to i = 90 degrees) of the
        companion mass (in solar mass units) in a binary system with
        the following characteristics:
            'pb' is the binary period in sec.
            'x' is the projected semi-major axis in lt-sec.
            'mpsr' is the mass of the pulsar in solar mass units.
    """
    return companion_mass(pb, x, inc=90.0, mpsr=mpsr)
        
def OMDOT(porb, e, Mp, Mc):
    """
    OMDOT(porb, e, Mp, Mc):
        Return the predicted advance of periaston (deg/yr) given the
        orbital period (s), eccentricity, and pulsar and companion masses.
    """
    return 3.0 * (porb/TWOPI)**(-5.0/3.0) * \
           (Tsun*(Mp+Mc))**(2.0/3.0) / (1.0-e**2.0) * \
           RADTODEG * SECPERJULYR

def gamma(porb, e, Mp, Mc):
    """
    gamma(porb, e, Mp, Mc):
        Return the predicted value of relativistic gamma (ms) given the
        orbital period (s), eccentricity, and pulsar and companion masses.
    """
    return e * (porb/TWOPI)**(1.0/3.0) * Tsun**(2.0/3.0) * \
           (Mp+Mc)**(-4.0/3.0) * Mc * (Mp+2.0*Mc) * 1000.0

def PBDOT(porb, e, Mp, Mc):
    """
    PBDOT(porb, e, Mp, Mc):
        Return the predicted orbital period derivative (s/s) given the
        orbital period (s), eccentricity, and pulsar and companion masses.
    """
    return -192.0*PI/5.0 * (porb/TWOPI)**(-5.0/3.0) * \
           (1.0 + 73.0/24.0*e**2.0 + 37.0/96.0*e**4.0) * \
           (1.0-e**2.0)**(-7.0/2.0) * Tsun**(5.0/3.0) * \
           Mp * Mc * (Mp+Mc)**(-1.0/3.0)


def OMDOT_to_Mtot(OMDOT, porb, e):
    """
    OMDOT_to_Mtot(OMDOT, porb, e):
        Return the total mass (in solar units) of a system given an advance
        of periastron (OMDOT) in deg/yr.  The opbital period should be in sec.
    """
    porb /= SECPERDAY
    wd = OMDOT/SECPERJULYR*DEGTORAD # rad/s
    return (wd/3.0*(1.0-e*e)*(porb*SECPERDAY/TWOPI)**(5.0/3.0))**(3.0/2.0)/Tsun

def beam_halfwidth(obs_freq, dish_diam):
    """
    beam_halfwidth(obs_freq, dish_diam):
        Return the telescope beam halfwidth in arcmin
            'obs_freq' = the observing frqeuency in MHz
            'dish_diam' = the telescope diameter in m
    """
    return 1.2*SOL/(obs_freq*10.0**6)/dish_diam*RADTODEG*60/2

def limiting_flux_dens(Ttot, G, BW, T, P=0.01, W=0.05, polar=2, factor=15.0):
    """
    limiting_flux_dens(Ttot, G, BW, T, P=0.01, W=0.05, polar=2, factor=15.0):
        Return the approximate limiting flux density for a pulsar
        survey in mJy based of the following characteristics:
            'Ttot' = sky + system temperature (K)
            'G' = forward gain of the antenna (K/Jy)
            'BW' = observing bandwidth (MHz)
            'T' = integration time (s)
            'P' = pulsar period (s) (default = 0.01)
            'W' = duty cycle of pulsar (0-1) (default = 0.05)
            'polar' = number of polarizations (default = 2)
            'factor' = normalization factor that take into account
                limiting SNR, hardware limitations etc. (default = 15.0)
        Note:  This is a _very_ approximate calculation.  For a better
            calculation, see Cordes and Chernoff, ApJ, 482, p971, App. A.
        Observatories:
            Parkes Multibeam: Tsys = 21 K, G = 0.735 K/Jy
    """
    w = W * P
    return Num.sqrt(w/((P-w)*polar*BW*T))*factor*Ttot/G

def dm_info(dm=None, dmstep=1.0, freq=1390.0, numchan=512, chanwidth=0.5):
    """
    dm_info(dm=None, dmstep=1.0, freq=1390.0, numchan=512, chanwidth=0.5):
        Return info about potential DM smearing during an observation.
    """
    BW = chanwidth * numchan
    print "      Center freq (MHz) = %.3f" % (freq)
    print "     Number of channels = %d" % (numchan)
    print "    Channel width (MHz) = %.3g" % (chanwidth)
    print "  Total bandwidth (MHz) = %.3g" % (BW)
    print "   DM offset (0.5*step) = %.3g" % (0.5 * dmstep)
    print "  Smearing over BW (ms) = %.3g" % \
          (1000.0 * dm_smear(0.5 * dmstep, BW, freq))
    if (dm):
        print " Smearing per chan (ms) = %.3g" % \
              (1000.0 * dm_smear(dm, chanwidth, freq))

def best_dm_step(maxsmear=0.1, dt=0.00080, dm=0.0, freq=1390.0, numchan=512, chanwidth=0.5):
    """
    best_dm_step(maxsmear=0.1, dt=0.00080, dm=0.0, freq=1390.0, numchan=512, chanwidth=0.5):
        Return the required DM step to keep the total smearing below 'maxsmear' (in ms).
    """
    BW = chanwidth * numchan
    tau_tot = maxsmear/1000.0
    tau_chan = dm_smear(dm, chanwidth, freq)
    tau_samp = dt
    if (tau_tot**2.0 < (tau_chan**2.0+tau_samp**2.0)):
        print "The requested total smearing is smaller than one or more of the components."
        return 0.0
    else:
        return 0.0001205*freq**3.0*2.0/BW*Num.sqrt(tau_tot**2.0-tau_chan**2.0-tau_samp**2.0)

def dm_smear(dm, BW, center_freq):
    """
    dm_smear(dm, BW, center_freq):
        Return the smearing in sec caused by a 'dm' over a bandwidth
        of 'BW' MHz centered at 'center_freq' MHz.
    """
    return dm * BW / (0.0001205 * center_freq * center_freq * center_freq)

def diagonal_DM(dt, chanBW, center_freq):
    """
    diagonal_DM(dt, chanBW, center_freq):
        Return the so-called "diagonal DM" where the smearing across
        one channel is equal to the sample time.
    """
    return (0.0001205 * center_freq * center_freq * center_freq) * dt / chanBW

def pulse_broadening(DM, f_ctr):
    """
    pulse_broadening(DM, f_ctr):
        Return the approximate pulse broadening (tau) in ms due to scattering
        based on the rough relation in Cordes' 'Pulsar Observations I' paper.
        'f_ctr' should be in MHz.  The approximate error is 0.65 in log(tau).
    """
    logDM = Num.log10(DM)
    return 10.0**(-3.59 + 0.129*logDM + 1.02*logDM**2.0 -
                  4.4*Num.log10(f_ctr/1000.0))/1000.0

def guess_DMstep(DM, dt, BW, f_ctr):
    """
    guess_DMstep(DM, dt, BW, f_ctr):
        Choose a reasonable DMstep by setting the maximum smearing across the
        'BW' to equal the sampling time 'dt'.
    """
    return dt*0.0001205*f_ctr**3.0/(0.5*BW)

def delay_from_DM(DM, freq_emitted):
    """
    Return the delay in seconds caused by dispersion, given
    a Dispersion Measure (DM) in cm-3 pc, and the emitted
    frequency (freq_emitted) of the pulsar in MHz.
    """
    if (type(freq_emitted)==type(0.0)):
        if (freq_emitted > 0.0):
            return DM/(0.000241*freq_emitted*freq_emitted)
        else:
            return 0.0
    else:
        return Num.where(freq_emitted > 0.0,
                         DM/(0.000241*freq_emitted*freq_emitted), 0.0)

def smear_plot(dm=[1.0,1000.0], dmstep=1.0, subdmstep=10.0, freq=1390.0,
               numchan=512, numsub=32, chanwidth=0.5, dt=0.000125,
               device='/xwin'):
    """
    smear_plot(dm=[0.0,1000.0], dmstep=1.0, subdmstep=10.0, freq=1390.0,
               numchan=512, numsub=32, chanwidth=0.5, dt=0.000125,
               device='/xwin'):
         Show a plot that displays the expected smearing in ms
         from various effects during a radio pulsar search.
    """
    numpts = 500
    BW = numchan * chanwidth
    subBW = numchan / numsub * chanwidth
    maxDMerror = 0.5 * dmstep
    maxsubDMerror = 0.5 * subdmstep
    ldms = span(Num.log10(dm[0]), Num.log10(dm[1]), numpts)
    dms = 10.0**ldms
    # Smearing from sample rate
    dts = Num.zeros(numpts) + 1000.0 * dt
    # Smearing due to the intrinsic channel width
    chan_smear = 1000.0 * dm_smear(dms, chanwidth, freq)
    # Smearing across the full BW due to max DM mismatch
    BW_smear = Num.zeros(numpts) + \
               1000.0 * dm_smear(maxDMerror, BW, freq)
    # Smearing in each subband due to max DM mismatch
    subband_smear = Num.zeros(numpts) + \
                    1000.0 * dm_smear(maxsubDMerror, subBW, freq)
    total_smear = Num.sqrt(dts**2.0 + chan_smear**2.0 +
                           subband_smear**2.0 + BW_smear**2.0)
    maxval = Num.log10(2.0 * max(total_smear))
    minval = Num.log10(0.5 * min([min(dts), min(chan_smear),
                                    min(BW_smear), min(subband_smear)]))
    Pgplot.plotxy(Num.log10(total_smear), ldms, rangey=[minval, maxval],
                  logx=1, logy=1, labx="Dispersion Measure",
                  laby="Smearing (ms)", device=device)
    ppgplot.pgsch(0.8)
    ppgplot.pgmtxt("t", 1.5, 1.0/12.0, 0.5, "\(2156)\dcenter\u = %gMHz" % freq)
    ppgplot.pgmtxt("t", 1.5, 3.0/12.0, 0.5, "N\dchan\u = %d" % numchan)
    ppgplot.pgmtxt("t", 1.5, 5.0/12.0, 0.5, "N\dsub\u = %d" % numsub)
    ppgplot.pgmtxt("t", 1.5, 7.0/12.0, 0.5, "BW\dchan\u = %gMHz" % chanwidth)
    ppgplot.pgmtxt("t", 1.5, 9.0/12.0, 0.5, "\gDDM = %g" % dmstep)
    ppgplot.pgmtxt("t", 1.5, 11.0/12.0, 0.5, "\gDDM\dsub\u = %g" % subdmstep)
    ppgplot.pgsch(1.0)
    ppgplot.pgmtxt("b", -7.5, 0.95, 1.0, "Total")
    Pgplot.plotxy(Num.log10(dts), ldms, color="green",
                  logx=1, logy=1)
    ppgplot.pgmtxt("b", -6.0, 0.95, 1.0, "Sample Rate")
    Pgplot.plotxy(Num.log10(chan_smear), ldms, color="purple",
                  logx=1, logy=1)
    ppgplot.pgmtxt("b", -4.5, 0.95, 1.0, "Channel")
    Pgplot.plotxy(Num.log10(BW_smear), ldms, color="red",
                  logx=1, logy=1)
    ppgplot.pgmtxt("b", -3.0, 0.95, 1.0, "Full BW")
    Pgplot.plotxy(Num.log10(subband_smear), ldms, color="blue",
                  logx=1, logy=1)
    ppgplot.pgmtxt("b", -1.5, 0.95, 1.0, "Subband")
    ppgplot.pgsci(1)


def search_sensitivity(Ttot, G, BW, chan, freq, T, dm, ddm, dt, Pmin=0.001,
                        Pmax=1.0, W=0.1, polar=2, factor=15.0, pts=1000):
    """
    (periods, S_min) = search_sensitivity(Ttot, G, BW, chan, freq, T, dm,
             ddm, dt, Pmin=0.001, Pmax=1.0, W=0.1, polar=2, factor=15.0, pts=1000):
        Return the approximate limiting flux density for a pulsar
        survey in mJy based of the following characteristics:
            'Ttot' = sky + system temperature (K)
            'G' = forward gain of the antenna (K/Jy)
            'BW' = observing bandwidth (MHz)
            'chan' = number of channels in the filterbank
            'freq' = central observing frequency (MHz)
            'T' = integration time (s)
            'dm' = Dispersion Measure in pc cm^-3
            'ddm' = Dispersion Measure stepsize in pc cm^-3
            'dt' = Sample time for each data point in sec
            'Pmin' = minimum pulsar period (s) (default = 0.001)
            'Pmax' = maximum pulsar period (s) (default = 1.0)
            'W' = duty cycle of pulsar (0-1) (default = 0.1)
            'polar' = number of polarizations (default = 2)
            'factor' = normalization factor that take into account
                limiting SNR, hardware limitations etc. (default = 15.0)
            'pts' = the number of points to calculate
        Note:  This is a _very_ approximate calculation.  For a better
            calculation, see Cordes and Chernoff, ApJ, 482, p971, App. A.
        Observatories:
            Parkes Multibeam: Tsys = 21 K, G = 0.735 K/Jy
    """
    periods = span(Pmin, Pmax, pts)
    widths = Num.sqrt((W * periods)**2.0 +
                      dm_smear(dm, BW/chan, freq)**2.0 + \
                      dm_smear(ddm/2.0, BW, freq)**2.0 + \
                      dt**2.0) / periods
    return (periods, limiting_flux_dens(Ttot, G, BW, T, periods, widths, 
                                        polar=polar, factor=factor))

def smin_noise(Ttot, G, BW, dt):
    """
    smin_noise(Ttot, G, BW, dt):
        Return the 1 sigma Gaussian noise level (mJy) for each time
        series bin in a pulsar data simulation.  Default is for a
        sinusoidal pulse (i.e. W = P / 2) with freq << Nyquist freq.
            'Ttot' = sky + system temperature (K)
            'G' = forward gain of the antenna (K/Jy)
            'BW' = observing bandwidth (MHz)
            'dt' = time per time series bin (s)
        Observatories:
            Parkes Multibeam: Tsys = 21 K, G = 0.735 K/Jy
    """
    return Ttot / (G * Num.sqrt(2 * BW * dt))

def read_profile(filenm, normalize=0):
    """
    read_profile(filenm, normalize=0):
        Read a simple ASCII profile with one bin per line
            from the file 'filenm'.  Comments are allowed
            if they begin with '#'.  The profile is pseudo-
            normalized if 'normalize' is true.
    """
    prof = []
    for line in file(filenm):
        if line.startswith("#"): continue
        else: prof.append(float(line.split()[-1]))
    prof = Num.asarray(prof)
    if normalize:
        prof -= min(prof)
        prof /= max(prof)
    return prof

def calc_phs(MJD, refMJD, f0, f1=0.0, f2=0.0, f3=0.0, f4=0.0, f5=0.0): 
    """
    calc_phs(MJD, refMJD, f0, f1=0.0, f2=0.0, f3=0.0, f4=0.0, f5=0.0):
        Return the rotational phase (0-1) at MJD given a reference MJD and the
            rotational freq (f0) and optional freq derivs (f1-f5).
    """
    t = (MJD-refMJD)*SECPERDAY
    return Num.fmod(t*(f0 +t*(f1/2.0 +
                                t*(f2/6.0 +
                                   t*(f3/24.0 +
                                      t*(f4/120.0 +
                                         t*f5/720.0))))), 1.0)

def calc_freq(MJD, refMJD, f0, f1=0.0, f2=0.0, f3=0.0, f4=0.0, f5=0.0):
    """
    calc_freq(MJD, refMJD, f0, f1=0.0, f2=0.0, f3=0.0, f4=0.0, f5=0.0):
        Return the instantaneous frequency at an MJD given a reference
            MJD and the rotational freq (f0) and optional freq derivs (f1-f5).
    """
    t = (MJD-refMJD)*SECPERDAY
    return f0 + t*(f1 +
                   t*(f2/2.0 +
                      t*(f3/6.0 +
                         t*(f4/24.0 +
                            t*f5/120.0))))

def calc_t0(MJD, refMJD, f0, f1=0.0, f2=0.0, f3=0.0, f4=0.0, f5=0.0):
    """
    calc_t0(MJD, refMJD, f0, f1=0.0, f2=0.0, f3=0.0, f4=0.0, f5=0.0):
        Return the closest previous MJD corresponding to phase=0 of the pulse.
    """
    phs = calc_phs(MJD, refMJD, f0, f1, f2, f3, f4, f5)
    p = 1.0/calc_freq(MJD, refMJD, f0, f1, f2, f3, f4, f5)
    return MJD-phs*p/SECPERDAY


def write_princeton_toa(toa, toaerr, freq, dm, obs='@', name=' '*13):
    """
    Princeton Format

    columns     item
    1-1     Observatory (one-character code) '@' is barycenter
    2-2     must be blank
    16-24   Observing frequency (MHz)
    25-44   TOA (decimal point must be in column 30 or column 31)
    45-53   TOA uncertainty (microseconds)
    69-78   DM correction (pc cm^-3)
    """
    if dm!=0.0:
        print obs+" %13s %8.3f %19.13f %8.2f              %9.4f" % \
              (name, freq, toa, toaerr, dm)
    else:
        print obs+" %13s %8.3f %19.13f %8.2f" % \
              (name, freq, toa, toaerr)

def rotate(arr, bins):
    """
    rotate(arr, bins):
        Return an array rotated by 'bins' places to the left
    """
    bins = bins % len(arr)
    if bins==0:
        return arr
    else:
        return Num.concatenate((arr[bins:], arr[:bins]))

def interp_rotate(arr, bins, zoomfact=10):
    """
    interp_rotate(arr, bins, zoomfact=10):
        Return a sinc-interpolated array rotated by 'bins' places to the left.
            'bins' can be fractional and will be rounded to the closest
            whole-number of interpolated bins.  The resulting vector will
            have the same length as the oiginal.
    """
    newlen = len(arr)*zoomfact
    rotbins = int(Num.floor(bins*zoomfact+0.5)) % newlen
    newarr = sinc_interp.periodic_interp(arr, zoomfact)  
    return rotate(newarr, rotbins)[::zoomfact]

def corr(profile, template):
    """
    corr(profile, template):
        Cross-correlate (using FFTs) a 'profile' and a 'template'.
    """
    return FFT.inverse_real_fft(FFT.real_fft(template) * Num.conjugate(FFT.real_fft(profile)))

def maxphase(profile, template):
    """
    maxphase(profile, template):
        Return the phase offset required to get the 'profile' to best
            match the 'template'.
    """
    return float(Num.argmax(corr(profile, template))) / len(profile)

def linear_interpolate(vector, zoom=10):
    """
    linear_interpolate(vector, zoom=10):
        Linearly interpolate 'vector' by a factor of 'zoom'.
    """
    n = len(vector)
    ivect = Num.zeros(zoom*n, dtype='d')
    nvect = Num.concatenate((vector, vector[:1]))
    ivals = Num.arange(zoom, dtype='d')/zoom
    loy = nvect[0]
    for ii in range(n):
        hiy = nvect[ii+1]
        ivect[ii*zoom:(ii+1)*zoom] = ivals*(hiy-loy) + loy
        loy = hiy
    return ivect

def downsample(vector, factor):
    """
    downsample(vector, factor):
        Downsample (i.e. co-add consecutive numbers) a short section
            of a vector by an integer factor.
    """
    if (len(vector) % factor):
        print "Lenght of 'vector' is not divisible by 'factor'=%d!" % factor
        return 0
    newvector = Num.reshape(vector, (len(vector)/factor, factor))
    return Num.add.reduce(newvector, 1)

def measure_phase_corr(profile, template, zoom=10):
    """
    measure_phase_corr(profile, template, zoom=10):
        Return the phase offset required to get the 'profile' to best
            match the 'template', each of which has been interpolated
            by a factor of 'zoom'.
    """
    zoomprof = zoomtemp = zoom
    if (len(template) != len(profile)):
        if (len(template)%len(profile) == 0):
            zoomprof = zoom*len(template)/len(profile)
        else:
            print "Warning!:  The lengths of the template (%d) and profile (%d)" % \
                  (len(template), len(profile))
            print "           are not the same!"
    #itemp = linear_interpolate(rotate(template, Num.argmax(template)), zoomtemp)
    itemp = linear_interpolate(template, zoomtemp)
    iprof = linear_interpolate(profile, zoomprof)
    return maxphase(iprof, itemp)

def spike_profile(N, phase, fwhm):
    """
    spike_profile(N, phase, fwhm):
        Return a triangular pulse profile with 'N' bins and
        an integrated 'flux' of 1 unit.
            'N' = the number of points in the profile
            'phase' = the pulse phase (0-1)
            'fwhm' = the triangular pulses full width at half-max
    """
    phsval = Num.arange(N, dtype='d') / float(N)
    peakst = 0.5 - fwhm
    peakend = 0.5 + fwhm
    normalize = 1.0 / fwhm
    if (mean < 0.5):
        phsval = Num.where(Num.greater(phsval, mean+0.5),
                           phsval-1.0, phsval)
    else:
        phsval = Num.where(Num.less(phsval, mean-0.5),
                               phsval+1.0, phsval)
    return Num.where(Num.less_equal(phsval, 0.5),
                     Num.where(Num.less_equal(phsval, peakst),
                               0.0, (phsval - peakst) *
                               normalize * normalize),
                     Num.where(Num.greater(phsval, peakend),
                               0.0, (1.0 - (phsval - 0.5) *
                                     normalize) * normalize))

def harm_to_sum(fwhm):
    """
    harm_to_sum(fwhm):
        For an MVMD profile returns the optimal number
            of harmonics to sum incoherently
    """
    fwhms = [0.0108, 0.0110, 0.0113, 0.0117, 0.0119, 0.0124, 0.0127, 0.0132,
             0.0134, 0.0140, 0.0145, 0.0151, 0.0154, 0.0160, 0.0167, 0.0173,
             0.0180, 0.0191, 0.0199, 0.0207, 0.0220, 0.0228, 0.0242, 0.0257,
             0.0273, 0.0295, 0.0313, 0.0338, 0.0366, 0.0396, 0.0437, 0.0482,
             0.0542, 0.0622, 0.0714, 0.0836, 0.1037, 0.1313, 0.1799, 0.2883]
    return len(fwhms)-bisect.bisect(fwhms, fwhm)+1

def expcos_profile(N, phase, fwhm):
    """
    expcos_profile(N, phase, fwhm):
        Return a pulse profile with 'N' bins and an integrated 'flux'
        of 1 unit based on the 'Exponentiated Sinusoid'.
            'N' = the number of points in the profile
            'phase' = the pulse phase (0-1)
            'fwhm' = pulse full width at half-max (0.0 < fwhm <= 0.5)
    """
    from simple_roots import secant
    def fwhm_func(k, fwhm=fwhm):
        if (fwhm < 0.02):
            return Num.arccos(1.0-Num.log(2.0)/k)/PI-fwhm
        else:
            return Num.arccos(Num.log(0.5*(Num.exp(k)+
                                           Num.exp(-k)))/k)/PI-fwhm
    phsval = TWOPI * Num.arange(N, dtype='d') / float(N)
    phi = -phase * TWOPI
    if (fwhm >= 0.5):
        return Num.cos(phsval + phi) + 1.0
    elif (fwhm < 0.02):
        # The following is from expanding of iO(x) as x->Infinity.
        k = Num.log(2.0) / (1.0 - Num.cos(PI * fwhm))
        # print "Expansion:  k = %f  FWHM = %f" % (k, fwhm_func(k, 0.0))
        phsval = Num.fmod(phsval + phi, TWOPI)
        phsval = Num.where(Num.greater(phsval, PI),
                           phsval - TWOPI, phsval)
        denom = ((1 + 1/(8*k) + 9/(128*k*k) + 75/(1024*k**3) + 
                 3675/(32768*k**4) + 59535/(262144*k**5)) / Num.sqrt(TWOPI*k))
        return Num.where(Num.greater(Num.fabs(phsval/TWOPI), 3.0*fwhm), 0.0, 
                         Num.exp(k*(Num.cos(phsval)-1.0))/denom)
    else:
        k = secant(fwhm_func, 1e-8, 0.5)
        norm = 1.0 / (i0(k) - Num.exp(-k))
        # print "Full Calc:  k = %f  FWHM = %f" % (k, fwhm_func(k, 0.0))
    if (k < 0.05):
        tmp = Num.cos(phsval + phi)
        tmp2 = tmp * tmp
        return norm * (k * (tmp + 1) +
                       k * k * (tmp2 - 1.0) / 2.0 +
                       k * k * k * (tmp2 * tmp + 1.0) / 6.0)
    else:
        return norm * (Num.exp(k * Num.cos(phsval + phi)) -
                       Num.exp(-k))

def gaussian_profile(N, phase, fwhm):
    """
    gaussian_profile(N, phase, fwhm):
        Return a gaussian pulse profile with 'N' bins and
        an integrated 'flux' of 1 unit.
            'N' = the number of points in the profile
            'phase' = the pulse phase (0-1)
            'fwhm' = the gaussian pulses full width at half-max
        Note:  The FWHM of a gaussian is approx 2.35482 sigma
    """
    sigma = fwhm / 2.35482
    mean = phase % 1.0
    phsval = Num.arange(N, dtype='d') / float(N)
    if (mean < 0.5):
        phsval = Num.where(Num.greater(phsval, mean+0.5),
                           phsval-1.0, phsval)
    else:
        phsval = Num.where(Num.less(phsval, mean-0.5),
                           phsval+1.0, phsval)
    try:
        zs = (phsval-mean)/sigma
        okzinds = Num.compress(Num.fabs(zs)<20.0, Num.arange(N))
        okzs = Num.take(zs, okzinds)
        retval = Num.zeros(N, 'd')
        Num.put(retval, okzinds, Num.exp(-0.5*(okzs)**2.0)/(sigma*Num.sqrt(2*PI)))
        return retval
    except OverflowError:
        print "Problem in gaussian prof:  mean = %f  sigma = %f" % \
              (mean, sigma)
        return Num.zeros(N, 'd')
        
def gauss_profile_params(profile, output=0):
    """
    gauss_profile_params(profile, output=0):
        Return parameters of a best-fit gaussian to a profile.
        The funtion returns a tuple containg the following values:
           ret[0] = Best-fit gaussian integrated 'flux'.
           ret[1] = Best-fit gaussian FWHM.
           ret[2] = Best-fit gaussian phase (0.0-1.0).
           ret[3] = Baseline (i.e. noise) average value.
           ret[4] = Residuals average value.
           ret[5] = Residuals standard deviation.
        If 'output' is true, the fit will be plotted and 
           the return values will be printed.
    """
    def funct(afpo, profile):
        return afpo[0] * gaussian_profile(len(profile), afpo[2], afpo[1]) \
               + afpo[3] - profile
    ret = leastsq(funct, [max(profile)-min(profile),
                          0.25, Num.argmax(profile)/float(len(profile)),
                          min(profile)], args=(profile))
    if (output):
        phases = Num.arange(0.0, 1.0,
                            1.0 / len(profile)) + 0.5 / len(profile)
        Pgplot.plotxy(profile, phases, rangex=[0.0, 1.0],
                      labx='Pulse Phase', laby='Pulse Intensity')
    bestfit = ret[0][0] * gaussian_profile(len(profile),
                                           ret[0][2], ret[0][1]) \
              + ret[0][3]
    if (output):
        Pgplot.plotxy(bestfit, phases, color='red')
        Pgplot.closeplot()
    residuals = bestfit - profile
    resid_avg = mean(residuals)
    resid_std = std(residuals)
    if (output):
        Pgplot.plotxy(residuals, phases, rangex=[0.0, 1.0],
                      rangey=[min(residuals) - 2 * resid_std,
                              max(residuals) + 2 * resid_std],
                      labx='Pulse Phase', laby='Residuals',
                      line=None, symbol=3)
        ppgplot.pgerrb(6, phases, residuals,
                       Num.zeros(len(residuals), 'd') + \
                       resid_std, 2)
        Pgplot.plotxy([resid_avg, resid_avg], [0.0, 1.0], line=2)
        Pgplot.closeplot()
        print ""
        print "  Best-fit gaussian integrated 'flux'  = ", ret[0][0]
        print "               Best-fit gaussian FWHM  = ", ret[0][1]
        print "    Best-fit gaussian phase (0.0-1.0)  = ", ret[0][2]
        print "        Baseline (i.e. noise) average  = ", ret[0][3]
        print "                    Residuals average  = ", resid_avg
        print "         Residuals standard deviation  = ", resid_std
        print ""
    return (ret[0][0], ret[0][1], ret[0][2], ret[0][3], resid_avg, resid_std)

def twogauss_profile_params(profile, output=0):
    """
    twogauss_profile_params(profile, output=0):
        Return parameters of a two best-fit gaussians to a profile.
        The function returns a tuple containg the following values:
           ret[0] = Best-fit gaussian integrated 'flux'.
           ret[1] = Best-fit gaussian FWHM.
           ret[2] = Best-fit gaussian phase (0.0-1.0).
           ret[3] = Best-fit gaussian integrated 'flux'.
           ret[4] = Best-fit gaussian FWHM.
           ret[5] = Best-fit gaussian phase (0.0-1.0).
           ret[6] = Baseline (i.e. noise) average value.
           ret[7] = Residuals average value.
           ret[8] = Residuals standard deviation.
        If 'output' is true, the fit will be plotted and
           the return values will be printed.
    """
    def yfunct(afpo, n):
        return afpo[0] * gaussian_profile(n, afpo[2], afpo[1]) + \
               afpo[3] * gaussian_profile(n, afpo[5], afpo[4]) + afpo[6]
    def min_funct(afpo, profile):
        return yfunct(afpo, len(profile)) - profile
    ret = leastsq(min_funct, [max(profile)-min(profile),
                              0.05,
                              Num.argmax(profile)/float(len(profile)),
                              0.2 * max(profile)-min(profile),
                              0.1,
                              Num.fmod(Num.argmax(profile)/float(len(profile))+0.5, 1.0),
                              min(profile)], args=(profile))
    if (output):
        phases = Num.arange(0.0, 1.0,
                                1.0 / len(profile)) + 0.5 / len(profile)
        Pgplot.plotxy(profile, phases, rangex=[0.0, 1.0],
                      labx='Pulse Phase', laby='Pulse Intensity')
    bestfit = yfunct(ret[0], len(profile))
    if (output):
        Pgplot.plotxy(bestfit, phases, color='red')
        Pgplot.closeplot()
    residuals = bestfit - profile
    resid_avg = mean(residuals)
    resid_std = std(residuals)
    if (output):
        Pgplot.plotxy(residuals, phases, rangex=[0.0, 1.0],
                      rangey=[min(residuals) - 2 * resid_std,
                              max(residuals) + 2 * resid_std],
                      labx='Pulse Phase', laby='Residuals',
                      line=None, symbol=3)
        ppgplot.pgerrb(6, phases, residuals,
                       Num.zeros(len(residuals), 'd') + \
                       resid_std, 2)
        Pgplot.plotxy([resid_avg, resid_avg], [0.0, 1.0], line=2)
        Pgplot.closeplot()
        print ""
        print "  Best-fit gaussian integrated 'flux'  = ", ret[0][0]
        print "               Best-fit gaussian FWHM  = ", ret[0][1]
        print "    Best-fit gaussian phase (0.0-1.0)  = ", ret[0][2]
        print "  Best-fit gaussian integrated 'flux'  = ", ret[0][3]
        print "               Best-fit gaussian FWHM  = ", ret[0][4]
        print "    Best-fit gaussian phase (0.0-1.0)  = ", ret[0][5]
        print "        Baseline (i.e. noise) average  = ", ret[0][6]
        print "                    Residuals average  = ", resid_avg
        print "         Residuals standard deviation  = ", resid_std
        print ""
    return (ret[0][0], ret[0][1], ret[0][2], ret[0][3], ret[0][4],
            ret[0][5], ret[0][6], resid_avg, resid_std)




def estimate_flux_density(profile, N, dt, Ttot, G, BW, prof_stdev, display=0):
    """
    estimate_flux_density(profile, N, dt, Ttot, G, BW, prof_stdev, display=0):
        Return an estimate of the flux density (mJy) of a pulsar.
            'profile' = the pulse profile you are using
            'N' = number of time series bins folded
            'dt' = time per time series bin (s)
            'Ttot' = sky + system temperature (K)
            'G' = forward gain of the antenna (K/Jy)
            'BW' = observing bandwidth (MHz)
            'prof_stdev' = profile standard deviation
            'display' = if set, the gaussian fit plots are shown
        Observatories:
            Parkes Multibeam: Tsys = 21 K, G = 0.735 K/Jy
    """
    (amp, fwhm, phase, offset, resid_avg, resid_std) = \
          gauss_profile_params(profile, display)
    T = N * dt
    norm_fact = (prof_stdev * len(profile)) / \
                 smin_noise(Ttot, G, BW, T / len(profile))
    return Num.add.reduce(profile - offset) / norm_fact

def max_spike_power(FWHM):
    """
    max_spike_power(FWHM):
        Return the (approx.) ratio of the highest power from a
        triangular spike pulse profile to the power from a
        perfect sinusoidal pulse profile.  In other words, if a
        sine gives you a power of 1, what power does a spike profile
        give you?  Both the spike and the sine are assumed to have
        an area under one full pulse of 1 unit.  Note:  A gaussian
        profile gives almost identical powers as a spike profile
        of the same width.  This expression was determined using
        a least-squares fit (Max abs error ~ 0.016).
            'FWHM' is the full width at half-max of the spike.
                (0.0 < FWHM <= 0.5)
    """
    return ((36.4165309504 * FWHM - 32.0107844537) * FWHM \
           + 0.239948319674) * FWHM + 4.00277916584

def num_spike_powers(FWHM):
    """
    num_spike_powers(FWHM):
        Return the (approx.) number of powers from a triangular spike
        pulse profile which are greater than one half the power
        perfect sinusoidal pulse profile.  Both the spike and the
        sine are assumed to have an area under one full pulse of 1 unit.
        Note:  A gaussian profile gives almost identical numbers of
        high powers as a spike profile of the same width.  This
        expression was determined using a least-squares fit.
        (Errors get large as FWHM -> 0).
            'FWHM' is the full width at half-max of the spike.
                (0.0 < FWHM <= 0.5)
    """
    return -3.95499721563e-05 / FWHM**2 + 0.562069634689 / FWHM - \
           0.683604041138

def incoherent_sum(amps):
    """
    incoherent_sum(amps):
        Given a series of complex Fourier amplitudes, return a vector
            showing the accumulated incoherently-summed powers.
    """
    return Num.add.accumulate(Num.absolute(amps)**2.0)

def coherent_sum(amps):
    """
    coherent_sum(amps):
        Given a series of complex Fourier amplitudes, return a vector
            showing the accumulated coherently-summed powers.
    """
    phss = Num.arctan2(amps.imag, amps.real)
    phs0 = phss[0]
    phscorr = phs0 - Num.fmod((Num.arange(len(amps), dtype='d')+1.0)*phs0, TWOPI)
    sumamps = Num.add.accumulate(amps*Num.exp(complex(0.0, 1.0)*phscorr))
    return Num.absolute(sumamps)**2.0

def prob_power(power):
    """
    prob_power(power):
        Return the probability for noise to exceed a normalized power
        level of 'power' in a power spectrum.
    """
    return Num.exp(-power)

def equivalent_gaussian_sigma(p):
    """
    equivalent_gaussian_sigma(p):
        Return the equivalent gaussian sigma corresponding
            to the cumulative gaussian probability p.  In other
            words, return x, such that Q(x) = p, where Q(x) is the
            cumulative normal distribution.  For very small 
    """
    logp = Num.log(p)
    if type(1.0) == type(logp):
        if logp > -30.0:
            return ndtri(1.0 - p)
        else:
            return extended_equiv_gaussian_sigma(logp)
    else:  # Array input
        return Num.where(logp>-30.0,
                         ndtri(1.0-p),
                         extended_equiv_gaussian_sigma(logp))

def extended_equiv_gaussian_sigma(logp):
    """
    extended_equiv_gaussian_sigma(logp):
        Return the equivalent gaussian sigma corresponding
            to the log of the cumulative gaussian probability logp.
            In other words, return x, such that Q(x) = p, where Q(x)
            is the cumulative normal distribution.  This version uses
            the rational approximation from Abramowitz and Stegun,
            eqn 26.2.23.  Using the log(P) as input gives a much
            extended range.
    """
    t = Num.sqrt(-2.0 * logp)
    num = 2.515517 + t * (0.802853 + t * 0.010328)
    denom = 1.0 + t * (1.432788 + t * (0.189269 + t * 0.001308))
    return t - num / denom

def log_asymtotic_incomplete_gamma(a, z):
    """
    log_asymtotic_incomplete_gamma(a, z):
        Return the log of the incomplete gamma function in its
            asymtotic limit as z->infty.  This is from Abramowitz
            and Stegun eqn 6.5.32.
    """
    x = 1.0
    newxpart = 1.0
    term = 1.0
    ii = 1
    while (Num.fabs(newxpart) > 1e-15):
        term *= (a - ii)
        newxpart = term / z**ii
        x += newxpart
        ii += 1
    return (a-1.0)*Num.log(z) - z + Num.log(x)

def log_asymtotic_gamma(z):
    """
    log_asymtotic_gamma(z):
        Return the log of the gamma function in its asymtotic limit
            as z->infty.  This is from Abramowitz and Stegun eqn 6.1.41.
    """
    x = (z-0.5) * Num.log(z) - z + 0.91893853320467267
    y = 1.0/(z*z)
    x += (((- 5.9523809523809529e-4 * y
            + 7.9365079365079365079365e-4) * y
            - 2.7777777777777777777778e-3) * y
            + 8.3333333333333333333333e-2) / z;
    return x

def prob_sum_powers(power, nsum):
    """
    prob_sum_powers(power, nsum):
        Return the probability for noise to exceed 'power' in
        the sum of 'nsum' normalized powers from a power spectrum.
    """
    # Notes:
    # prob_sum_powers(power, nsum)
    # = scipy.special.gammaincc(nsum, power)
    # = statdists.chi_prob(power*2, nsum*2)
    # = scipy.special.chdtrc(nsum*2, power*2)
    # = Q(power*2|nsum*2)  (from A&S 26.4.19)
    # = Gamma(nsum,power)/Gamma(nsum)
    # = [Gamma(nsum) - gamma(nsum,power)]/Gamma(nsum)
    return chdtrc(2*nsum, 2.0*power)

def log_prob_sum_powers(power, nsum):
    """
    log_prob_sum_powers(power, nsum):
        Return the log of the probability for noise to exceed
        'power' in the sum of 'nsum' normalized powers from a
        power spectrum.  This version uses allows the use of
        very large powers by using asymtotic expansions from
        Abramowitz and Stegun Chap 6.
    """
    # Notes:
    # prob_sum_powers(power, nsum)
    # = scipy.special.gammaincc(nsum, power)
    # = statdists.chi_prob(power*2, nsum*2)
    # = scipy.special.chdtrc(nsum*2, power*2)
    # = Q(power*2|nsum*2)  (from A&S 26.4.19)
    # = Gamma(nsum,power)/Gamma(nsum)
    # = [Gamma(nsum) - gamma(nsum,power)]/Gamma(nsum)
    if type(1.0) == type(power):
        if power < 100.0:
            return Num.log(prob_sum_powers(power, nsum))
        else:
            return log_asymtotic_incomplete_gamma(nsum, power) - \
                   log_asymtotic_gamma(nsum)
    else:
        return Num.where(power < 100.0,
                         Num.log(prob_sum_powers(power, nsum)),
                         log_asymtotic_incomplete_gamma(nsum, power) - \
                         log_asymtotic_gamma(nsum))

def sigma_power(power):
    """
    sigma_power(power):
        Return the approximate equivalent Gaussian sigma for noise
        to exceed a normalized power level given as 'power'
        in a power spectrum.
    """
    if type(1.0) == type(power):
        if power > 36.0:
            return Num.sqrt(2.0 * power - Num.log(PI * power))
        else:
            return equivalent_gaussian_sigma(prob_power(power))
    else:
        return Num.where(power > 36.0,
                         Num.sqrt(2.0 * power - Num.log(PI * power)),
                         extended_equiv_gaussian_sigma(log_prob_sum_powers(power, 1)))
        
def sigma_sum_powers(power, nsum):
    """
    sigma_sum_powers(power, nsum):
        Return the approximate equivalent Gaussian sigma for noise
        to exceed a sum of 'nsum' normalized powers given by 'power'
        in a power spectrum.
    """
    if type(1.0) == type(power):
        if power < 100.0:
            return equivalent_gaussian_sigma(prob_sum_powers(power, nsum))
        else:
            return extended_equiv_gaussian_sigma(log_prob_sum_powers(power, nsum))
    else: # Array input
        return Num.where(power < 100.0,
                         equivalent_gaussian_sigma(prob_sum_powers(power, nsum)),
                         extended_equiv_gaussian_sigma(log_prob_sum_powers(power, nsum)))

def power_at_sigma(sigma):
    """
    power_at_sigma(sigma):
        Return the approximate normalized power level that is
        equivalent to a detection of significance 'sigma'.
    """
    return sigma**2 / 2.0 + Num.log(Num.sqrt(PIBYTWO)
                                      * sigma)
def powersum_at_sigma(sigma, nsum):
    """
    powersum_at_sigma(sigma, nsum):
        Return the approximate sum of 'nsum' normalized powers that is
        equivalent to a detection of significance 'sigma'.
    """
    return 0.5 * chdtri(2.0 * nsum, 1.0 - ndtr(sigma))

def cand_sigma(N, power):
    """
    cand_sigma(N, power):
        Return the sigma of a candidate found in a power
        spectrum of 'N' bins after taking into account the
        number of bins searched.
    """
    return ndtri(1.0 - N * prob_power(power))

def fft_max_pulsed_frac(N, numphot, sigma=3.0):
    """
    fft_max_pulsed_frac(N, numphot, sigma=3.0):
        Return the approximate maximum pulsed fraction for a
        sinusoidal signal that _wasn't_ found in a FFT-based
        search.  'N' is the number of bins searched in the FFT.
        'numphot' is the number of photons present in the data.
        And 'sigma' is your confidence (in sigma) that you
        have in expressing this limit.
    """
    # The following is the power level required to get a
    # noise spike that would appear somewhere in N bins
    # at the 'sigma' level
    power_required = -Num.log((1.0-ndtr(sigma))/N)
    return Num.sqrt(4.0 * numphot * power_required)/N

def p_to_f(p, pd, pdd=None):
   """
   p_to_f(p, pd, pdd=None):
      Convert period, period derivative and period second
      derivative to the equivalent frequency counterparts.
      Will also convert from f to p.
   """
   f = 1.0 / p
   fd = -pd / (p * p)
   if (pdd==None):
       return [f, fd]
   else:
       if (pdd==0.0):
           fdd = 0.0
       else:
           fdd = 2.0 * pd * pd / (p**3.0) - pdd / (p * p)
       return [f, fd, fdd]

def pferrs(porf, porferr, pdorfd=None, pdorfderr=None):
    """
    pferrs(porf, porferr, pdorfd=None, pdorfderr=None):
       Calculate the period or frequency errors and
       the pdot or fdot errors from the opposite one.
    """
    if (pdorfd==None):
        return [1.0 / porf, porferr / porf**2.0]
    else:
        forperr = porferr / porf**2.0
        fdorpderr = Num.sqrt((4.0 * pdorfd**2.0 * porferr**2.0) / porf**6.0 +
                               pdorfderr**2.0 / porf**4.0)
        [forp, fdorpd] = p_to_f(porf, pdorfd)
        return [forp, forperr, fdorpd, fdorpderr]

def pdot_from_B(p, B):
    """
    pdot_from_B(p, B):
        Return a pdot (or p, actually) that a pulsar with spin
        period (or pdot) 'p' (in sec) would experience given a
        magnetic field strength 'B' in gauss.
    """
    return (B / 3.2e19)**2.0 / p

def pdot_from_age(p, age):
    """
    pdot_from_B(p, B):
        Return the pdot that a pulsar with spin period 'p' (in sec)
        would experience given a characteristic age 'age' (in yrs).
    """
    return p / (2.0 * age * SECPERJULYR)

def pulsar_age(f, fdot, n=3, fo=1e99):
    """
    pulsar_age(f, fdot, n=3, fo=1e99):
        Return the age of a pulsar (in years) given the spin frequency
        and frequency derivative.  By default, the characteristic age
        is returned (assuming a braking index 'n'=3 and an initial
        spin freqquency fo >> f).  But 'n' and 'fo' can be set.
    """
    return -f / ((n-1.0) * fdot) * (1.0 - (f / fo)**(n-1.0)) / SECPERJULYR

def pulsar_edot(f, fdot, I=1.0e45):
    """
    pulsar_edot(f, fdot, I=1.0e45):
        Return the pulsar Edot (in erg/s) given the spin frequency and
        frequency derivative. The NS moment of inertia is assumed to be
        I = 1.0e45 g cm^2
    """
    return -4.0 * PI * PI * I * f * fdot

def pulsar_B(f, fdot):
    """
    pulsar_B(f, fdot):
        Return the estimated pulsar surface magnetic field strength
        (in Gauss) given the spin frequency and frequency derivative.
    """
    return 3.2e19 * Num.sqrt(-fdot/f**3.0)

def psr_info(porf, pdorfd, time=None, input=None):
    """
    psr_info(porf, pdorfd, input=None):
        Print a list of standard derived pulsar parameters based
        on the period (or frequency) and its first derivative.  The
        routine will automatically assume you are using periods if
        'porf' <= 1.0 and frequencies otherwise.  You can override this
        by setting input='p' or 'f' appropriately.
    """
    if ((input==None and porf > 1.0) or
        (input=='f' or input=='F')):
        pdorfd = - pdorfd / (porf * porf)
        porf = 1.0 / porf
    I = 1.0e45  # Moment of Inertia in g cm^2
    Edot = 4.0 * PI * PI * I * pdorfd / porf ** 3.0
    Bo = 3.2e19 * Num.sqrt(porf * pdorfd)
    age = porf / (2.0 * pdorfd * 31557600.0) 
    [f, fd] = p_to_f(porf, pdorfd)
    print ""
    print "             Period = %f s" % porf
    print "              P-dot = %g s/s" % pdorfd
    print "          Frequency = %f Hz" % f
    print "              F-dot = %g Hz/s" % fd
    if (time):
        print "       Fourier Freq = %g bins" % (f * time)
        print "      Fourier F-dot = %g bins" % (fd * time * time)
    print "              E-dot = %g ergs/s" % Edot
    print "    Surface B Field = %g gauss" % Bo
    print " Characteristic Age = %g years" % age
    print "          Assumed I = %g g cm^2" % I
    print ""

#include "presto.h"
#include "cpgplot.h"

#ifdef USEDMALLOC
#include "dmalloc.h"
#endif

#define DEBUGOUT 0
 
/* Note:  zoomlevel is simply (LOGDISPLAYNUM-Log_2(numbins)) */
#define LOGNUMHARMBINS    7  /* 128: Number of bins to show for each harmonic */
#define LOGDISPLAYNUM     10 /* 1024: Maximum number of points to display at once */
#define LOGLOCALCHUNK     4  /* 16: Chunk size for polynomial fit */
#define LOGMINBINS        5  /* 32 points */
#define LOGMAXBINS        22 /* 4M points */
#define LOGINITIALNUMBINS 16 /* 65536: The initial number of bins to plot */
#define NUMHARMBINS    (1<<LOGNUMHARMBINS)
#define DISPLAYNUM     (1<<LOGDISPLAYNUM)
#define LOCALCHUNK     (1<<LOGLOCALCHUNK)
#define MINBINS        (1<<LOGMINBINS)
#define MAXBINS        (1<<LOGMAXBINS)
#define INITIALNUMBINS (1<<LOGINITIALNUMBINS)

static long long N;    /* Number of points in the original time series */
static long long Nfft; /* Number of bins in the FFT */
static double T;       /* The time duration of FFT */
static float r0;       /* The value of the zeroth Fourier freq */
static infodata idata;
static FILE *fftfile;
static double norm_const=0.0;  /* Used if the user specifies a power normalization. */

typedef struct fftpart {
  int rlo;          /* Lowest Fourier freq displayed */
  int numamps;      /* Number of raw amplitudes */
  float maxrawpow;  /* The highest raw power present */
  float *rawpowers; /* The raw powers */
  float *medians;   /* The local median values (chunks of size LOCALCHUNK bins) */
  float *normvals;  /* The values to use for normalization (default is median/-log(0.5)) */
  fcomplex *amps;   /* Raw FFT amplitudes    */
} fftpart;

typedef struct fftview {
  double dr;        /* Fourier frequency stepsize (2.0**(-zoomlevel)) */
  double centerr;   /* The center Fourier freq to plot */
  int lor;          /* The lowest Fourier freq to plot */
  int zoomlevel;    /* Positive = zoomed in, Negative = zoomed out */
  int numbins;      /* The number of full bins from low to high to display */
  float maxpow;     /* The maximum normalized power in the view */
  float powers[DISPLAYNUM];  /* The normalized powers to display */
  double rs[DISPLAYNUM];     /* The corresponding Fourier freqs */
} fftview;

static int floor_log2(int nn)
{
  int ii=0;
  
  if (nn <= 0)
    return -1;
  while (nn >> 1){
    ii++;
    nn >>= 1;
  }
  return ii;
}


static double plot_fftview(fftview *fv, float maxpow)
/* The return value is offsetf */
{
  int ii;
  double lof, hif, offsetf=0.0;
  float *freqs;

  cpgsave();
  cpgbbuf();

  /* Set the "Normal" plotting attributes */

  cpgsls(1);
  cpgslw(1);
  cpgsch(1);
  cpgsci(1);

  if (maxpow==0.0) /* Autoscale for the maximum value */
    maxpow = 1.1 * fv->maxpow;

  lof = fv->lor / T;
  hif = (fv->lor + fv->dr * DISPLAYNUM) / T;
  offsetf = 0.0;

  /* Period Labels */
  if (fv->zoomlevel >= 0 && lof > 1.0){
    double lop, hip, offsetp=0.0;
    lop = 1.0/lof;
    hip = 1.0/hif;
    offsetp = 0.0;
    
    if ((lop-hip)/hip < 0.001){
      int numchar;
      char label[50];
      
      offsetp = 0.5*(hip+lop);
      numchar = snprintf(label, 50, "Period - %.15g (s)", offsetp);
      cpgmtxt("T", 3, 0.5, 0.5, label);
    } else {
      cpgmtxt("T", 3, 0.5, 0.5, "Period (s)");
    }
    cpgswin(lop-offsetp, hip-offsetp, 0.0, maxpow);
    cpgbox("CIMST", 0.0, 0, "", 0.0, 0);
  }

  /* Frequency Labels */

  if ((hif-lof)/hif < 0.001){
    int numchar;
    char label[50];

    offsetf = 0.5*(hif+lof);
    numchar = snprintf(label, 50, "Frequency - %.15g (Hz)", offsetf);
    cpgmtxt("B", 3, 0.5, 0.5, label);
  } else {
    cpgmtxt("B", 3, 0.5, 0.5, "Frequency (Hz)");
  }
  cpgswin(lof-offsetf, hif-offsetf, 0.0, maxpow);
  if (fv->zoomlevel >= 0 && lof > 1.0)
    cpgbox("BINST", 0.0, 0, "BCNST", 0.0, 0);
  else
    cpgbox("BCINST", 0.0, 0, "BCNST", 0.0, 0);

  /* Plot the spectrum */

  freqs = gen_fvect(DISPLAYNUM);
  for (ii=0; ii<DISPLAYNUM; ii++)
    freqs[ii] = fv->rs[ii]/T - offsetf;
  if (fv->zoomlevel > 0){ /* Magnified power spectrum */
    cpgline(DISPLAYNUM, freqs, fv->powers);
  } else { /* Down-sampled power spectrum */
    for (ii=0; ii<DISPLAYNUM; ii++){
      cpgmove(freqs[ii], 0.0);
      cpgdraw(freqs[ii], fv->powers[ii]);
    }
  }
  free(freqs);
  cpgmtxt("L", 3, 0.5, 0.5, "Normalized Power");
  cpgebuf();
  cpgunsa();
  return offsetf;
}


static fftview *get_fftview(double centerr, int zoomlevel, fftpart *fp)
{
  int ii;
  double split=1.0/(double)LOCALCHUNK;
  float powargr, powargi;
  fftview *fv;

  fv = (fftview *)malloc(sizeof(fftview));
  fv->zoomlevel = zoomlevel;
  fv->centerr = centerr;
  if (zoomlevel > 0){ /* Magnified power spectrum */
    int numbetween, nextbin, index;
    fcomplex *interp;

    numbetween = (1 << zoomlevel);
    fv->numbins = DISPLAYNUM / numbetween;
    fv->dr = 1.0 / (double) numbetween;
    fv->lor = (int) floor(centerr - 0.5 * fv->numbins);
    if (fv->lor < 0) fv->lor = 0;
    /* fv->lor = floor(numbewteen * fv->lor + 0.5) / numbetween; */
    interp = corr_rz_interp(fp->amps, fp->numamps, numbetween,
			    fv->lor - fp->rlo, 0.0, DISPLAYNUM*2,
			    LOWACC, &nextbin);
    if (norm_const==0.0){
      for (ii=0; ii<DISPLAYNUM; ii++){
	fv->rs[ii] = fv->lor + ii * fv->dr;
	index = (int) ((fv->rs[ii] - fp->rlo) * split + 0.5);
	fv->powers[ii] = POWER(interp[ii].r, interp[ii].i) * fp->normvals[index];
      }
    } else {
      for (ii=0; ii<DISPLAYNUM; ii++){
	fv->rs[ii] = fv->lor + ii * fv->dr;
	fv->powers[ii] = POWER(interp[ii].r, interp[ii].i) * norm_const;
      }
    }
    free(interp);
  } else { /* Down-sampled power spectrum */
    int jj, powindex, normindex, binstocombine;
    float *tmprawpwrs, maxpow;

    binstocombine = (1 << abs(zoomlevel));
    fv->numbins = DISPLAYNUM * binstocombine;
    fv->dr = (double) binstocombine;
    fv->lor = (int) floor(centerr - 0.5 * fv->numbins);
    if (fv->lor < 0) fv->lor = 0;
    tmprawpwrs = gen_fvect(fv->numbins);
    if (norm_const==0.0){
      for (ii=0; ii<fv->numbins; ii++){
	powindex = (int) (fv->lor - fp->rlo + ii + 0.5);
	normindex = (int) (powindex * split);
	tmprawpwrs[ii] = fp->rawpowers[powindex] * fp->normvals[normindex];
      }
    } else {
      for (ii=0; ii<fv->numbins; ii++){
	powindex = (int) (fv->lor - fp->rlo + ii + 0.5);
	tmprawpwrs[ii] = fp->rawpowers[powindex] * norm_const;
      }
    }
    powindex = 0;
    for (ii=0; ii<DISPLAYNUM; ii++){
      maxpow = 0.0;
      for (jj=0; jj<binstocombine; jj++, powindex++)
	if (tmprawpwrs[powindex] > maxpow) maxpow = tmprawpwrs[powindex];
      fv->rs[ii] = fv->lor + ii * fv->dr;
      fv->powers[ii] = maxpow;
    }
  }
  fv->maxpow = 0.0;
  for (ii=0; ii<DISPLAYNUM; ii++)
    if (fv->powers[ii] > fv->maxpow) fv->maxpow = fv->powers[ii];
  return fv;
}


static fftpart *get_fftpart(int rlo, int numr)
{
  int ii, jj, index;
  float powargr, powargi, tmppwr, chunk[LOCALCHUNK];
  fftpart *fp;

  fp = (fftpart *)malloc(sizeof(fftpart));
  fp->rlo = rlo;
  fp->numamps = numr;
  fp->amps = read_fcomplex_file(fftfile, rlo, fp->numamps);
  if (rlo==0){
    fp->amps[0].r = 1.0;
    fp->amps[0].i = 0.0;
  }
  fp->rawpowers = gen_fvect(fp->numamps);
  fp->medians = gen_fvect(fp->numamps/LOCALCHUNK);
  fp->normvals = gen_fvect(fp->numamps/LOCALCHUNK);
  fp->maxrawpow = 0.0;
  for (ii=0; ii<fp->numamps/LOCALCHUNK; ii++){
    index = ii * LOCALCHUNK;
    for (jj=0; jj<LOCALCHUNK; jj++, index++){
      tmppwr = POWER(fp->amps[index].r, fp->amps[index].i);
      if (tmppwr > fp->maxrawpow)
	fp->maxrawpow = tmppwr;
      fp->rawpowers[index] = tmppwr;
      chunk[jj] = tmppwr;
    }
    fp->medians[ii] = median(chunk, LOCALCHUNK);
    fp->normvals[ii] = 1.0 / (1.4426950408889634 * fp->medians[ii]);
  }
  return fp;
}

static void free_fftpart(fftpart *fp)
{
  free(fp->normvals);
  free(fp->medians);
  free(fp->rawpowers);
  free(fp->amps);
  free(fp);
}


static double find_peak(float inf, fftview *fv, fftpart *fp)
{
  int ii, lobin, hibin, maxbin=0;
  float maxpow=0.0;
  double inr, viewfrac=0.05, newmaxr, newmaxz;
  rderivs derivs;
  fourierprops props;

  inr = inf * T;
  lobin = inr - (fv->numbins * 0.5 * viewfrac);
  hibin = inr + (fv->numbins * 0.5 * viewfrac);
  for (ii=lobin-fp->rlo; ii<hibin-fp->rlo+1; ii++){
    if (fp->rawpowers[ii] > maxpow){
      maxpow = fp->rawpowers[ii];
      maxbin = ii + fp->rlo;
    }
  }
  maxpow = max_rz_arr(fp->amps, fp->numamps, maxbin, 0.0, 
		      &newmaxr, &newmaxz, &derivs);
  newmaxr += fp->rlo;
  calc_props(derivs, newmaxr, newmaxz, 0.0, &props);
  print_candidate(&props, idata.dt, N, r0, 2);
  return newmaxr;
}

static void print_help(void)
{
  printf("\n"
	 " Button or Key      Effect\n"
	 " -------------      ------\n"
	 " Mouse1 or A        Zoom in by a factor of 2\n"
	 " Mouse3 or X        Zoom in by a factor of 2\n"
	 " J                  Shift left  by 15%% of the screen width\n"
	 " L                  Shift right by 15%% of the screen width\n"
	 " I                  Increase the power scale (make them taller)\n"
	 " K                  Decrease the power scale (make them shorter)\n"
	 " Space              Auto-scale the powers\n"
	 " N                  Renormalize the nowers by one of several methods\n"
	 " P                  Print the current plot to a file\n"
	 " Mouse2 or S or D   Select and optimize a frequency\n"
	 " H                  Show the harmonics of the center frequency\n"
	 " ?                  Show this help screen\n"
	 " Q                  Quit\n"
	 "\n");
}

int main(int argc, char *argv[])
{
  float maxpow=0.0;
  double centerr, offsetf;
  int numamps, zoomlevel, maxzoom, minzoom, xid, psid;
  char *rootfilenm, inchar;
  fftpart *lofp;
  fftview *fv;
 
  printf("\n\n");
  printf("      Interactive FFT Explorer\n");
  printf("         by Scott M. Ransom\n");
  printf("            October, 2001\n");
  print_help();

  {
    int hassuffix=0;
    char *suffix;
    
    hassuffix = split_root_suffix(argv[1], &rootfilenm, &suffix);
    if (hassuffix){
      if (strcmp(suffix, "fft")!=0){
        printf("\nInput file ('%s') must be a FFT file ('.fft')!\n\n", argv[1]);
        free(suffix);
        exit(0);
      }
      free(suffix);
    } else {
      printf("\nInput file ('%s') must be a FFT file ('.fft')!\n\n", argv[1]);
      exit(0);
    }
  }

  /* Read the info file */
 
  readinf(&idata, rootfilenm);
  if (idata.object) {
    printf("Examining %s data from '%s'.\n\n",
           remove_whitespace(idata.object), argv[1]);
  } else {
    printf("Examining data from '%s'.\n\n", argv[1]);
  }
  N = idata.N;
  T = idata.dt * idata.N;
  fftfile = chkfopen(argv[1], "rb");
  Nfft = chkfilelen(fftfile, sizeof(fcomplex));

  /* Get and plot the initial data */
  
  numamps = (Nfft > MAXBINS) ? (int) MAXBINS : (int) Nfft;
  lofp = get_fftpart(0, numamps);
  r0 = lofp->amps[0].r;
  centerr = 0.5 * INITIALNUMBINS;
  zoomlevel = LOGDISPLAYNUM - LOGINITIALNUMBINS;
  minzoom = LOGDISPLAYNUM - LOGMAXBINS;
  maxzoom = LOGDISPLAYNUM - LOGMINBINS;
  fv = get_fftview(centerr, zoomlevel, lofp);

  /* Prep the XWIN device for PGPLOT */

  xid = cpgopen("/XWIN");
  if (xid <= 0){
    fclose(fftfile);
    free(fv);
    free_fftpart(lofp);
    exit(EXIT_FAILURE);
  }
  cpgask(0);
  cpgpage();
  offsetf = plot_fftview(fv, maxpow);

  do {
    float inx, iny;
    
    cpgcurs(&inx, &iny, &inchar);
    if (DEBUGOUT) printf("You pressed '%c'\n", inchar);

    switch (inchar){
    case 'A': /* Zoom in */
    case 'a':
      if (DEBUGOUT) printf("  Zooming in  (zoomlevel = %d)...\n", zoomlevel);
      centerr = (inx + offsetf) * T;
      if (zoomlevel < maxzoom){
	zoomlevel++;
	free(fv);
	fv = get_fftview(centerr, zoomlevel, lofp);
	cpgpage();
	offsetf = plot_fftview(fv, maxpow);
      } else 
	printf("  Already at maximum zoom level (%d).\n", zoomlevel);
      break;
    case 'X': /* Zoom out */
    case 'x':
      if (DEBUGOUT) printf("  Zooming out  (zoomlevel = %d)...\n", zoomlevel);
      centerr = (inx + offsetf) * T;
      if (zoomlevel > minzoom){
	zoomlevel--;
	free(fv);
	fv = get_fftview(centerr, zoomlevel, lofp);
	cpgpage();
	offsetf = plot_fftview(fv, maxpow);
      } else 
	printf("  Already at minimum zoom level (%d).\n", zoomlevel);
      break;
    case 'J': /* Shift left */
    case 'j':
      if (DEBUGOUT) printf("  Shifting left...\n");
      centerr -= 0.15 * fv->numbins;
      free(fv);
      fv = get_fftview(centerr, zoomlevel, lofp);
      cpgpage();
      offsetf = plot_fftview(fv, maxpow);
      break;
    case 'L': /* Shift left */
    case 'l':
      if (DEBUGOUT) printf("  Shifting right...\n");
      centerr += 0.15 * fv->numbins;
      free(fv);
      fv = get_fftview(centerr, zoomlevel, lofp);
      cpgpage();
      offsetf = plot_fftview(fv, maxpow);
      break;
    case 'I': /* Scaling down */
    case 'i':
      if (maxpow==0.0){
	printf("  Auto-scaling is off.\n");
	maxpow = 1.1 * fv->maxpow;
      }
      maxpow = 3.0/4.0 * maxpow;
      cpgpage();
      offsetf = plot_fftview(fv, maxpow);
      break;
    case 'K': /* Scaling up */
    case 'k':
      if (maxpow==0.0){ 
	printf("  Auto-scaling is off.\n");
	maxpow = 1.1 * fv->maxpow;
      }
      maxpow = 4.0/3.0 * maxpow;
      cpgpage();
      offsetf = plot_fftview(fv, maxpow);
      break;
    case ' ': /* Auto-scale */
      if (maxpow==0.0)
	break;
      else {
	printf("  Auto-scaling is on.\n");
	maxpow = 0.0;
	cpgpage();
	offsetf = plot_fftview(fv, maxpow);
	break;
      }
    case 'G': /* Goto a frequency */
    case 'g':
      {
	char freqstr[50];
	double freq=-1.0;

	while (freq < 0.0){
	  printf("  Enter the frequency (Hz) to go to:\n");
	  fgets(freqstr, 50, stdin);
	  freqstr[strlen(freqstr)-1]= '\0';
	  freq = atof(freqstr);
	}
	offsetf = 0.0;
	centerr = freq * T;
	printf("  Moving to frequency %.12f.\n", freq);
	free(fv);
	fv = get_fftview(centerr, zoomlevel, lofp);
	cpgpage();
	offsetf = plot_fftview(fv, maxpow);
      }
      break;
    case '?': /* Print help screen */
      print_help();
      break;
    case 'S': /* Select a point */
    case 's':
    case 'D':
    case 'd':
      {
	double newr;
	
	printf("  Searching for peak near freq = %.7g Hz...\n", (inx + offsetf));
	newr = find_peak(inx+offsetf, fv, lofp);
	centerr = newr;
	if (zoomlevel < maxzoom)
	  zoomlevel++;
	free(fv);
	fv = get_fftview(centerr, zoomlevel, lofp);
	cpgpage();
	offsetf = plot_fftview(fv, maxpow);
	/*
	  cpgsci(2);
	  cpgmove(newr/T-offsetf, 0.0);
	  cpgdraw(newr/T-offsetf, 10.0*fv->maxpow);
	*/
      }
      break;
    case 'P': /* Print the current plot */
    case 'p':
      {
	int len;
	char filename[200];

	printf("  Enter the filename to save the plot as:\n");
	fgets(filename, 196, stdin);
	len = strlen(filename)-1;
	filename[len+0] = '/';
	filename[len+1] = 'P';
	filename[len+2] = 'S';
	filename[len+3] = '\0';
	psid = cpgopen(filename);
	cpgslct(psid);
	cpgpap(11.0, 8.5/11.0);
	offsetf = plot_fftview(fv, maxpow);
	cpgclos();
	cpgslct(xid);
	filename[len] = '\0';
	printf("  Wrote the plot to the file '%s'.\n", filename);
      }
      break;
    case 'N': /* Changing power normalization */
    case 'n':
      {
	float inx2, iny2;
	char choice;
	unsigned char badchoice=1;

	printf("  Specify the type of power normalization:\n"
	       "       m,M  :  Median values determined locally\n"
	       "       d,D  :  DC frequency amplitude\n"
	       "       r,R  :  Raw powers (i.e. no normalization)\n"
	       "       u,U  :  User specified interval (the average powers)\n");
	while (badchoice){
	  cpgcurs(&inx2, &iny2, &choice);
	  switch (choice){
	  case 'M':
	  case 'm':
	    norm_const = 0.0;
	    maxpow = 0.0;
	    badchoice = 0;
	    printf("  Using local median normalization.  Autoscaling is on.\n");
	    break;
	  case 'D':
	  case 'd':
	    norm_const = 1.0/r0;
	    maxpow = 0.0;
	    badchoice = 0;
	    printf("  Using DC frequency (%f) normalization.  Autoscaling is on.\n", r0);
	    break;
	  case 'R':
	  case 'r':
	    norm_const = 1.0;
	    maxpow = 0.0;
	    badchoice = 0;
	    printf("  Using raw powers (i.e. no normalization).  Autoscaling is on.\n");
	    break;
	  case 'U':
	  case 'u':
	    {
	      char choice2;
	      float xx, yy;
	      int lor, hir, numr;
	      double avg, var;

	      printf("  Use the left mouse button to select a left and right boundary\n"
		     "  of a region to calculate the average power.\n");
	      do {
		cpgcurs(&xx, &yy, &choice2);
	      } while (choice2 != 'A' && choice2 != 'a');
	      lor = (int)((xx + offsetf) * T);
	      cpgsci(7);
	      cpgmove(xx, 0.0);
	      cpgdraw(xx, 10.0*fv->maxpow);
	      do {
		cpgcurs(&xx, &yy, &choice2);
	      } while (choice2 != 'A' && choice2 != 'a');
	      hir = (int)((xx + offsetf) * T);
	      cpgmove(xx, 0.0);
	      cpgdraw(xx, 10.0*fv->maxpow);
	      cpgsci(1);
	      if (lor > hir){
		int tempr;
		tempr = hir;
		hir = lor;
		lor = tempr;
	      }
	      numr = hir - lor + 1;
	      avg_var(lofp->rawpowers+lor-lofp->rlo, numr, &avg, &var);
	      printf("  Selection has:  average = %.5g\n"
		     "                  std dev = %.5g\n", avg, sqrt(var));
	      norm_const = 1.0/avg;
	      maxpow = 0.0;
	      badchoice = 0;
	      printf("  Using %.5g as the normalization constant.  Autoscaling is on.\n", avg);
	      break;
	    }
	  default:
	    printf("  Unrecognized choice '%c'.\n", choice);
	    break;
	  }
	}
	free(fv);
	fv = get_fftview(centerr, zoomlevel, lofp);
	cpgpage();
	offsetf = plot_fftview(fv, maxpow);
      }
      break;
    case 'Q': /* Quit */
    case 'q':
      printf("  Quitting...\n");
      free(fv);
      cpgclos();
      break;
    default:
      printf("  Unrecognized option '%c'.\n", inchar);
      break;
    }
  } while (inchar != 'Q' && inchar != 'q');

  free_fftpart(lofp);
  fclose(fftfile);
  printf("Done\n\n");
  return 0;
}

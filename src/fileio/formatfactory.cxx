
#include <globals.hxx>

#include "formatfactory.hxx"

#include "impls/emptyformat.hxx"

#include "impls/netcdf4/ncxx4.hxx"
#include "impls/netcdf/nc_format.hxx"
#include "impls/hdf5/h5_format.hxx"
#include "impls/pnetcdf/pnetcdf.hxx"

#include <boutexception.hxx>
#include <output.hxx>
#include <cstring>

FormatFactory *FormatFactory::instance = nullptr;

FormatFactory* FormatFactory::getInstance() {
  if (instance == nullptr) {
    // Create the singleton object
    instance = new FormatFactory();
  }
  return instance;
}

// Work out which data format to use for given filename
std::unique_ptr<DataFormat> FormatFactory::createDataFormat(const char *filename, bool parallel) {
  if ((filename == nullptr) || (strcasecmp(filename, "default") == 0)) {
    // Return default file format
    

    if (parallel) {
#ifdef PNCDF
      return bout::utils::make_unique<PncFormat>();
#else
    }

#ifdef NCDF4
    return bout::utils::make_unique<Ncxx4>();
#else

#ifdef NCDF
    return bout::utils::make_unique<NcFormat>();
#else

#ifdef HDF5
    return bout::utils::make_unique<H5Format>();
#else

#error No file format available; aborting.

#endif // HDF5
#endif // NCDF
#endif // NCDF4
#endif // PNCDF
    throw BoutException("Parallel I/O disabled, no serial library found");
  }

  // Extract the file extension

  int len = strlen(filename);

  int ind = len-1;  
  while((ind != -1) && (filename[ind] != '.')) {
    ind--;
  }
  
  const char *s = filename + ind+1;

  // Match strings
  
#ifdef PNCDF
  if(parallel) {
    const char *pncdf_match[] = {"cdl", "nc", "ncdf"};
    if(matchString(s, 3, pncdf_match) != -1) {
      output.write("\tUsing Parallel NetCDF format for file '%s'\n", filename);
      return bout::utils::make_unique<PncFormat>();
    }
  }
#endif

#ifdef NCDF4
  const char *ncdf_match[] = {"cdl", "nc", "ncdf"};
  if(matchString(s, 3, ncdf_match) != -1) {
    output.write("\tUsing NetCDF4 format for file '%s'\n", filename);
    return bout::utils::make_unique<Ncxx4>();
  }
#endif

#ifdef NCDF
  const char *ncdf_match[] = {"cdl", "nc", "ncdf"};
  if(matchString(s, 3, ncdf_match) != -1) {
    output.write("\tUsing NetCDF format for file '%s'\n", filename);
    return bout::utils::make_unique<NcFormat>();
  }
#endif

#ifdef HDF5
  const char *hdf5_match[] = {"h5","hdf","hdf5"};
  if(matchString(s, 3, hdf5_match) != -1) {
    output.write("\tUsing HDF5 format for file '%s'\n", filename);
#ifdef PHDF5
    return bout::utils::make_unique<H5Format>(parallel);
#else
    return bout::utils::make_unique<H5Format>();
#endif
  }
#endif

  throw BoutException("\tFile extension not recognised for '%s'\n", filename);
  return nullptr;
}

////////////////////// Private functions /////////////////////////////

int FormatFactory::matchString(const char *str, int n, const char **match) {
  for(int i=0;i<n;i++) {
    if(strcasecmp(str, match[i]) == 0) {
      return i;
    }
  }
  return -1;
}

////////////////////// Depreciated function ///////////////////////////

std::unique_ptr<DataFormat> data_format(const char *filename) {
  return FormatFactory::getInstance()->createDataFormat(filename);
}


{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.gdal
    pkgs.geos
    pkgs.proj
    pkgs.expat
    pkgs.sqlite
    pkgs.hdf5
    pkgs.netcdf
    pkgs.curl
    pkgs.zlib
    pkgs.libxml2
    pkgs.libxslt
    pkgs.openssl
    pkgs.pkg-config
    pkgs.gcc
  ];
  
  env = {
    PYTHONPATH = "${pkgs.python311}/lib/python3.11/site-packages";
    LD_LIBRARY_PATH = "${pkgs.gdal}/lib:${pkgs.geos}/lib:${pkgs.proj}/lib:${pkgs.expat}/lib:${pkgs.sqlite}/lib:${pkgs.hdf5}/lib:${pkgs.netcdf}/lib";
    GDAL_DATA = "${pkgs.gdal}/share/gdal";
    PROJ_LIB = "${pkgs.proj}/share/proj";
  };
}

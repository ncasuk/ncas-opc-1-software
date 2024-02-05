"""
Create netCDF files using ncas_amof_netcdf_template module for ncas-opc-1 instrument
- input data is in GRIMM_ALL_DCMexV3.csv
- the first row in the input data is the header
- the first column in the input data is the date and time in UTC in ISO 8601 format
- the other columns are the number concentration (in Number per litre) for each size bin
- the lower bounds of the size bin are the column names for each column (except the Datetime column)
- need one netCDF file per day
- the netCDF files should be created using the ncas_amof_netcdf_template module
- the instrument name is ncas-opc-1
- the platform name needs to be changed from the default value "mobile" to "kiva-2-lab"
"""

import pandas as pd
import ncas_amof_netcdf_template as nant
import datetime as dt
import numpy as np
import os


def main(input_file, netcdf_file_location, metadata_file):
    # Load the CSV file into a pandas DataFrame, using the datetime column as the index
    df = pd.read_csv(input_file, parse_dates=[0]).dropna(how='all')

    # drop rows where all columns except datetime are NaN
    df = df.dropna(subset=df.columns[1:], how='all')

    # For each unique day in the datetime column
    for date in df.iloc[:,0].dt.date.unique():
        print(date)
        # Filter the DataFrame for that day
        df_day = df[df.iloc[:,0].dt.date == date]

        # convert the time column to a datetime object
        df_day.iloc[:,0] = pd.to_datetime(df_day.iloc[:,0])

        # get all the needed time formats
        unix_times, day_of_year, years, months, days, hours, minutes, seconds, time_coverage_start_unix, time_coverage_end_unix, file_date = nant.util.get_times(df_day.iloc[:,0])

        # Create a new netCDF file using the ncas_amof_netcdf_template module
        nc_file = nant.create_netcdf.main("ncas-opc-1", date.strftime('%Y%m%d'), dimension_lengths={"time": len(unix_times), "index": df_day.shape[1] - 1}, file_location=netcdf_file_location, return_open=True)

        # Add data to ambient_aerosol_number_per_channel variable, converting number per litre into number per centimetre cubed
        nant.util.update_variable(nc_file, "ambient_aerosol_number_per_channel", df_day.iloc[:,1:].values/1000)

        # Make data array of the lower limits of the size bins
        lower_limits = np.array([df_day.columns[1:].values.astype(float)]*len(unix_times))

        # Upper limits is the lower limits shifted one to the right, with the last value being 32
        upper_limits = np.array([np.append(df_day.columns[2:].values.astype(float), 32)]*len(unix_times))

        # Add data to measurement_channel_lower_limit and measurement_channel_upper_limit variables
        nant.util.update_variable(nc_file, "measurement_channel_lower_limit", lower_limits)
        nant.util.update_variable(nc_file, "measurement_channel_upper_limit", upper_limits)

        # Add times to the relavent time variables
        nant.util.update_variable(nc_file, "time", unix_times)
        nant.util.update_variable(nc_file, "day_of_year", day_of_year)
        nant.util.update_variable(nc_file, "year", years)
        nant.util.update_variable(nc_file, "month", months)
        nant.util.update_variable(nc_file, "day", days)
        nant.util.update_variable(nc_file, "hour", hours)
        nant.util.update_variable(nc_file, "minute", minutes)
        nant.util.update_variable(nc_file, "second", seconds)

        # Add latitude and longitude variables, and geospatial_bounds attribute
        nant.util.update_variable(nc_file, "latitude", 33.9913)
        nant.util.update_variable(nc_file, "longitude", -107.1880)
        geobounds = f"33.9913N, -107.1880E"
        nc_file.setncattr('geospatial_bounds', geobounds)

        # Add the time coverage start and end times
        nc_file.setncattr(
            'time_coverage_start',
            dt.datetime.fromtimestamp(time_coverage_start_unix, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        )
        nc_file.setncattr(
            'time_coverage_end',
            dt.datetime.fromtimestamp(time_coverage_end_unix, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        )

        # Add metadata from CSV file
        nant.util.add_metadata_to_netcdf(nc_file, metadata_file)

        # Overwrite instrument_software_version to be string, not float
        #nc_file.setncattr('instrument_software_version', "1.2")

        # Delete unnecessary global attributes
        attrs_to_delete = ["dma_inner_radius","dma_outer_radius","dma_length","impactor_orifice_diameter"]
        for attr in attrs_to_delete:
            nc_file.delncattr(attr)

        # Close file
        nc_file.close()

        # Check for and remove empty variables
        nant.remove_empty_variables.main(f"{netcdf_file_location}/ncas-opc-1_mobile_{date.strftime('%Y%m%d')}_aerosol-size-distribution_v1.0.nc")

        # Change the platform name from "mobile" to "kiva-2-lab"
        os.rename(
            f"{netcdf_file_location}/ncas-opc-1_mobile_{date.strftime('%Y%m%d')}_aerosol-size-distribution_v1.0.nc",
            f"{netcdf_file_location}/ncas-opc-1_kiva-2-lab_{date.strftime('%Y%m%d')}_aerosol-size-distribution_v1.0.nc",
        )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create netCDF files for ncas-opc-1 instrument")
    parser.add_argument("input_file", help="The input CSV file")
    parser.add_argument("-n", "--netcdf-location", default = ".", help="The location to save the netCDF files. Default is '.'")
    parser.add_argument("-m", "--metadata-file", default = "metadata.csv", help="The metadata file. Default is 'metadata.csv'")
    args = parser.parse_args()
    main(args.input_file, args.netcdf_location, args.metadata_file)
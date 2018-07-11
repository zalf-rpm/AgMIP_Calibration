import pandas as pd
import csv
import datetime
input_climate_file = "cal2_weather.xlsx"

# open excel file with pandas
excel_file = pd.ExcelFile(input_climate_file)

# list of sheet names
sheets = excel_file.sheet_names


# go through all sheets
for sheet_name in sheets:

    print(sheet_name)
    csv_filename = "climate_" + sheet_name[5:] + ".csv"

    sheet_df = excel_file.parse(sheet_name, header=4)


    with open(csv_filename, "wb") as csv_fp:

        csv_out = csv.writer(csv_fp, delimiter=",")
        csv_out.writerow(["iso-date", "tmin", "tmax", "tavg", "globrad", "precip","et0"])

        for df_row in sheet_df.iterrows():
            row_value = df_row[1]

            date = datetime.date(year=int(row_value['YYYY']), month=int(row_value['MM']), day=int(row_value['DD']))
            date_str = date.isoformat()

            globrad = round(float(row_value['SRAD']), 5)
            tmin = round(float(row_value['TMIN']), 2)
            tmax = round(float(row_value['TMAX']), 2)
            tavg = round(float(tmin+tmax) / 2.0, 2)
            et0 = round(float(row_value['ET0']), 5)
            precip = round(float(row_value['RAIN']), 3)

            csv_out.writerow([date, tmin, tmax, tavg, globrad, precip, et0])

        #print(date)

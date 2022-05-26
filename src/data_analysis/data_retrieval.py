import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

from scipy.stats import linregress
import datetime as dt

from utils import PROJECT_ROOT

# Global intra day and day ahead dataframes for functions to use
files = ['trds_1.parquet',
         'trds_2.parquet',
         'trds_3.parquet',
         'trds_4.parquet',
         'trds_5.parquet',
         'trds_6.parquet',
         ]
tables = []
for file in files:
    tables.append(pq.read_table(f'{PROJECT_ROOT}\\data\\{file}',
                                columns=['trd_trade_id', 'trd_execution_time', 'trd_venue',
                                         'trd_buy_delivery_area', 'trd_sell_delivery_area',
                                         'trd_tariff',
                                         'trd_sequence_name', 'trd_product', 'trd_price',
                                         'trd_delivery_time_name', 'trd_delivery_time_start',
                                         'trd_delivery_time_end']))
table = pa.concat_tables(tables)
df_intra_day = table.to_pandas()
df_intra_day = df_intra_day.sort_values(by=['trd_execution_time', 'trd_buy_delivery_area', 'trd_sell_delivery_area'])

df_day_ahead = pd.read_csv(f'{PROJECT_ROOT}\\data\\DE_DA_prices.csv',
                           converters={'timestamp': lambda t: pd.Timestamp(t).timestamp()})

# Global wind dataframes for functions to use
df_wind_historic = pd.read_csv(f'{PROJECT_ROOT}\\data\\wind_data_average.csv')
df_wind_forecast = pd.read_csv(f'{PROJECT_ROOT}\\data\\forecast_wind_data_average.csv')

df_wind = pd.read_csv(f'{PROJECT_ROOT}\\data\\pro_de_wnd_actual_ec00_gfs00_icon00_cet_min15_f.csv', index_col=[0])
df_wind.index = pd.to_datetime(df_wind.index.astype(str).str[:-6])

df_residual_load = pd.read_csv(f'{PROJECT_ROOT}\\data\\rdl_de_actual_ec00_gfs00_cet_min15_f.csv', index_col=[0])
df_residual_load.index = pd.to_datetime(df_residual_load.index.astype(str).str[:-6])

df_solar = pd.read_csv(f'{PROJECT_ROOT}\\data\\pro_de_spv_actual_ec00_gfs00_icon00_cet_min15_f.csv', index_col=[0])
df_solar.index = pd.to_datetime(df_solar.index.astype(str).str[:-6])


def get_intra_day_data_for_region(region: str):
    """
    :param region: (sub)string that is contained in the region name
    :return: intra-day dataframe for provided region
    """
    region = region.upper()
    return df_intra_day[df_intra_day["trd_buy_delivery_area"].str.contains(region) &
                        df_intra_day["trd_sell_delivery_area"].str.contains(region)].copy()


def get_intra_day(max_time_before_closing=None,
                  min_time_before_closing=None,
                  unit=None,
                  region="GERMANY",
                  start_date=None,
                  end_date=None):
    """
    :param max_time_before_closing: only trades after maximum till product closes
    :param min_time_before_closing: only trades before minimum time till product closes
    :param unit: pandas unit for time before closing
        Possible values:
        ‘W’, ‘D’, ‘T’, ‘S’, ‘L’, ‘U’, or ‘N’
        ‘days’ or ‘day’
        ‘hours’, ‘hour’, ‘hr’, or ‘h’
        ‘minutes’, ‘minute’, ‘min’, or ‘m’
        ‘seconds’, ‘second’, or ‘sec’
        ‘milliseconds’, ‘millisecond’, ‘millis’, or ‘milli’
        ‘microseconds’, ‘microsecond’, ‘micros’, or ‘micro’
        ‘nanoseconds’, ‘nanosecond’, ‘nanos’, ‘nano’, or ‘ns’.
    :param region: (sub)string that is contained in the region name
    :param start_date: filter trades to those that happened on or after start_date
    :param end_date: filter trades to those that happened on or before end_date
    :return: pandas dataframe for intra-day prices
    """
    df = get_intra_day_data_for_region(region)
    # Filter to trades that happened between start_date and end_date
    if start_date and end_date:
        df = df[(df['trd_delivery_time_start'] >= f'{start_date} 00:00:00') &
                (df['trd_delivery_time_start'] <= f'{end_date} 23:59:59')]
    # Filter to only trades that happened at most time_before_closing-units before closing
    if max_time_before_closing and min_time_before_closing and unit:
        df['diff'] = (df['trd_delivery_time_start']
                      - df['trd_execution_time'])
        df = df[(df['diff'] <= pd.Timedelta(max_time_before_closing, unit=unit)) &
                (df['diff'] >= pd.Timedelta(min_time_before_closing, unit=unit))]
    if max_time_before_closing and unit:
        df['diff'] = (df['trd_delivery_time_start']
                      - df['trd_execution_time'])
        df = df[df['diff'] <= pd.Timedelta(max_time_before_closing, unit=unit)]
    elif min_time_before_closing and unit:
        df['diff'] = (df['trd_delivery_time_start']
                      - df['trd_execution_time'])
        df = df[df['diff'] >= pd.Timedelta(min_time_before_closing, unit=unit)]
    return df


def get_day_ahead_data():
    """
    :return: pandas dataframe of day-ahead data
    """
    return df_day_ahead.copy()


def get_wind_historic():
    """
    :return: pandas dataframe of historic (actual) wind data
    """
    return df_wind_historic.copy()


def get_wind_forecast():
    """
    :return: pandas dataframe of forecast wind data
    """
    return df_wind_forecast.copy()


def get_wind(start_date=None,
             end_date=None):
    """
    First column is the actual value for every 15 min, the other three are day ahead forecasts from different providers
    by hour.
    :return: pandas dataframe of forecast and historic wind data
    """
    df = df_wind.copy()
    if start_date and end_date:
        df = df[(df.index >= f'{start_date} 00:00:00') &
                (df.index <= f'{end_date} 23:59:59')]
    return df


def get_residual_load(start_date=None,
                      end_date=None):
    """
    :param start_date:
    :param end_date:
    :return: pandas dataframe of residual load
    """
    df = df_residual_load.copy()
    if start_date and end_date:
        df = df[(df.index >= f'{start_date} 00:00:00') &
                (df.index <= f'{end_date} 23:59:59')]
    return df


def get_solar(start_date=None,
              end_date=None):
    """
    :param start_date:
    :param end_date:
    :return: pandas dataframe of solar forecast and historic data
        """
    df = df_solar.copy()
    if start_date and end_date:
        df = df[(df.index >= f'{start_date} 00:00:00') &
                (df.index <= f'{end_date} 23:59:59')]
    return df


def get_intra_day_min_max_mean(interval='15min',
                               on='trd_execution_time',
                               max_time_before_closing=None,
                               min_time_before_closing=None,
                               unit=None,
                               start_date=None,
                               end_date=None):
    """
    :param interval: interval to resample on
    :param on: column to resample on
    :param max_time_before_closing: only trades after maximum till product closes
    :param min_time_before_closing: only trades before minimum time till product closes
    :param unit: pandas unit for time before closing
        Possible values:
        ‘W’, ‘D’, ‘T’, ‘S’, ‘L’, ‘U’, or ‘N’
        ‘days’ or ‘day’
        ‘hours’, ‘hour’, ‘hr’, or ‘h’
        ‘minutes’, ‘minute’, ‘min’, or ‘m’
        ‘seconds’, ‘second’, or ‘sec’
        ‘milliseconds’, ‘millisecond’, ‘millis’, or ‘milli’
        ‘microseconds’, ‘microsecond’, ‘micros’, or ‘micro’
        ‘nanoseconds’, ‘nanosecond’, ‘nanos’, ‘nano’, or ‘ns’.
    :param start_date: filter trades to those that happened on or after start_date
    :param end_date: filter trades to those that happened on or before end_date
    :return: day-ahead dataframe with tdr_price_mean, trd_price_min and trd_price_max
    """
    df = get_intra_day(start_date=start_date, end_date=end_date,
                       max_time_before_closing=max_time_before_closing,
                       min_time_before_closing=min_time_before_closing, unit=unit)
    df = df.resample(interval, on=on).agg(trd_price_mean=('trd_price', np.mean),
                                          trd_price_min=('trd_price', np.min),
                                          trd_price_max=('trd_price', np.max))
    df.reset_index(inplace=True)
    return df


def get_transformed_day_ahead(start_date=None,
                              end_date=None):
    """
    Transforms columnar DateCET and hour data into a single timestamp column and the corresponding price
    :param start_date: filter trades to those that happened on or after start_date
    :param end_date: filter trades to those that happened on or before end_date
    :return: transformed day ahead dataframe
    """
    df = get_day_ahead_data()
    df = df.groupby('DateCET').apply(lambda row: pd.DataFrame(
        {'trd_delivery_time_start': pd.date_range(row['DateCET'].iloc[0],
                                                  periods=len(df.columns[1:]), freq='1H'),
         'trd_price': np.repeat(np.array([row[col].iloc[0] for col in df.columns[1:]]), 1)}))
    # Filter to trades that happened between start_date and end_date
    if start_date and end_date:
        df = df[(df['trd_delivery_time_start'] >= f'{start_date} 00:00:00') &
                (df['trd_delivery_time_start'] <= f'{end_date} 23:59:59')]
    df.reset_index(inplace=True, drop=True)
    return df


def get_diff(absolute=True,
             max_time_before_closing=None,
             min_time_before_closing=None,
             unit=None,
             start_date='2021-11-09',
             end_date='2022-03-23'):
    """
    :param absolute: to calculate absolute diff or not
    :param interval: time interval on which to group intra-day prices
    :param max_time_before_closing: only trades after maximum till product closes
    :param min_time_before_closing: only trades before minimum time till product closes
    :param unit: pandas unit for time before closing
        Possible values:
        ‘W’, ‘D’, ‘T’, ‘S’, ‘L’, ‘U’, or ‘N’
        ‘days’ or ‘day’
        ‘hours’, ‘hour’, ‘hr’, or ‘h’
        ‘minutes’, ‘minute’, ‘min’, or ‘m’
        ‘seconds’, ‘second’, or ‘sec’
        ‘milliseconds’, ‘millisecond’, ‘millis’, or ‘milli’
        ‘microseconds’, ‘microsecond’, ‘micros’, or ‘micro’
        ‘nanoseconds’, ‘nanosecond’, ‘nanos’, ‘nano’, or ‘ns’.
    :param start_date: filter trades to those that happened on or after start_date
    :param end_date: filter trades to those that happened on or before end_date
    :return: dataframe with price differences between day-ahead and intra-day
    """
    df_id = get_intra_day_min_max_mean(interval='H',
                                       on='trd_delivery_time_start',
                                       start_date=start_date,
                                       end_date=end_date,
                                       max_time_before_closing=max_time_before_closing,
                                       min_time_before_closing=min_time_before_closing,
                                       unit=unit) \
        .drop(columns=['trd_price_min', 'trd_price_max']).rename(columns={"trd_price_mean": "trd_price"})
    df_da = get_transformed_day_ahead(start_date=start_date, end_date=end_date)

    df_id.set_index('trd_delivery_time_start', inplace=True)
    df_da.set_index('trd_delivery_time_start', inplace=True)

    if absolute:
        df = (df_id - df_da).abs()
    else:
        df = df_id - df_da
    df.dropna(inplace=True)
    df.rename(columns={"trd_price": "price_diff"}, inplace=True)

    return df.copy()


def get_pct_change_dataframe(interval='H',
                             max_time_before_closing=60,
                             min_time_before_closing=None,
                             unit='minutes',
                             start_date='2021-11-09',
                             end_date='2022-03-23'):
    """
    :param interval: time interval on which to group intra-day prices
    :param max_time_before_closing: only trades after maximum till product closes
    :param min_time_before_closing: only trades before minimum time till product closes
    :param unit: pandas unit for time before closing
        Possible values:
        ‘W’, ‘D’, ‘T’, ‘S’, ‘L’, ‘U’, or ‘N’
        ‘days’ or ‘day’
        ‘hours’, ‘hour’, ‘hr’, or ‘h’
        ‘minutes’, ‘minute’, ‘min’, or ‘m’
        ‘seconds’, ‘second’, or ‘sec’
        ‘milliseconds’, ‘millisecond’, ‘millis’, or ‘milli’
        ‘microseconds’, ‘microsecond’, ‘micros’, or ‘micro’
        ‘nanoseconds’, ‘nanosecond’, ‘nanos’, ‘nano’, or ‘ns’.
    :param start_date: filter trades to those that happened on or after start_date
    :param end_date: filter trades to those that happened on or before end_date
    :return: dataframe with percentage change between day-ahead and intra-day
    """
    df = get_transformed_day_ahead(start_date=start_date, end_date=end_date)
    df['percentage_change'] = ((get_intra_day_min_max_mean(interval=interval,
                                                           on='trd_delivery_time_start',
                                                           max_time_before_closing=max_time_before_closing,
                                                           min_time_before_closing=min_time_before_closing,
                                                           unit=unit,
                                                           start_date=start_date,
                                                           end_date=end_date)['trd_price_mean']
                                - df['trd_price'].values) /
                               df[
                                   'trd_price'].values) * 100
    df.drop(columns='trd_price', inplace=True)

    # Drop any inf values that were created due to day_ahead price of 0.0 (corner case)
    return df.replace([np.inf, -np.inf], np.nan).dropna()


def get_intra_day_by_hours(start_date='2021-11-09',
                           end_date='2022-03-23'):
    """
    :param start_date: filter trades to those that happened on or after start_date
    :param end_date: filter trades to those that happened on or before end_date
    :return: dataframe of intra-day prices split into columns by hours
    """
    df = get_intra_day_min_max_mean(on='trd_delivery_time_start', interval='H',
                                    start_date=start_date, end_date=end_date)
    by_hours = []

    for hour in range(24):
        df_hour = df[df['trd_delivery_time_start'].dt.hour == hour]['trd_price_mean'] \
            .rename(hour)
        by_hours.append(df_hour.reset_index()[hour])
    df = pd.concat(by_hours, axis=1).dropna()
    return df


def get_intra_day_mean(interval='H',
                       on='trd_delivery_time_start',
                       max_time_before_closing=30,
                       min_time_before_closing=None,
                       unit='minutes',
                       start_date=None,
                       end_date=None):
    """
    :param interval: time interval on which to group intra-day prices
    :param on: column to aggregate
    :param max_time_before_closing: only trades after maximum till product closes
    :param min_time_before_closing: only trades before minimum time till product closes
    :param unit: pandas unit for time before closing
        Possible values:
        ‘W’, ‘D’, ‘T’, ‘S’, ‘L’, ‘U’, or ‘N’
        ‘days’ or ‘day’
        ‘hours’, ‘hour’, ‘hr’, or ‘h’
        ‘minutes’, ‘minute’, ‘min’, or ‘m’
        ‘seconds’, ‘second’, or ‘sec’
        ‘milliseconds’, ‘millisecond’, ‘millis’, or ‘milli’
        ‘microseconds’, ‘microsecond’, ‘micros’, or ‘micro’
        ‘nanoseconds’, ‘nanosecond’, ‘nanos’, ‘nano’, or ‘ns’.
    :param start_date: filter trades to those that happened on or after start_date
    :param end_date: filter trades to those that happened on or before end_date
    :return: dataframe of intra-day price mean (trd_price_mean)
    """
    df = get_intra_day(start_date=start_date, end_date=end_date,
                       max_time_before_closing=max_time_before_closing,
                       min_time_before_closing=min_time_before_closing, unit=unit)
    df = df.resample(interval, on=on).agg(trd_price_mean=('trd_price', np.mean))
    df.reset_index(inplace=True)
    return df


def get_std_by_day(absolute=False,
                   interval='H',
                   max_time_before_closing=None,
                   min_time_before_closing=None,
                   unit='hours',
                   start_date='2021-11-09',
                   end_date='2022-03-23'):
    """

    :param absolute: to calculate absolute diff or not
    :param interval: time interval on which to group intra-day prices
    :param max_time_before_closing: only trades after maximum till product closes
    :param min_time_before_closing: only trades before minimum time till product closes
    :param unit: pandas unit for time before closing
        Possible values:
        ‘W’, ‘D’, ‘T’, ‘S’, ‘L’, ‘U’, or ‘N’
        ‘days’ or ‘day’
        ‘hours’, ‘hour’, ‘hr’, or ‘h’
        ‘minutes’, ‘minute’, ‘min’, or ‘m’
        ‘seconds’, ‘second’, or ‘sec’
        ‘milliseconds’, ‘millisecond’, ‘millis’, or ‘milli’
        ‘microseconds’, ‘microsecond’, ‘micros’, or ‘micro’
        ‘nanoseconds’, ‘nanosecond’, ‘nanos’, ‘nano’, or ‘ns’.
    :param start_date: filter trades to those that happened on or after start_date
    :param end_date: filter trades to those that happened on or before end_date
    :return: dataframe with standard deviation between day-ahead and intra-day by day
    """

    df = get_diff(absolute=absolute,
                  interval=interval,
                  max_time_before_closing=max_time_before_closing,
                  min_time_before_closing=min_time_before_closing,
                  unit=unit,
                  start_date=start_date, end_date=end_date)
    df['std'] = df.groupby(df.index.day_name())['price_diff'].transform('std')
    return df


def get_labeled_data(start_date='2021-11-09',
                     end_date='2022-03-23',
                     simple=False):
    """
    Labels intra-day prices depending on how much the price changed
    :param start_date: filter trades to those that happened on or after start_date
    :param end_date: filter trades to those that happened on or before end_date
    :return: pandas dataframe with labels for changes
    """
    df_intra_day = get_intra_day_min_max_mean(interval='H', on='trd_delivery_time_start', start_date=start_date,
                                              end_date=end_date, max_time_before_closing=1, unit='H')

    df = get_transformed_day_ahead(start_date=start_date, end_date=end_date)

    if simple:
        conditions = [
            # Label 0
            (df['trd_price'] - df_intra_day['trd_price_mean']) >= 0,

            # Label 1
            (df['trd_price'] - df_intra_day['trd_price_mean']) < 0
        ]

        values = [0, 1]

    else:
        conditions = [
            # Label 14
            ((df['trd_price'] - df_intra_day['trd_price_mean']) > 60),

            # Label 13
            ((df['trd_price'] - df_intra_day['trd_price_mean']) <= 60) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) > 50),

            # Label 12
            ((df['trd_price'] - df_intra_day['trd_price_mean']) <= 50) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) > 40),

            # Label 11
            (df['trd_price'] - df_intra_day['trd_price_mean']) > 40,

            # Label 10
            ((df['trd_price'] - df_intra_day['trd_price_mean']) <= 40) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) > 30),

            # Label 9
            ((df['trd_price'] - df_intra_day['trd_price_mean']) <= 30) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) > 20),

            # Label 8
            ((df['trd_price'] - df_intra_day['trd_price_mean']) <= 20) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) > 10),

            # Label 7
            ((df['trd_price'] - df_intra_day['trd_price_mean']) <= 10) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) >= 0),

            # Label 6
            ((df['trd_price'] - df_intra_day['trd_price_mean']) < 0) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) >= -10),

            # Label 5
            ((df['trd_price'] - df_intra_day['trd_price_mean']) < -10) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) >= -20),

            # Label 4
            ((df['trd_price'] - df_intra_day['trd_price_mean']) < -20) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) >= -30),

            # Label 3
            ((df['trd_price'] - df_intra_day['trd_price_mean']) < -30) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) >= -40),

            # Label 2
            ((df['trd_price'] - df_intra_day['trd_price_mean']) < -40) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) >= -50),

            # Label 1
            ((df['trd_price'] - df_intra_day['trd_price_mean']) < -50) &
            ((df['trd_price'] - df_intra_day['trd_price_mean']) >= -60),

            # Label 0
            (df['trd_price'] - df_intra_day['trd_price_mean']) < -60
        ]

        values = [i for i in range(14, -1, -1)]
    # df['price_diff'] = df['trd_price'] - df_intra_day['trd_price_mean']
    df['label'] = np.select(conditions, values, default='Undefined')
    return df


def get_prepared_data(base_model=False,
                      labeled=False,
                      simple=False,
                      split_timestamp='2022-03-21 00:00:00',
                      start_date='2021-11-09',
                      end_date='2022-03-22'):
    df_ia = get_intra_day_min_max_mean(interval='H', on='trd_delivery_time_start',
                                       start_date=start_date, end_date=end_date,
                                       max_time_before_closing=30,
                                       unit='minutes').set_index('trd_delivery_time_start')

    df_ia['1h_before_closing'] = get_intra_day_min_max_mean(interval='H', on='trd_delivery_time_start',
                                                            start_date=start_date, end_date=end_date,
                                                            min_time_before_closing=1,
                                                            unit='hours').set_index('trd_delivery_time_start')[
        'trd_price_mean']
    df_ia['1h_diff'] = get_diff(absolute=True, min_time_before_closing=1, unit='H')['price_diff']

    df_ia['2h_before_closing'] = get_intra_day_min_max_mean(interval='H', on='trd_delivery_time_start',
                                                            start_date=start_date, end_date=end_date,
                                                            min_time_before_closing=2,
                                                            unit='hours').set_index('trd_delivery_time_start')[
        'trd_price_mean']

    df_ia['2h_diff'] = get_diff(absolute=True, min_time_before_closing=2, unit='H')['price_diff']

    df_ia['3h_before_closing'] = get_intra_day_min_max_mean(interval='H', on='trd_delivery_time_start',
                                                            start_date=start_date, end_date=end_date,
                                                            min_time_before_closing=3,
                                                            unit='hours').set_index('trd_delivery_time_start')[
        'trd_price_mean']

    df_ia['3h_diff'] = get_diff(absolute=True, min_time_before_closing=3, unit='H')['price_diff']

    df_ia['label'] = get_labeled_data(simple=simple, start_date=start_date, end_date=end_date) \
        .set_index('trd_delivery_time_start')['label']

    df_da = get_transformed_day_ahead(start_date='2021-11-09', end_date='2022-03-22').set_index(
        'trd_delivery_time_start')

    df_w = get_wind(start_date='2021-11-09', end_date='2022-03-22')
    df = pd.concat([df_ia, df_da, df_w], axis=1).dropna()

    def day_time(x):
        if (x > 4) and (x <= 8):
            return 'early_morning'
        elif (x > 8) and (x <= 12):
            return 'morning'
        elif (x > 12) and (x <= 16):
            return 'noon'
        elif (x > 16) and (x <= 20):
            return 'eve'
        elif (x > 20) and (x <= 24):
            return 'night'
        elif x <= 4:
            return 'late_night'

    if base_model:
        X = df[['trd_price']]
        X['day'] = X.index.dayofweek
        X['hour'] = X.index.hour
        if labeled:
            y = df['label']
        else:
            y = df['trd_price_mean']
    else:
        # X = df[['trd_price', 'price_diff', 'std']]
        # X = df[['trd_price', 'wnd Actual de', 'ec00', 'icon00', 'gfs00']]
        X = df[['trd_price', '1h_before_closing', '2h_before_closing',
                '3h_before_closing',
                '1h_diff', '2h_diff', '3h_diff']]
        # X = df[['trd_price', 'wnd Actual de', 'ec00', 'icon00', 'gfs00', '3h_before_closing', '3h_diff']]
        X['day'] = X.index.dayofweek
        X['hour'] = X.index.hour
        X['weekend'] = X.index.dayofweek > 4
        X['day_night_time'] = X['hour'].apply(day_time)
        X['day_night_time'] = pd.factorize(X['day_night_time'])[0]
        if labeled:
            y = df['label']
        else:
            y = df['trd_price_mean']

    mask = df.index >= split_timestamp
    X_train, X_test, y_train, y_test = X[~mask], X[mask], y[~mask], y[mask]
    return X, y, X_train, X_test, y_train, y_test


if __name__ == "__main__":
    """ start_date = '2021-11-09'
    end_date = '2022-03-22'
    pd.set_option('display.expand_frame_repr', False)
    df = get_intra_day(start_date=start_date, end_date=end_date)
    df['trd_execution_time_ordinal'] = pd.to_datetime(df['trd_execution_time']).apply(lambda v: v.timestamp())
    df['year'] = df['trd_execution_time'].dt.year
    df['month'] = df['trd_execution_time'].dt.month
    df['day'] = df['trd_execution_time'].dt.day
    df['hour'] = df['trd_execution_time'].dt.hour
    df = df.dropna()
    print(df)
    df_slope = df.groupby([df['year'], df['month'], df['day'], df['hour'], df['trd_delivery_time_start']])\
        .apply(lambda x: linregress(x['trd_execution_time_ordinal'], x['trd_price'])[0]).to_frame()

    print(df_slope)
    #df = df.merge(df_slope, how='left', on=['year', 'month', 'day', 'hour'])"""
    #print(get_labeled_data(simple=True)['label'].value_counts())
    print(get_wind())
    print(get_solar())
    print(get_residual_load())

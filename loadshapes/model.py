import pandas as pd


def clean_data(data):
    loads = [
    'baseline.out.electricity.bath_fan.energy_consumption.kwh',
      'baseline.out.electricity.ceiling_fan.energy_consumption.kwh',
      'baseline.out.electricity.clothes_dryer.energy_consumption.kwh',
      'baseline.out.electricity.clothes_washer.energy_consumption.kwh',
      'baseline.out.electricity.cooking_range.energy_consumption.kwh',
      'baseline.out.electricity.cooling.energy_consumption.kwh',
      'baseline.out.electricity.dishwasher.energy_consumption.kwh',
      'baseline.out.electricity.ext_holiday-light.energy_consumption.kwh',
      'baseline.out.electricity.exterior_lighting.energy_consumption.kwh',
      'baseline.out.electricity.extra_refrigerator.energy_consumption.kwh',
      'baseline.out.electricity.fans_cooling.energy_consumption.kwh',
      'baseline.out.electricity.fans_heating.energy_consumption.kwh',
      'baseline.out.electricity.freezer.energy_consumption.kwh',
      'baseline.out.electricity.garage_lighting.energy_consumption.kwh',
      'baseline.out.electricity.heating.energy_consumption.kwh',
      'baseline.out.electricity.heating_supplement.energy_consumption.kwh',
      'baseline.out.electricity.hot_tub-heater.energy_consumption.kwh',
      'baseline.out.electricity.hot_tub-pump.energy_consumption.kwh',
      'baseline.out.electricity.house_fan.energy_consumption.kwh',
      'baseline.out.electricity.interior_lighting.energy_consumption.kwh',
      'baseline.out.electricity.plug_loads.energy_consumption.kwh',
      'baseline.out.electricity.pool_heater.energy_consumption.kwh',
      'baseline.out.electricity.pool_pump.energy_consumption.kwh',
      'baseline.out.electricity.pumps_cooling.energy_consumption.kwh',
      'baseline.out.electricity.pumps_heating.energy_consumption.kwh',
      'baseline.out.electricity.pv.energy_consumption.kwh',
      'baseline.out.electricity.range_fan.energy_consumption.kwh',
      'baseline.out.electricity.recirc_pump.energy_consumption.kwh',
      'baseline.out.electricity.refrigerator.energy_consumption.kwh',
      'baseline.out.electricity.vehicle.energy_consumption.kwh',
      'baseline.out.electricity.water_systems.energy_consumption.kwh',
      'baseline.out.electricity.well_pump.energy_consumption.kwh']

    data['time'] = pd.to_datetime(data['Timestamp (EST)']) + pd.Timedelta(minutes=15)
    data['hour'] = data['time'].dt.hour+1
    data = data.melt(['time','hour'],var_name='end_use',value_name='kWh') # pivot

    # IMPROVEMENT: read in list of vt_loads to shorten / clean
    # IMPROVEMENT: consider selecting which loads to include in a house...

    data = data[data.end_use.isin(loads)].reset_index(drop=True)
    data.end_use = data.end_use.apply(lambda x: x.split('.')[3])

    pv = data[data.end_use.isin(['pv'])].reset_index(drop=True)
    ev = data[data.end_use.isin(['vehicle'])].reset_index(drop=True)
    data = data[~data.end_use.isin(['pv','vehicle'])].reset_index(drop=True)

    data = data.groupby(['time','hour'],as_index=False).agg(kWh = ('kWh','sum'))

    weekends_holidays = 52*2+10
    peak = range(12,21,1)       # INPUT - consider seasonal diff
    peak_rate = 0.2             # INPUT
    off_peak_rate = 0.1         # INPUT
    flat_rate = 0.15            # INPUT

    data['peak'] = data.hour.apply(lambda x: True if x in peak else False)
    data['peak_rate'] = data.peak.apply(lambda x: peak_rate if x == True else off_peak_rate)
    data['flat_rate'] = flat_rate

    annual_kWh = 750*12            # INPUT
    solar_system_ac = 8            # INPUT

    total = sum(data.kWh)
    adj = total/annual_kWh # avg annual kWh
    data['kWh_adj'] = data.kWh/adj

    total_pv = sum(pv.kWh)
    adj_pv = total_pv/(solar_system_ac * 0.148 * 8760) # 6 kW-ac system 14.8% CF
    pv['kWh_adj_pv'] = pv.kWh/-adj_pv

    ev_ = []
    home_occ = max(data.kWh_adj)
    # peak
    for row in data.values:
        if row[3] == False:

            if row[1] > 14: #and np.random.binomial(1,row[5]/home_occ) == 1:
                ev_.append(row[5]/home_occ)
            else:
                ev_.append(row[5]/(home_occ*2.2))
        else:
            ev_.append(0)

    # ADJUST EV LOAD SHAPE
    ev_mileage = 12000          # INPUT
    total_ev = sum(ev_)
    adj_ev = total_ev/(ev_mileage * .9 * .3) # home charging: 90% and efficiency 0.3 kWh/mi
    ev.kWh = ev_
    ev['kWh_adj_ev'] = ev.kWh/adj_ev

    pv_ = pv[['time','kWh_adj_pv']]
    ev_ = ev[['time','kWh_adj_ev']]

    clean = data.merge(pv_).merge(ev_)
    clean = clean[['time','hour','peak','flat_rate','peak_rate','kWh_adj','kWh_adj_pv','kWh_adj_ev']]
    clean.columns = ['time','hour','peak','flat_rate','peak_rate','kWh','kWh_pv','kWh_ev']
    clean['everything'] = clean.kWh + clean.kWh_pv + clean.kWh_ev

    clean = pd.melt(clean, id_vars=['time','hour','peak','flat_rate','peak_rate'],
        value_vars=['everything','kWh','kWh_pv','kWh_ev'],value_name='energy',var_name='load_shape')


    return clean

def format_loadshapes(data, loadshape, base_kwh, miles, pv_kw, hp_kwh):

    df = data.copy(deep=True)

    if base_kwh != 9000:
        adj = base_kwh/9000
        df.energy = df.apply(lambda row: row.energy * adj if row.end_use == 'base' else row.energy, axis=1)

    if miles != 11000:
        adj = miles/11000
        df.energy = df.apply(lambda row: row.energy * adj if row.end_use == 'ev' else row.energy, axis=1)

    if pv_kw != 9:
        adj = pv_kw/9
        df.energy = df.apply(lambda row: row.energy * adj if row.end_use == 'solar' else row.energy, axis=1)

    # if hp_kwh != 1000:
    #     adj = hp_kwh/1000
    #     df.energy = df.apply(lambda row: row.energy * adj if row.end_use == 'heatpump' else row.energy, axis=1)


    # filter
    df = df[df.end_use.isin(loadshape)].reset_index(drop=True)
    df = df[['time','hour','end_use','energy']]

    # make everything if needed
    if len(loadshape) > 1:
        everything = df.groupby(['time','hour'],as_index=False).agg(energy = ('energy','sum'))
        everything['end_use'] = 'everything'

        df = pd.concat([df,everything])

    return df

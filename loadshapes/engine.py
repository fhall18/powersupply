import ast
import numpy as np
import pandas as pd
import copy


class Rate:
    '''
    Wow! The powers of object oriented programming (OOP) are so handy! This class
    outlines the dataset objects and methods to be used in the main App. For
    those unfamiliar with OOP, it is an amazing way to associate and store all
    kinds of nifty datatypes assigned to a single object (or alias).

    In this case I am using different inputted rates (A and B) as the objects to
    determine the comparative bill impacts.

    The __init__ is the way that this object is first initialized and is set
    up with two objects for loadshapeData and loadshape (which is then updated
    in a latter method).

    Highly recommend learning this approach when things get messy and you need
    to have different datasets for different objects.
    '''
    def __init__(self,ls,rateDataset):

        # initialize datasets
        self.loadshapeData = ls
        self.loadshape = ls[(ls.type == 'base') & (ls.climate == 'Cold')]
        self.rateData = rateDataset

    def climatize(self,climate, loadType):
        ''' Switches between climate regions '''
        self.loadshape = self.loadshapeData[(self.loadshapeData['climate'] == climate) & (self.loadshapeData['type'].isin(loadType))] # single zone

    def loadAdjustment(self,loadType,climate, baseAdj,solarAdj,evAdj,ev_slider):
        if 'base' in loadType:
            totalBase = sum(self.loadshape[self.loadshape.type == 'base'].energy)
            self.loadshape.energy = self.loadshape.apply(lambda row: row['energy']/totalBase * baseAdj  if row['type'] == 'base' else row['energy'], axis=1)
        if 'pv' in loadType:
            totalSolar = sum(self.loadshape[self.loadshape.type == 'pv'].energy)
            self.loadshape.energy = self.loadshape.apply(lambda row: row['energy']/totalSolar * (-solarAdj *  1000)  if row['type'] == 'pv' else row['energy'], axis=1)
        if 'ev' in loadType:
            no_charging = np.arange(ev_slider[0],ev_slider[1]+1)
            # pull in loadshape from rates.loadshapes
            ev_t = self.loadshapeData[(self.loadshapeData.type.isin(['ev'])) & (self.loadshapeData.climate == climate)]
            # adjust based on that profile for EVs
            ev_t.energy = ev_t.apply(lambda row: 0 if row['hour'] in no_charging else row['energy'], axis=1)

            # ADJUSTMENT
            totalEV = sum(ev_t.energy)
            ev_t.energy = ev_t.energy/totalEV * (evAdj*.3)

            # join back in to loadshape
            self.loadshape.update(ev_t)


    def rateInfo(self,selection,nm_value):
        ''' This takes in a selected rate and spits out a rate schedule: value, period, tier and tier_kwh'''
        self.rateName = selection

        energyCols = [x for x in self.rateData.columns if (x.startswith('energyratestructure')) & (x.endswith('rate') or x.endswith('max'))]
        selectedRate = self.rateData[self.rateData.rateName == selection].reset_index(drop=True).iloc[:1] # filter selection
        selectedEnergy = selectedRate[energyCols].dropna(axis=1) # get energy only
        self.utility = selectedRate.utility
        # self.rateNameShort = selectedRate.name

        df_ = selectedEnergy.melt() # melt
        # df_['period'] = df_.variable.apply(lambda x: x.split('/')[1][-1:])
        df_['period'] = df_.variable.apply(lambda x: x.split('/period')[1])
        df_['period'] = df_['period'].apply(lambda x: x.split('/')[0])

        df_['tier'] = df_.variable.apply(lambda x: x.split('/')[2][4:5])

        maxTiers = df_[df_.variable.str.contains('max')]
        maxTiers.columns = ['variable','tier_kwh','period','tier']
        maxTiers = maxTiers[['tier_kwh','period','tier']]
        rateTiers = df_[~df_.variable.str.contains('max')]

        rateSchedule = rateTiers.merge(maxTiers,how='left')
        rateSchedule = rateSchedule.fillna(10000) # set to 0, could also be a big number...
        rateSchedule = rateSchedule.drop('variable',axis=1)
        rateSchedule.period = rateSchedule.period.astype('int64')

        self.selectedRate = selectedRate
        self.rateSchedule = rateSchedule


        groupedSchedule = self.rateSchedule
        groupedSchedule['weighted_value'] = groupedSchedule.tier_kwh * groupedSchedule.value
        groupedSchedule = groupedSchedule.groupby(['period'],as_index=False).agg(tier_kwh = ('tier_kwh','sum'),value = ('weighted_value','sum'))
        groupedSchedule.value = groupedSchedule.value/groupedSchedule.tier_kwh
        self.rateScheduleGrouped = groupedSchedule

        self.touInfo()

        ls = self.loadshape.groupby(['month','weekday','hour'],as_index=False).agg(energy = ('energy','sum'))
        j1 = ls.merge(self.TOU,on=['month','weekday','hour'])
        j1 = j1.groupby(['month','period'],as_index=False).agg(energy = ('energy','sum'))

        j2 = j1.merge(self.rateSchedule)
        j2['tier_cum'] = j2.groupby(['month','period'])['tier_kwh'].cumsum() # builds up the tiered amounts

        j2['tier_excess'] = abs(j2.energy) - j2.tier_cum + j2.tier_kwh
        j2['tier_actual_kwh'] = j2.apply(lambda x: x.tier_kwh if x.tier_excess >= x.tier_kwh else x.tier_excess, axis=1)
        j2['cost'] = j2.apply(lambda x: x.tier_actual_kwh * -nm_value if x.energy < 0 else x.tier_actual_kwh * x.value,axis=1)

        j3 = j2[j2.tier_actual_kwh > 0].reset_index(drop=True)
        j3['rateName'] = self.rateName


        j4 = j3.groupby(['month','period','rateName'],as_index=False).agg(energy = ('energy','mean'),cost=('cost','sum'))
        j4['rateNameShort'] = self.selectedRate.name[0]

        self.rate = j4.groupby(['month','rateName','rateNameShort'],as_index=False).agg(energy = ('energy','sum'),cost=('cost','sum'))
        self.totalCost = sum(self.rate.cost)
        self.totalEnergy = np.abs(sum(self.rate.energy))

    def touInfo(self):
        ''' This takes in a selected rate and spits out a tou schedule: value, period, hour, month '''

        n = list(range(24))
        mess = [[x+1] for x in n]*12
        hour = [item for row in mess for item in row]

        self.weekdayMatrix = ast.literal_eval(self.selectedRate.iloc[0]['energyweekdayschedule'])
        self.weekendMatrix = ast.literal_eval(self.selectedRate.iloc[0]['energyweekendschedule'])

        # update with rates
        self.weekdayMatrixRate = copy.deepcopy(self.weekdayMatrix)
        for idx,row in enumerate(self.weekdayMatrixRate):
            for col in range(len(row)):
                self.weekdayMatrixRate[idx][col] = float(self.rateScheduleGrouped.loc[self.rateScheduleGrouped['period'] == self.weekdayMatrixRate[idx][col], 'value'])

        self.weekendMatrixRate = copy.deepcopy(self.weekendMatrix)
        for idx,row in enumerate(self.weekendMatrixRate):
            for col in range(len(row)):
                self.weekendMatrixRate[idx][col] = float(self.rateScheduleGrouped.loc[self.rateScheduleGrouped['period'] == self.weekendMatrixRate[idx][col], 'value'])


        touWD = pd.DataFrame(self.weekdayMatrix).T.melt(var_name='month', value_name='period')
        touWD['hour'] = hour
        touWD['month'] = touWD.month+1
        touWD['weekday'] = 1

        touWE = pd.DataFrame(self.weekendMatrix).T.melt(var_name='month', value_name='period')
        touWE['hour'] = hour
        touWE['month'] = touWE.month+1
        touWE['weekday'] = 0

        self.TOU = pd.concat([touWE,touWD])

        self.TOU = pd.concat([touWE,touWD])

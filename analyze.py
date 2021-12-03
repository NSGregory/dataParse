from scipy import stats
import pandas as pd
import numpy as np
import pickle
from configs import Config



class Analyzer:
    def __init__(self):
        #get configurations, predominantly filepaths
        configs = Config('config.ini')
        self.file_list = configs.file_list
        self.pickled_data_file = configs.pickled_data
        self.decomposed_data_file = configs.decomposed_data
        self.headings_file = configs.headings

        #data
        self.pickled_data = self.open_pickle_file(self.pickled_data_file)
        self.decomposed_data = self.open_pickle_file(self.decomposed_data_file)
        self.headings = self.open_pickle_file(self.headings_file)

        #derived variables
        self.sets_to_analyze = self.make_set_to_analyze()

    def clean_dataframe(self, dataframe, x_val, y_val):
        """remove data cells that would prevent graphing the data"""
        df = dataframe
        vals = [x_val, y_val]
        for val in vals:
            series = pd.to_numeric(df[val], errors='coerce')
            clean_series = series.dropna(how='any')
            df[val] = clean_series
            df = df[df[val] != 999]  # in this dataset 999 is used to indicate an error
        return df

    def clean_dataset(self, dataframe, x_val, y_val, sets):
        cleaned_dataset = {}
        for set in sets:
            clean_dict = {x: self.clean_dataframe(dataframe[x], x_val, set) for x in dataframe.keys()}
            cleaned_dataset[set] = clean_dict
        return cleaned_dataset

    def rank_r2_values(self, dataframe, x_val, sets_to_analyze):
        data_list = []
        keys = list(dataframe.keys())
        for key in keys:
            current_set = dataframe[key]
            for set in sets_to_analyze:
                x_val = x_val
                y_val = set
                current_set = self.clean_dataframe(current_set, x_val, y_val)
                mask = ~np.isnan(current_set[x_val]) & ~np.isnan(current_set[y_val])
                slope, intercept, r_value, pv, se = stats.linregress(current_set[x_val][mask], current_set[y_val][mask])
                set_name = key + ": " + x_val + " by " + y_val
                data_list.append([set_name, slope, intercept, r_value, abs(r_value), pv, se])

        df = pd.DataFrame(data=data_list, columns=['Set name', 'Slope', 'Intercept', 'r^2', 'abs r^2', 'pv', 'se'])
        df.sort_values(by='abs r^2', ascending=False, inplace=True)
        df.to_excel('ranked_r2.xlsx')
        return df

    def get_headers_from_pickle(self, pickle_file):
        with open(pickle_file, 'rb') as handle:
            self.header_dict = pickle.load(handle)
            return self.header_dict

    def open_pickle_file(self, filename):
        with open(filename, 'rb') as handle:
            return pickle.load(handle)

    def make_set_to_analyze(self):
        #self.get_headers_from_pickle(self.headings_file)
        sums = [key + " sum" for key in self.headings.keys()]
        avgs = [key + " avg" for key in self.headings.keys()]
        cpt_times = ['CPT 30s', 'CPT 60s', 'CPT 90s', 'CPT 120s']
        vas_times = ['VAS10', 'VAS20', 'VAS30', 'VAS40', 'VAS50',
                     'VAS60', 'VAS70', 'VAS80', 'VAS90', 'VAS100'
                     ]

        return sums + ['SHS Total', 'SHS Heat Subscale', 'SHS Cold Subscale', 'CPT Stop Time (s)'] +cpt_times + vas_times



if __name__ == '__main__':
    analyzer = Analyzer()

    #load up all the data
    data = pd.read_pickle('C:/Users/gregoryn/Dropbox (Personal)/Science/Projects/Choir/Grit/merged_df.pickle')
    dc_data = analyzer.open_pickle_file('C:/Users/gregoryn/Dropbox (Personal)/Science/Projects/Choir/Grit/df_by_groups.pickle')
    headings_pickle = 'C:/Users/gregoryn/Dropbox (Personal)/Science/Projects/Choir/Grit/title_headings.pickle'

    #define datasets of interest
    cpt_times = ['CPT 30s', 'CPT 60s', 'CPT 90s', 'CPT 120s']
    vas_times = ['VAS10',	'VAS20',	'VAS30',	'VAS40',	'VAS50',
                 'VAS60',	'VAS70',	'VAS80',	'VAS90',	'VAS100'
                 ]
    analyzer.get_headers_from_pickle(headings_pickle)
    sums = [key+" sum" for key in analyzer.header_dict.keys() ]
    avgs = [key +" avg" for key in analyzer.header_dict.keys()]
    sets_to_analyze = sums + ['SHS Total', 'SHS Heat Subscale', 'SHS Cold Subscale',
                            'CPT Stop Time (s)'] + cpt_times + vas_times


    #dict_of_clean_data = analyzer.clean_dataset(dc_data, 'grit sum', '?', sets_to_analyze )

    #for key in list(dict_of_clean_data.keys()):
    #    dataset = dict_of_clean_data[key]

    ranked_df = analyzer.rank_r2_values(analyzer.decomposed_data, 'grit sum', analyzer.sets_to_analyze)
    # all = dc_data['all']
    # data_list = []
    # keys = list(dc_data.keys())
    # for key in keys:
    #     current_set = dc_data[key]
    #     for set in sets_to_analyze:
    #         x_val = 'grit sum'
    #         y_val = set
    #         current_set = analyzer.clean_dataframe(current_set, x_val, y_val)
    #         mask = ~np.isnan(current_set[x_val]) & ~np.isnan(current_set[y_val])
    #         slope, intercept, r_value, pv, se = stats.linregress(current_set[x_val][mask], current_set[y_val][mask])
    #         set_name = key+ ": "+ x_val + " by " + y_val
    #         data_list.append([set_name, slope, intercept, r_value, abs(r_value), pv, se])
    #
    #
    # df = pd.DataFrame(data=data_list, columns=['Set name','Slope', 'Intercept', 'r^2', 'abs r^2', 'pv', 'se'])
    # df.sort_values(by='abs r^2', ascending=False, inplace=True)
    # df.to_excel('ranked_r2.xlsx')




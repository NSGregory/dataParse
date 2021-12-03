import pandas as pd
import pickle as pk
import math
from configs import Config

configs = Config('config.ini')
filename = configs.headings_csv
outfile = configs.headings

heading_df = pd.read_csv(filename, header=None)

def clean_suffix(messy_string):
    if '_' in messy_string:
        split_string = messy_string.split('_')
        dropped_last = split_string[:-1]
        recompiled = '_'.join(dropped_last)
        return recompiled

counter = 0
heading_dict = {}
while counter < len(heading_df):
    messy_heading_list = list(heading_df.iloc[counter])
    messy_list_as_str = [str(x) for x in messy_heading_list]
    heading_list = [x for x in messy_list_as_str if x != 'nan' ]
    heading_key = clean_suffix(heading_list[0])
    heading_dict[heading_key] = heading_list
    counter += 1

with open (outfile, 'wb') as handle:
    pk.dump(heading_dict, handle, protocol=pk.HIGHEST_PROTOCOL)
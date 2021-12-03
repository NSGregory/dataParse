"""Parses excel data"""

from configs import Config
from data_reader import dataReader
from numpy import unique as np_unique
import pandas as pd
import pickle
import re

class Parser:

    def __init__(self, data):
        lab = Config('config.ini')
        self.data = data.dataset #expect this to be a dict provided by data_reader.py
        self.keys = data.key_list #keys for the above dict
        self.pooled_data = self.pool_data_frames(self.data, self.keys)


    def filter_by_list(self, list_type):
        """Filters a raw VSC list using specified parameter
        list_type: (string) the kind of list used to filter the document
                   currently supports personnel or protocol
                   """
        if list_type == "personnel":
            column = ' RP Name '
            comparison = self.personnel
        elif list_type == "protocol":
            column = ' Protocol '
            comparison = self.protocols
        else:
            print(f"{list_type} is not a supported value")
            exit
        full_data = self.data
        boolean_data_frame_result = full_data[column].isin(comparison)
        filtered_data_frame = full_data[boolean_data_frame_result]

        return filtered_data_frame

    def count_by_personnel(self, PTA=False, verbose=True):
        """Parses data for each individual in the lab.  The lab personnel included in this function is defined by
        the config.ini. """
        individual_column = ' RP Name '
        room_column = ' Room '
        # self.personnel comes from config.ini
        personnel_counts = {}
        for individual in self.personnel: #selects only the rows in the dataframe associated with an individual
            individual_filtered_result = self.column_filter(individual_column, individual)
            rooms_occupied = np_unique(individual_filtered_result[room_column])
            if verbose:
                print(f"{individual} has {len(individual_filtered_result)} cages.")
                print("  Located in:")
            individual_room_data = {}
            collated_PTA_data = {}
            for room in rooms_occupied: #for a given room, counts the occurences to determine num. cages in each room
                room_filtered_result = self.column_filter(room_column, room, individual_filtered_result)
                room_count = len(room_filtered_result)
                if verbose:
                    print(f"\t {room}: {room_count}")
                individual_room_data[room] = room_count
            if PTA == True: #for a given billing entry, counts the occurence to determine where funding comes from
                pta_list = self.pta_assigned_to_lab_personnel(frame=individual_filtered_result)
                collated_PTA_data = self.collate_pta_entries(pta_list, verbose=False)
                if verbose:
                    print("  Paid for by:")
                if verbose:
                    for key in collated_PTA_data.keys():
                        print(f"\t {key}: {collated_PTA_data[key]} cages")

            personnel_counts[individual] = [individual_room_data, collated_PTA_data]
        return personnel_counts


    def locate_genotype(self, verbose=True):
        """Gives location of each genotype belonging to the lab and the people responsible at that location"""
        full_data = self.data
        individual_column = ' RP Name '
        genotype_column = ' Species / Strain '
        room_column = ' Room '

        #narrow down to animals cared for by members of the lab
        lab_personnel_filtered_dataframe = self.filter_by_list('personnel')
        genotypes = np_unique(lab_personnel_filtered_dataframe[genotype_column])

        for genotype in genotypes:
            genotype_filtered_result = self.column_filter(genotype_column, genotype, lab_personnel_filtered_dataframe)
            rooms_occupied = np_unique(genotype_filtered_result[room_column])
            if verbose:
                print(f"There are {len(genotype_filtered_result)} cages of {genotype}.")
            for room in rooms_occupied:
                room_filtered_result = self.column_filter(room_column, room, genotype_filtered_result)
                responsible_people = np_unique(room_filtered_result[individual_column])
                if verbose:
                    print(f"  {room}: {len(room_filtered_result)}")
                    print(f"\t Responsible Personnel: {responsible_people}")


    def column_filter(self, column, filter, frame = None):
        """Return a dataframe that uses a given column to filter by a desired value"""

        # This boolean nonsense is to allow you to either enter a dataframe or leave that arg absent
        # If the arg is absent it pulls the original dataframe defined when the class object is instantiated
        # TODO: do this check better; assess if it's even needed
        noneType = type(None)
        if type(frame) == noneType:
            full_data = self.data
        else:
            full_data = frame

        boolean_data_frame_result = full_data[column] == filter
        filtered_data_frame = full_data[boolean_data_frame_result]
        return filtered_data_frame

    def flatten_pta(self, frame=None):
        """Returns the unique account PTAs regardless of shared PTA and percentage of each assignment.  This list
        is likely to contain redundant values.

        self.collate_pta_entries method can be used to pool the redundant values

        e.g., 'ABC(30), CDE(70)' is simply the reverse order of 'CDE(70), ABC(30)' and thus is redundant"""
        #allows for no frame to be specified, if so, uses the original dataframe
        #otherwise, use the dataframe provided when called
        noneType = type(None)
        if type(frame) == noneType:
            full_data = self.data
        else:
            full_data = frame

        pta_column = ' PTA (%) '
        pta_array = full_data[pta_column]
        list = np_unique(pta_array)
        output_list = []
        for entry in list:
            if entry.__contains__(','):
                sublist = entry.split(',')
                for item in sublist:
                    output_list.append(self.drop_pta_percentage(item.strip()))
            else:
                output_list.append(self.drop_pta_percentage(entry.strip()))
        return np_unique(output_list)

    def drop_pta_percentage(self, item):
        """PTA entries are in the format of ddddddd-ddd-wwwww(ddd|dd)
        so this function looks for '(' and deletes the rest of the entry"""
        return item[:item.find('(')]

    def pta_assigned_to_lab_personnel(self, frame=None):
        """Compares the given dataframe against the list of lab members and for each unique string in the PTA column
        returns both the PTA name and the number of occurences of that string in the given dataframe's PTA column."""
        #allows for no frame to be specified, if so, uses the original dataframe
        #otherwise, use the dataframe provided when called
        noneType = type(None)
        if type(frame) == noneType:
            mice_in_lab = self.filter_by_list('personnel')
        else:
            mice_in_lab = frame

        pta_column = ' PTA (%) '
        pta_in_lab = mice_in_lab[pta_column]
        unique_pta_entries = np_unique(pta_in_lab)

        list_of_counts = []
        for pta in unique_pta_entries:
            count = len(mice_in_lab[mice_in_lab[pta_column]==pta])
            list_of_counts.append([pta,count])

        return list_of_counts

    def collate_pta_entries(self, pta_list, verbose=True):
        """PTA entries can contain multiple accounts.  Within an entry, the order of the accounts listed can vary.
           This function collapses entries with equivalent values but different names into a single value.

           For example take the entries:
           abc(30), cde(70): 10 animals
           cde(70), abc(30): 15 animals

           This function will return
           abc(30), cde(70): 25 animals

           requires self.clean_pta_name"""
        collating_dict = {}

        for entry in pta_list:
            pta_name = self.clean_pta_name(entry[0])
            #print(pta_name)
            pta_count = entry[1]
            if pta_name in collating_dict.keys():
                collating_dict[pta_name] = collating_dict[pta_name] + pta_count
            else:
                collating_dict[pta_name] = pta_count

        for key in collating_dict.keys():
            if verbose:
                print(f"{key}: {collating_dict[key]} cages")

        return collating_dict

    def clean_pta_name(self,name):
        """Some entries for the PTA will include multiple accounts.  All entries are a string.
        If there are multiple entries, these will be separated by a comma (',').
        If a comma is present, this functions assume there are multiple accounts listed and will separated the string
        and remove any white space.  To prevent redundant entries, the values are sorted before being returned.

        In this case, 'ABC(30), CDE(70)' would be redundant with 'CDE(70), ABC(30)' and each input string would return
        'ABC(30), CDE(70);.

        If there is no comma, the function assumes the input is a single entry and simply returns the value."""
        if name.__contains__(','):
            sublist = name.split(',')
            whitespace_cleaned_list = [ x.strip() for x in sublist]
            whitespace_cleaned_list.sort()
            reordered_list_as_string = ', '.join(whitespace_cleaned_list)
            return reordered_list_as_string

        else:
            return name

    def show_pta_info(self, verbose=True):
        """Shorthand method for displaying the PTA info"""
        return self.collate_pta_entries(self.pta_assigned_to_lab_personnel(), verbose=verbose)

    def pool_data_frames(self, data, key_list):
        """Combining three distinct datsets with variations in structure
        Using specific values rather than programmatic approach.
        If re-using this code you will need to alter the specifics"""

        pooled_dataset = pd.DataFrame()
        for entry in key_list:
            current_frame = data[entry]
            current_frame = self.clean_subject_ID(current_frame)
            current_frame = current_frame.set_index(self.assign_col_title(current_frame))
            pooled_dataset = pooled_dataset.join(current_frame, how='right', rsuffix='_*_')


        return pooled_dataset

    def clean_subject_ID(self, frame):
        """Uses while loop so index is accessible"""
        col_title = self.assign_col_title(frame)
        column = frame[col_title]
        index_counter = 0
        while index_counter < len(column):
            m = re.match('(\d+)', str(column[index_counter])) # use str() to protect against byte types in data
            column.iloc[index_counter] = m.group()
            index_counter += 1

        return frame

    def assign_col_title(self, frame):
        if "Participant ID" in frame.columns:
            col_title = "Participant ID"
        elif "record_id" in frame.columns:
            col_title = "record_id"
        else:
            print(f"Can't find an 'id' column with this frame:{frame.columns}")

        return col_title

    def add_mean_across_columns(self, column_list, new_column_name):
        """Takes a list of columns and averages them for each row.
        That series is added to the original dataframe as a new column."""

        pertinent_df = self.pooled_data[column_list]
        self.pooled_data[new_column_name] = pertinent_df.mean(axis=1)

        return self.pooled_data

    def add_sum_across_columns(self, column_list, new_column_name):
        """Takes a list of columns and averages them for each row.
        That series is added to the original dataframe as a new column."""

        pertinent_df = self.pooled_data[column_list]
        self.pooled_data[new_column_name] = pertinent_df.sum(axis=1)

        return self.pooled_data

    def get_headers_from_pickle(self, pickle_file):
        with open(pickle_file, 'rb') as handle:
            self.header_dict = pickle.load(handle)
            return self.header_dict

    def sum_all_surveys(self):
        survey_dict = self.header_dict
        survey_keys = survey_dict.keys()
        for key in survey_keys:
            self.add_sum_across_columns(survey_dict[key], key+" sum")
        return

    def average_all_surveys(self):
        survey_dict = self.header_dict
        survey_keys = survey_dict.keys()
        for key in survey_keys:
            self.add_mean_across_columns(survey_dict[key], key+" avg")
        return

    def decompose_df_by_value(self, column_to_decompose):
        """Takes a string corresponding to a column title as input and the pooled_data dataframe from the parser object.
        The dataframe is then broken down into different dataframes based on the values in the column_to_decompose.
        The dataframes are stored in a dict with the key being the value from column_to_decompose.
        e.g.
        If column_to_decompose represents colors associated with the data and has possible values of
        'red', 'blue', and 'green' then the output will be a dict containing three entries with keys
        'red', blue', and 'green'.
        output_dict = { 'red' : df_where_color_is_red,
                        'blue' : df_where_color_is_blue,
                        'green' : df_where_color_is_green
                        }
        """
        dataframe = self.pooled_data
        output_dict = {}
        sort_values = dataframe[column_to_decompose].dropna()
        unique_values = np_unique(sort_values)
        for key in unique_values:
            output_dict[key] = dataframe[dataframe[column_to_decompose]==key]
        return output_dict

def file_to_pickle(dataset, outfile):
    with open(outfile, 'wb') as handle:
        pickle.dump(dataset, handle, protocol=pickle.HIGHEST_PROTOCOL)





if __name__ =='__main__':
    from configs import Config
    lab = Config('config.ini')
    #file to pull from to get all the column titles
    pickle_file = 'C:/Users/gregoryn/Dropbox (Personal)/Science/Projects/Choir/Grit/title_headings.pickle'

    #final comprehensive dataset output file
    df_outfile = 'C:/Users/gregoryn/Dropbox (Personal)/Science/Projects/Choir/Grit/merged_df.pickle'

    #decomposed dataset output file
    dc_df_outfile = 'C:/Users/gregoryn/Dropbox (Personal)/Science/Projects/Choir/Grit/df_by_groups.pickle'

    #create the parser object with data
    data = dataReader(lab.file_list)
    keys = data.key_list
    parser = Parser(data)

    #get all the survey column names
    headers = parser.get_headers_from_pickle(pickle_file)

    #process all the surveys
    parser.sum_all_surveys()
    parser.average_all_surveys()

    #save the resulting dataframe so display_data.py can use it
    parser.pooled_data.to_pickle(df_outfile)

    #break own the dataset into pertinent groups and then save it as a pickle file
    #also contains the full dataset undecomposed - can really be the master dataset
    grouped_dataframe_dict = parser.decompose_df_by_value('Group')
    grouped_dataframe_dict['all'] = parser.pooled_data
    file_to_pickle(grouped_dataframe_dict, dc_df_outfile)


    #sum/avg grit data
    # grit = ['grit_1','grit_2','grit_3','grit_4','grit_5','grit_6','grit_7','grit_8','grit_9',
    #         'grit_10','grit_11','grit_12']
    # parser.add_mean_across_columns(grit, 'avg grit')
    # parser.add_sum_across_columns(grit, 'total grit')

    #sum/avg state-trait anxiety index



"""
    Possible useful code
    # m.match(m_re, test_string)

    # m.group()

    # for col in df.columns:
    #     df.rename(columns={col: col.upper().replace(" ", "_")}, inplace=True)
    #
    # df_dict = {'df1': df1, 'df2': df2, 'df3': df3}
    # for name, df in df_dict.items():
    #     df.rename(lambda x: x + '_' + name, inplace=True)
"""


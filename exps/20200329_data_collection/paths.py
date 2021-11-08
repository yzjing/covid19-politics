"""
Classes and functions to handle the file paths
"""
import os
import numpy as np
import pandas as pd
# import covidtwt.utils

# logger = covidtwt.utils.get_logger(__name__)

project_root = '/l/nx/user/jingy/covid19/'

hoaxy_db_string = """
    dbname='hoaxy' user='shaoc' host='recall.ils.indiana.edu' port='5433'
    """

class HoaxyPaths:
    def __init__(
        self,
        root_dir='/l/nx/user/jingy/covid19/',
        start_day="2020-02-01",
        end_day="2020-04-24",
        chunksize=100000
    ):
        self.dates = list(pd.date_range(start=start_day, end=end_day).strftime('%Y-%m-%d'))
        self.chunksize = chunksize
        self.root_dir = root_dir

    def generate_tid_partition_mapping(self):
        if hasattr(self, 'partition_mapping'):
            return
        self.tweet_count = pd.read_csv(
            os.path.join(self.root_dir, 'tweet_count.csv')
        )
        self.tweet_count['partition'] = np.ceil(
            self.tweet_count.n_tweets / self.chunksize
        ).astype(int)
        self.partition_mapping = {
            row.date: row.partition for _, row in self.tweet_count.iterrows()
        }
        self.partition_mapping_concat_dict = {}
        for tweet_date, num_p in self.partition_mapping.items():
            self.partition_mapping_concat_dict[tweet_date] = [
                '{}_{:02d}'.format(tweet_date, i) for i in range(num_p)
            ]

        self.partition_mapping_concat_list = []
        for _, row in self.tweet_count.iterrows():
            self.partition_mapping_concat_list.extend(
                self.partition_mapping_concat_dict[row.date]
            )


class Paths:
    data_configs = {
        0: {
            'name': 'weekly_jan_01_31',
            'partition_n': 41,
            'path': 'weekly_jan_01_31/getTweetsWithMeme_11-9001249'
        },
        1: {
            'name': 'weekly_feb_01_01',
            'partition_n': 133,
            'path': 'weekly_feb_01_01/getTweetsWithMeme_11-9863349'
        },
        2: {
            'name': 'weekly_mar_02_08',
            'partition_n': 81,
            'path': 'weekly_mar_02_08/getTweetsWithMeme_11-11402886'
        },
        3: {
            'name': 'weekly_mar_09_15',
            'partition_n': 216,
            'path': 'weekly_mar_09_15/getTweetsWithMeme_27-67536594'
        },
        4: {
            'name': 'weekly_mar_16_22',
            'partition_n': 300,
            'path': 'weekly_mar_16_22/getTweetsWithMeme_27-70125557'
        },
        5: {
            'name': 'weekly_mar_23_29',
            'partition_n': 253,
            'path': 'weekly_mar_23_29/getTweetsWithMeme_11-12208308'
        },
        6: {
            'name': 'weekly_mar_30_05',
            'partition_n': 205,
            'path': 'weekly_mar_30_05/getTweetsWithMeme_11-13624198'
        },
        7: {
            'name': 'weekly_apr_06_12',
            'partition_n': 156,
            'path': 'weekly_apr_06_12/getTweetsWithMeme_24-76730664'
        },
        8: {
            'name': 'weekly_apr_13_19',
            'partition_n': 139,
            'path': 'weekly_apr_13_19/getTweetsWithMeme_24-81571415'
        },
    }
    def __init__(self):
        self.moe_data_root = project_root
        self._rename_the_raw_files()

    def _rename_the_raw_files(self):
        self.rawfile2rename = dict()
        self.renames_map = dict()
        for index, config in self.data_configs.items():
            renames = []
            for i in range(config['partition_n']+1):
                rename = 'w{:02d}p{:03d}'.format(index, i)
                raw_file_path = os.path.join(
                    self.moe_data_root,
                    config['path'],
                    'tweetContent',
                    'part-m-00{:03d}.gz'.format(i)
                )
                renames.append(rename)
                self.rawfile2rename[raw_file_path] = rename
            self.renames_map[index] = renames

        self.rename2rawfile = {
            value: index for index, value in self.rawfile2rename.items()
        }

    def get_refilenames(self, index=None, partition=None):
        if isinstance(index, int):
            renames = self.renames_map[index]
        else:
            if index is None:
                index = list(self.data_configs.keys())
            renames = []
            for i in index:
                for rename in self.renames_map[i]:
                    renames.append(rename)

        if partition is None:
            return renames
        else:
            return renames[:partition]

    def get_rawfilenames(self, index=None, partition=None):
        renames = self.get_refilenames(index=index, partition=partition)
        return list(map(self.rename2rawfile.get, renames))

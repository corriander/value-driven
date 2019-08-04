import abc
import re
import collections
import itertools
import warnings

import numpy as np

try:
    import pandas as pd
    import xlrd
except ImportError:
    warnings.warn('`pandas` and `xlrd` packages required for '
                  'spreadsheet support.')

from .. import common


class CODASheet(common.ABC):

    # ----------------------------------------------------------------
    # Simple record classes for transfering data from source.
    # ----------------------------------------------------------------
    CDefRecord = collections.namedtuple(
        'CDefRecord',
        ['name', 'min', 'max']
    )

    ReqRecord = collections.namedtuple(
        'ReqRecord',
        ['name', 'weight']
    )

    MinMaxRelRecord = collections.namedtuple(
        'MinMaxRelRecord',
        ['requirement', 'characteristic', 'relationship_type',
         'correlation', 'neutral_value']
    )

    OptRelRecord = collections.namedtuple(
        'OptRelRecord',
        ['requirement', 'characteristic', 'relationship_type',
         'correlation', 'optimum_value', 'tolerance']
    )

    @abc.abstractmethod
    def get_characteristics(self):
        """Characteristic definitions."""
        return list[()]

    @abc.abstractmethod
    def get_requirements(self):
        """Requirements and their weighting."""
        return list[()]

    @abc.abstractmethod
    def get_relationships(self):
        """Relationships between requirements and characteristics."""
        return list[()]




class ExcelParser(CODASheet):

    # 20 characteristic definitions are supported ((4*26)/5 cols)
    _MAX_COL = 'CZ'
    _NCOLS_CHAR = 4

    def __init__(self, path):
        self.path = path

    @property
    def df(self):
        """DataFrame of requirement-characteristic relationships."""
        try:
            return self._df
        except AttributeError:
            df = self._df = pd.read_excel(self.path, skiprows=[0,1])
            return df

    @property
    def cdf(self):
        """DataFrame of characteristic definitions.

        This augments the regular DataFrame.
        """
        try:
            return self._cdf
        except AttributeError:
            df = pd.read_excel(
                self.path,
                usecols="C:{}".format(self._MAX_COL)
            )[:1]

        return self._cdf_base(df)

    def _cdf_base(self, df):
            dd = collections.defaultdict(list)
            for i, s in enumerate(df.columns):

                ridx = i % self._NCOLS_CHAR # Relative index

                if ridx == 0:
                    # Initial column of group; begin construct.
                    dd['name'].append(s)

                elif ridx == 1:
                    dd['min'].append(df.iloc[0, i])

                elif ridx == 3:
                    # Final column of group; add construct to list.
                    dd['max'].append(df.iloc[0, i])

            self._cdf = tdf = pd.DataFrame.from_dict(dd)
            return tdf

    def get_characteristics(self):
        """Returns a 3-tuple: (<name>, <minvalue>, <maxvalue>).

        If the minimum or maximum values are omitted, NaN(s) will be
        returned.
        """
        l = []
        for rec in self.cdf.to_records():
            if re.match(r'^(Unnamed: \d+|Characteristic \d+)$',
                        rec['name']) is not None:
                warnings.warn("Picked up a default column name")
            else:
                l.append(
                    self.CDefRecord(
                        name=rec['name'],
                        min=rec['min'],
                        max=rec['max']
                    )
                )
        return l

    def get_relationships(self):
        """Get relationships defined a 4/5-tuple.

        Size of tuple depends on the type of relationship.
        """
        # TODO: Yeah I know, variable return type.
        reqts = [tup[0] for tup in self.get_requirements()]
        chars = [tup[0] for tup in self.get_characteristics()]

        return self._parse_row(reqts, chars)

    def _parse_row(self, reqts, chars):

        n = self._NCOLS_CHAR
        df = self.df.loc[:,'Correlation':]

        relationships = []
        for (i, r), (j, c) in itertools.product(enumerate(reqts),
                                                enumerate(chars)):
            row = df.loc[i,:].values
            base_tup = (r, c, row[j*n+1], row[j*n+0], row[j*n+2])

            if np.isnan(base_tup[4]):
                # The target value is always a quantity.
                continue

            if base_tup[2] == 'opt':
                tup = self.OptRelRecord(*(base_tup + (row[j*n+3],)))
            else:
                tup = self.MinMaxRelRecord(*base_tup)

            relationships.append(tup)

        return relationships

    def get_requirements(self):
        cols = ('Weighting', 'Requirements')
        return [self.ReqRecord(*reversed(tuple(rec)[1:])) # Exclude idx
                for rec in self.df.loc[:,cols].to_records()]


class CompactExcelParser(ExcelParser):

    _NCOLS_CHAR = 3

    def _cdf_base(self, df):
            dd = collections.defaultdict(list)
            for i, s in enumerate(df.columns):

                ridx = i % self._NCOLS_CHAR # Relative index

                if ridx == 0:
                    # Initial column of group; begin construct.
                    dd['name'].append(s)

                elif ridx == 1:
                    dd['min'].append(df.iloc[0, i])

                elif ridx == 2:
                    # Final column of group; add construct to list.
                    dd['max'].append(df.iloc[0, i])

            self._cdf = tdf = pd.DataFrame.from_dict(dd)
            return tdf

    def _parse_row(self, reqts, chars):
        n = self._NCOLS_CHAR
        df = self.df.loc[:,'Relationship Type':]

        relationships = []
        for (i, r), (j, c) in itertools.product(enumerate(reqts),
                                                enumerate(chars)):
            row = df.loc[i,:].values
            rel = row[j*n]

            try:
                type_ = {'+': 'max', 'o': 'opt', '-': 'min'}[rel[0]]
            except (TypeError, IndexError):
                # rel is not a recognised string.
                continue

            base_tup = (r, c, type_, rel, row[j*n+1])

            if np.isnan(base_tup[4]):
                # The target value is always a quantity.
                continue

            if base_tup[2] == 'opt':
                tup = self.OptRelRecord(*(base_tup + (row[j*n+2],)))
            else:
                tup = self.MinMaxRelRecord(*base_tup)

            relationships.append(tup)

        return relationships


class GSheetCODA(common.io.AbstractGSheet, CompactExcelParser):

    @property
    def df(self):
        """Raw dataframe representing the CODA table."""
        try:
            return self._cached_df
        except AttributeError:
            self._cached_df = self._facade.get_sheet_as_dataframe()
            return self._cached_df

    @property
    def characteristic_df(self):
        """Dataframe containing characteristic definitions.

        Each row is a characteristic (index) with min/max bounds for
        the possible values.
        """
        # Characteristics are the first row (sparse, excluding the
        # label in B1).
        label = self.df.columns[1]
        df = self._drop_df_columns_by_index(self.df, [0, 1])
        df = self._extract_characteristic_bounds(df)
        df = df.set_index('name')
        df.index.name = label
        return df

    @staticmethod
    def _drop_df_columns_by_index(df, indices):
        keep = set(range(df.shape[1])).difference(set(indices))
        return df.iloc[:,list(sorted(keep))]

    def _extract_characteristic_bounds(self, df):
        # Glue to improve readibility; TODO: deprecate "_cdf_base"
        return self._cdf_base(df)

    @property
    def requirement_df(self):
        """Dataframe containing the requirements with weighting."""
        label = self.df.iloc[2,0]
        df = self.df.iloc[2:,:2]
        df.columns = ['Requirement', 'Weight']
        df = df.set_index('Requirement')
        df.index.name = 'Requirement'
        return df

    @property
    def relationship_df(self):
        """Dataframe containing the relationships."""
        # Fill all column headers (currently they are sparse)

        df = self.df
        df.columns = pd.Series(df.columns).replace('', np.nan).ffill()

        # Preserve the relationship fields (tolerance etc.)
        relationship_fields = self.df.iloc[1,2:]

        # Get rid of the first two rows (characteristic bounds and
        # relationship field labels)
        df = self.df.drop([0, 1, 2])

        # Get rid of the requirements weighting column, we don't need
        # it here.
        df = self._drop_df_columns_by_index(df, [1])

        # Requirements (index) column is currently NaN label
        df.columns = df.columns.fillna('Requirements')
        df = df.set_index('Requirements')

        # Convert the columns into a multi-index
        arrays = [relationship_fields.index.values,
                  relationship_fields.values]
        df.columns = pd.MultiIndex.from_tuples(
            list(zip(*arrays)),
            names=['characteristic', 'relationship_property']
        )

        return df

    def is_valid(self):
        return False

    def get_characteristics(self):
        return [()]

    def get_requirements(self):
        return [()]

    def get_relationships(self):
        return [()]

    def update(self, df):
        return None

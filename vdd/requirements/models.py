from __future__ import division

import itertools
import random
import warnings

import numpy as np
import pandas as pd

try:
    import jinja
except ImportError:
    df_styling_available = False
else:
    df_styling_available = True

from . import io


class BinWM(object):
    """Binary Weighting Matrix

    Used to model relative importance of requirements. Each
    requirement is assessed to be less or more important than every
    other requirement in turn. This allows us to calculate a weighted
    set of requirements.
    """
    # This class deliberately provides a restricted API limiting
    # access to the underlying data; this helps maintain integrity and
    # limits complexity in keeping it in sync with source data.

    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------

        *args : str
            Requirements provided as N positional args.

        matrix : np.matrix, optional
            Square binary matrix for N requirements.
        """
        self.requirements = args
        default_matrix = np.matrix(np.zeros([len(args), len(args)]))
        matrix = kwargs.get('matrix', default_matrix)
        self._matrix = matrix

    @classmethod
    def from_google_sheet(cls, workbook_name):
        """Construct the binary matrix from a Google Sheet.

        The spreadsheet must be a standard format (see included Excel
        examples).
        """
        sheet = cls._get_sheet(workbook_name)
        inst = cls(*sheet.get_requirements())
        inst._sheet = sheet
        inst._matrix = sheet.get_value_matrix()
        return inst

    @property
    def matrix(self):
        """Copy of the weighting matrix."""
        return np.copy(self._matrix)

    @property
    def score(self):
        """Calculate the relative score."""
        sum_x = self.matrix.sum(axis=1)
        sum_y = np.triu(1 - self.matrix, k=1).sum(axis=0).T

        sum_combined = sum_x + sum_y
        sum_biased = sum_combined + 1

        return sum_biased / sum_biased.sum()

    @staticmethod
    def _get_sheet(workbook_name):
        # Helper method for constructing a sheet
        return io.GSheetBinWM(workbook_name)

    @staticmethod
    def _input(prompt_string):
        # Wrapper for testing
        return input(prompt_string)

    @staticmethod
    def _print(string):
        # Wrapper for testing
        print(string)

    @staticmethod
    def _set_df_styling(df):
        # Center align and (attempt to) equally space columns
        # This has an additional dependency which we just deal with by
        # making this a no-op if it's not available.
        if not df_styling_available:
            warnings.warn("Install jinja for dataframe styling")
            return df

        properties = {'width':'15em', 'text-align':'center'}
        styles = [{
            'selector': 'th',
            'props': [('text-align', 'center')]
        }]
        df.style.set_properties(**properties).set_table_styles(styles)
        return df

    def to_dataframe(self):
        """Convert to a pandas dataframe.

        Returns
        -------

        pd.DataFrame
        """
        df = pd.DataFrame(
            data=self.matrix,
            columns=self.requirements,
            index=self.requirements
        )
        return self._set_df_styling(df)

    def prompt(self, shuffle=True):
        """Step through an interactive prompt to calculate weighting.

        Parameters
        ----------

        shuffle: bool
            Shuffle the comparisons so each decision is presented in
            random order.
        """
        reqs = self.requirements
        combinations = itertools.combinations(reqs, 2)
        coordinates = itertools.combinations(range(len(reqs)), 2)

        self._print("Please agree (y) or disagree (n) with the "
                    "following statements:\n")
        iterable = zip(coordinates, combinations)
        decisions = []
        for x, grp in itertools.groupby(iterable, lambda o: o[1][0]):
            for (i, j), (this, other) in grp:
                decisions.append((i, j, this, other))

        if shuffle:
            random.shuffle(decisions)

        for i, j, this, other in decisions:

                # Keep asking until response is valid
                while True:
                    response = self._input(
                        "'{}' is more important than '{}': "
                        .format(this, other)
                    )
                    if response in 'yn':
                        break
                    else:
                        self._print(
                            "Sorry I didn't understand...\n\n"
                        )

                self._matrix[i, j] = 1 if response == 'y' else 0

    def save(self):
        """If created from a google sheet, update it.

        Raises
        ------

        NotImplementedError
            Where not created from a google sheet (no _sheet
            attribute).
        """
        try:
            sheet = self._sheet
        except AttributeError:
            raise NotImplementedError(
                "Saving only implemented for {} instances "
                "created via 'from_google_sheet' constructor"
            )

        sheet.update(self.to_dataframe())

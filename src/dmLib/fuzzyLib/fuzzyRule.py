import skfuzzy as fuzz
import numpy as np

class fuzzyRule():

    def __init__(self,input_statements,output,label=''):

        """
        Constructor

        Parameters
        ----------
        input_statements: list 
            list of dicts 
            structure of each dict
            {
                'fun1': fuzzyFunction object
                'fun2': fuzzyFunction object
                operator: 'AND', 'OR'
            }
        
        # TODO: add case for only one set

        Optional
        --------
        label: str
            string to tag instance with
        """

        self.input_statements = input_statements
        self.output = output
        self.label = label

    def apply(self,input):
        """
        Apply rule on fuzzy sets

        Parameters
        ----------
        input: dict
            dict of structure
            {
                'label': float,
                'label': float,
            }

        Returns
        -------
        activation: np.array
            1d array of length universe
            holding activation function 
            values

        """

        rules = 1.0

        for statement in self.input_statements:

            fun1 = statement['fun1']
            fun2 = statement['fun2']

            # The OR operator means we take the maximum of these two.
            # The AND operator means we take the minimum of these two.

            if statement['operator'] == 'AND':
                rule = np.fmin(fun1.interp(input[fun1.label]), fun2.interp(input[fun2.label]))
            elif statement['operator'] == 'OR':
                rule = np.fmax(fun1.interp(input[fun1.label]), fun2.interp(input[fun2.label]))

            # TODO: add case for no operator

            rules = np.fmin(rules,rule) # AND statement between each line of statements

        # Now we apply rule by clipping the top off the corresponding output
        # membership function with `np.fmin`
        activation = np.fmin(rules, self.output.getArray())  # removed entirely to 0

        return activation

        
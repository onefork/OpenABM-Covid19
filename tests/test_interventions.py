#!/usr/bin/env python3
"""
Tests of the individual-based model, COVID19-IBM, using the individual file

Usage:
With pytest installed (https://docs.pytest.org/en/latest/getting-started.html) tests can be 
run by calling 'pytest' from project folder.  

Created: March 2020
Author: p-robot
"""

import pytest
import subprocess
import sys
import numpy as np, pandas as pd
from scipy import optimize
from math import sqrt
from numpy.core.numeric import NaN

sys.path.append("src/COVID19")
from parameters import ParameterSet
from model import OccupationNetworkEnum
from . import constant
from . import utilities as utils

# from test.test_bufio import lengths
# from CoreGraphics._CoreGraphics import CGRect_getMidX


def pytest_generate_tests(metafunc):
    # called once per each test function
    funcarglist = metafunc.cls.params[metafunc.function.__name__]
    argnames = sorted(funcarglist[0])
    metafunc.parametrize(
        argnames, [[funcargs[name] for name in argnames] for funcargs in funcarglist]
    )


class TestClass(object):
    params = {
        "test_zero_quarantine": [dict()],
        "test_hospitalised_zero": [dict()],
        "test_quarantine_interactions": [
            dict(
                test_params=dict(
                    n_total=50000,
                    quarantined_daily_interactions=0,
                    end_time=25,
                    infectious_rate=4,
                    self_quarantine_fraction=1.0,
                    daily_non_cov_symptoms_rate=0.0,
                )
            ),
            dict(
                test_params=dict(
                    n_total=50000,
                    quarantined_daily_interactions=1,
                    end_time=25,
                    infectious_rate=4,
                    self_quarantine_fraction=0.75,
                    daily_non_cov_symptoms_rate=0.0005,
                )
            ),
            dict(
                test_params=dict(
                    n_total=50000,
                    quarantined_daily_interactions=2,
                    end_time=25,
                    infectious_rate=4,
                    self_quarantine_fraction=0.50,
                    daily_non_cov_symptoms_rate=0.001,
                )
            ),
            dict(
                test_params=dict(
                    n_total=50000,
                    quarantined_daily_interactions=3,
                    end_time=25,
                    infectious_rate=4,
                    self_quarantine_fraction=0.25,
                    daily_non_cov_symptoms_rate=0.005,
                )
            ),
        ],
        "test_quarantine_on_symptoms": [
            dict(
                test_params=dict(
                    n_total=50000,
                    end_time=25,
                    infectious_rate=4,
                    self_quarantine_fraction=0.8,
                    daily_non_cov_symptoms_rate=0.0,
                    asymptomatic_infectious_factor=0.4,
                )
            ),
            dict(
                test_params=dict(
                    n_total=50000,
                    end_time=1,
                    infectious_rate=4,
                    self_quarantine_fraction=0.5,
                    daily_non_cov_symptoms_rate=0.05,
                    asymptomatic_infectious_factor=1.0,
                )
            ),
        ],
        "test_quarantine_household_on_symptoms": [ 
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 20,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    quarantine_household_on_symptoms = 1
                )
            ) 
        ],
        "test_trace_on_symptoms": [ 
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 20,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    trace_on_symptoms = 1,
                    quarantine_on_traced = 1,
                    app_turn_on_time = 1,
                    quarantine_household_on_symptoms = 1
                ),
                app_users_fraction = 0.85

            ) 
        ],
        "test_lockdown_transmission_rates": [ 
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 10000,
                    end_time = 3,
                    infectious_rate = 4,
                    lockdown_occupation_multiplier_primary_network = 0.8,
                    lockdown_occupation_multiplier_secondary_network = 0.8,
                    lockdown_occupation_multiplier_working_network= 0.8,
                    lockdown_occupation_multiplier_retired_network= 0.8,
                    lockdown_occupation_multiplier_elderly_network= 0.8,
                    lockdown_random_network_multiplier = 0.8,
                    lockdown_house_interaction_multiplier = 1.2
                )
            ) 
        ],
         "test_app_users_fraction": [ 
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 20,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    trace_on_symptoms = 1,
                    quarantine_on_traced = 1,
                    app_turn_on_time = 1,
                    app_users_fraction_0_9 = 0,
                    app_users_fraction_10_19 = 0.8,
                    app_users_fraction_20_29 = 0.8,
                    app_users_fraction_30_39 = 0.8,
                    app_users_fraction_40_49 = 0.8,
                    app_users_fraction_50_59 = 0.8,
                    app_users_fraction_60_69 = 0.8,
                    app_users_fraction_70_79 = 0.4,
                    app_users_fraction_80 = 0.2,
                    traceable_interaction_fraction = 1
                ),

            ),
        ],
        "test_risk_score_household": [
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 10,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    quarantine_household_on_symptoms = 1
                ),
                min_age_inf = 2, 
                min_age_sus = 2
            ),
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 10,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    quarantine_household_on_symptoms = 1
                ),
                min_age_inf = 1, 
                min_age_sus = 3
            )
        ],
        "test_risk_score_age": [
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 10,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    trace_on_symptoms = 1,
                    quarantine_on_traced = 1,
                    app_turn_on_time = 0
                ),
                min_age_inf = 2, 
                min_age_sus = 2
            )
        ],
        "test_risk_score_days_since_contact": [
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 10,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    trace_on_symptoms = 1,
                    quarantine_on_traced = 1,
                    app_turn_on_time = 0
                ),
                days_since_contact = 2, 
            ),
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 10,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    trace_on_symptoms = 1,
                    quarantine_on_traced = 1,
                    app_turn_on_time = 0
                ),
                days_since_contact = 4 
            )
        ],
        "test_risk_score_multiple_contact": [
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 10,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    trace_on_symptoms = 1,
                    quarantine_on_traced = 1,
                    app_turn_on_time = 0,
                    traceable_interaction_fraction = 1,
                    daily_non_cov_symptoms_rate = 0
                ),
                days_since_contact    = 2,
                required_interactions = 1
            ),
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 500,
                    end_time = 10,
                    infectious_rate = 4,
                    self_quarantine_fraction = 1.0,
                    trace_on_symptoms = 1,
                    quarantine_on_traced = 1,
                    app_turn_on_time = 0,
                    traceable_interaction_fraction = 1,
                    daily_non_cov_symptoms_rate = 0
                ),
                days_since_contact    = 3,
                required_interactions = 2
            ),
        ],
        "test_quarantine_household_on_trace_positive_not_symptoms": [
            dict(
                test_params = dict( 
                    n_total = 100000,
                    n_seed_infection = 100,
                    end_time = 10,
                    infectious_rate = 6,
                    self_quarantine_fraction = 1.0,
                    trace_on_symptoms = True,
                    trace_on_positive = True,
                    test_on_symptoms = True,
                    quarantine_on_traced = True,
                    app_turn_on_time = 0,
                    traceable_interaction_fraction = 1,
                    daily_non_cov_symptoms_rate = 0,
                    test_order_wait = 1,
                    test_result_wait = 1,
                    quarantine_household_on_positive = True,
                    quarantine_household_on_symptoms = True,
                    quarantine_household_on_traced_positive = True,
                    quarantine_household_on_traced_symptoms = False,
                    quarantine_dropout_traced = 0,
                    mean_time_to_hospital = 30
                ),
            )
        ]
    }
    """
    Test class for checking 
    """
    def test_zero_quarantine(self):
        """
        Test there are no individuals quarantined if all quarantine parameters are "turned off"
        """
        params = ParameterSet(constant.TEST_DATA_FILE, line_number = 1)
        params = utils.turn_off_quarantine(params)
        params.write_params(constant.TEST_DATA_FILE)
        
        # Call the model
        file_output = open(constant.TEST_OUTPUT_FILE, "w")
        completed_run = subprocess.run([constant.command], stdout = file_output, shell = True)
        df_output = pd.read_csv(constant.TEST_OUTPUT_FILE, comment = "#", sep = ",")
        np.testing.assert_equal(df_output["n_quarantine"].to_numpy().sum(), 0)
    
    def test_hospitalised_zero(self):
        """
        Test setting hospitalised fractions to zero (should be no hospitalised)
        """
        params = ParameterSet(constant.TEST_DATA_FILE, line_number = 1)
        params = utils.set_hospitalisation_fraction_all(params, 0.0)
        params.write_params(constant.TEST_DATA_FILE)
        
        # Call the model, pipe output to file, read output file
        file_output = open(constant.TEST_OUTPUT_FILE, "w")
        completed_run = subprocess.run([constant.command], stdout = file_output, shell = True)
        df_output = pd.read_csv(constant.TEST_OUTPUT_FILE, comment = "#", sep = ",")
        
        np.testing.assert_equal(df_output["n_hospital"].sum(), 0)
    
    def test_quarantine_interactions(self, test_params):
        """
        Tests the number of interactions people have on the interaction network is as 
        described when they have been quarantined
        """
        tolerance = 0.01
        end_time = test_params["end_time"]

        params = ParameterSet(constant.TEST_DATA_FILE, line_number=1)
        params = utils.turn_off_interventions(params, end_time)
        params.set_param(test_params)
        params.write_params(constant.TEST_DATA_FILE)

        file_output = open(constant.TEST_OUTPUT_FILE, "w")
        completed_run = subprocess.run([constant.command], stdout=file_output, shell=True)
        
        df_trans = pd.read_csv(constant.TEST_TRANSMISSION_FILE, 
            sep = ",", comment = "#", skipinitialspace = True)
            
        df_indiv = pd.read_csv(constant.TEST_INDIVIDUAL_FILE, 
            sep = ",", comment = "#", skipinitialspace = True)
        
        df_int = pd.read_csv(constant.TEST_INTERACTION_FILE, 
            comment = "#", sep = ",", skipinitialspace = True)
        
        # Merge columns from transmission file into individual file
        df_indiv = pd.merge(df_indiv, df_trans, 
            left_on = "ID", right_on = "ID_recipient", how = "left")
        
        # get the people who are in quarantine and were on the previous step
        df_quar = df_indiv[
            (df_indiv["quarantined"] == 1) & (df_indiv["time_quarantined"] < end_time)
        ]
        df_quar = df_quar.loc[:, "ID"]

        # get the number of interactions by type
        df_int = df_int.groupby(["ID_1", "type"]).size().reset_index(name="connections")

        # check to see there are no work connections
        df_test = pd.merge(
            df_quar, df_int[df_int["type"] == constant.OCCUPATION], 
            left_on = "ID", right_on = "ID_1", how="inner"
        )
        
        np.testing.assert_equal(
            len(df_test), 0, "quarantined individual with work contacts"
        )

        # check to see there are are household connections
        df_test = pd.merge(
            df_quar, df_int[df_int["type"] == constant.HOUSEHOLD], 
            left_on = "ID", right_on = "ID_1", how="inner"
        )
        np.testing.assert_equal(
            len(df_test) > 0,
            True,
            "quarantined individuals have no household connections",
        )
        
        # check to whether the number of random connections are as specified
        df_test = pd.merge(
            df_quar, df_int[df_int["type"] == constant.RANDOM], 
            left_on = "ID", right_on = "ID_1", how="inner"
        )
        
        df_test.fillna(0, inplace=True)
        
        # In some instances df_test has zero rows
        if len(df_test) == 0:
            expectation = 0
        else:
            expectation = df_test.loc[:, "connections"].mean()
        
        np.testing.assert_allclose(
            expectation,
            float(params.get_param("quarantined_daily_interactions")),
            rtol=tolerance,
        )

    def test_quarantine_on_symptoms(self, test_params):
        """
        Tests the correct proportion of people are self-isolating on sypmtoms
        """

        tolerance = 0.01
        tol_sd = 4
        end_time = test_params["end_time"]

        params = ParameterSet(constant.TEST_DATA_FILE, line_number=1)
        params = utils.turn_off_interventions(params, end_time)
        params.set_param(test_params)
        params.write_params(constant.TEST_DATA_FILE)

        file_output = open(constant.TEST_OUTPUT_FILE, "w")
        completed_run = subprocess.run([constant.command], stdout=file_output, shell=True)
        df_indiv = pd.read_csv(
            constant.TEST_INDIVIDUAL_FILE, comment="#", sep=",", skipinitialspace=True
        )
        
        df_trans = pd.read_csv(constant.TEST_TRANSMISSION_FILE)
        df_indiv = pd.read_csv(constant.TEST_INDIVIDUAL_FILE)
        df_indiv = pd.merge(df_indiv, df_trans, 
            left_on = "ID", right_on = "ID_recipient", how = "left")
        
        # get the people who are in quarantine and were on the last step
        df_quar = df_indiv[
            (df_indiv["quarantined"] == 1) & (df_indiv["time_quarantined"] == end_time)
        ]
        df_quar = df_quar.loc[:, "ID"]
        n_quar = len(df_quar)

        # get the people who developed symptoms on the last step
        df_symp = df_indiv[(df_indiv["time_symptomatic"] == end_time)]
        n_symp = len(df_symp)

        # if no seasonal flu or contact tracing then this is the only path
        if test_params["daily_non_cov_symptoms_rate"] == 0:
            df = pd.merge(df_quar, df_symp, on="ID", how="inner")
            np.testing.assert_equal(
                n_quar,
                len(df),
                "people quarantined without symptoms when daily_non_cov_symptoms_rate turned off",
            )

            n_exp_quar = n_symp * test_params["self_quarantine_fraction"]
            np.testing.assert_allclose(
                n_exp_quar,
                n_quar,
                atol=tol_sd * sqrt(n_exp_quar),
                err_msg="the number of quarantined not explained by symptoms",
            )

        # if no symptomatic then check number of newly quarantined is from flu
        elif end_time == 1 and test_params["asymptomatic_infectious_factor"] == 1:
            n_flu = test_params["n_total"] * test_params["daily_non_cov_symptoms_rate"]
            n_exp_quar = n_flu * test_params["self_quarantine_fraction"]

            np.testing.assert_allclose(
                n_exp_quar,
                n_quar,
                atol=tol_sd * sqrt(n_exp_quar),
                err_msg="the number of quarantined not explained by daily_non_cov_symptoms_rate",
            )

        else:
            np.testing.assert_equal(
                True, False, "no test run due test_params not being testable"
            )
    
    def test_quarantine_household_on_symptoms(self, test_params ):
        """
        Tests households are quarantine when somebody has symptoms
        """
        end_time = test_params[ "end_time" ]

        params = ParameterSet(constant.TEST_DATA_FILE, line_number=1)
        params = utils.turn_off_interventions(params, end_time)
        params.set_param(test_params)
        params.write_params(constant.TEST_DATA_FILE)

        file_output = open(constant.TEST_OUTPUT_FILE, "w")
        completed_run = subprocess.run([constant.command], stdout = file_output, shell = True)
        df_int = pd.read_csv( constant.TEST_INTERACTION_FILE, 
            comment="#", sep=",", skipinitialspace=True )
        df_trace = pd.read_csv( constant.TEST_TRACE_FILE, 
            comment="#", sep=",", skipinitialspace=True )
        
        # prepare the interaction data to get all household interations
        df_int.rename( columns = { "ID_1":"index_ID", "ID_2":"traced_ID"}, inplace = True )
        df_int[ "household" ] = ( df_int[ "house_no_1" ] == df_int[ "house_no_2" ] )
        df_int = df_int.loc[ :, [ "index_ID", "traced_ID", "household"]]
                
        # don't consider ones with multiple index events
        filter_single = df_trace.groupby( ["index_ID", "days_since_index"] ).size();
        filter_single = filter_single.groupby( ["index_ID"]).size().reset_index(name="N");
        filter_single = filter_single[ filter_single[ "N"] == 1 ]
        
        # look at the trace token data to get all traces
        index_traced = df_trace[ ( df_trace[ "time" ] == end_time ) & ( df_trace[ "days_since_contact" ] == 0 ) ] 
        index_traced = index_traced.groupby( [ "index_ID", "traced_ID" ] ).size().reset_index(name="cons")    
        index_traced[ "traced" ] = True
        index_traced = pd.merge( index_traced, filter_single, on = "index_ID", how = "inner")
       
        # get all the interactions for the index cases
        index_cases  = pd.DataFrame( data = { 'index_ID': index_traced.index_ID.unique() } )
        index_inter = pd.merge( index_cases, df_int, on = "index_ID", how = "left" )             
        index_inter = index_inter.groupby( [ "index_ID", "traced_ID", "household" ]).size().reset_index(name="N")    
        index_inter[ "inter" ] = True

        # test nobody traced without an interaction
        t = pd.merge( index_traced, index_inter, on = [ "index_ID", "traced_ID" ], how = "outer" )
        n_no_inter = len( t[ t[ "inter"] != True ] )
        np.testing.assert_equal( n_no_inter, 0, "tracing someone without an interaction" )

        # check everybody with a household interaction is traced
        n_no_trace = len( t[ ( t[ "traced"] != True ) &  (t["household"] == True  )] )
        np.testing.assert_equal( n_no_trace, 0, "failed to trace someone in the household" )

    def test_lockdown_transmission_rates(self, test_params):
        """
        Tests the change in transmission rates on lockdown are correct
        NOTE - this can only be done soon after a random seed and for small
        changes due to saturation effects
        """
        
        sd_diff  = 3;
        end_time = test_params[ "end_time" ]

        params = ParameterSet(constant.TEST_DATA_FILE, line_number=1)
        params = utils.turn_off_interventions(params, end_time)
        params.set_param(test_params)
        params.write_params(constant.TEST_DATA_FILE)
        
        # run without lockdown
        file_output   = open(constant.TEST_OUTPUT_FILE, "w")
        completed_run = subprocess.run([constant.command], stdout=file_output, shell=True)
        df_without    = pd.read_csv( constant.TEST_TRANSMISSION_FILE, comment="#", sep=",", skipinitialspace=True )
        df_without    = df_without[ df_without[ "time_infected"] == end_time ].groupby( [ "infector_network"] ).size().reset_index(name="N")

        # lockdown on t-1
        params = utils.turn_off_interventions(params, end_time)
        params.set_param(test_params)
        params.write_params(constant.TEST_DATA_FILE)
        params.set_param( "lockdown_time_on", end_time - 1 );
        params.write_params(constant.TEST_DATA_FILE)
        
        file_output   = open(constant.TEST_OUTPUT_FILE, "w")
        completed_run = subprocess.run([constant.command], stdout=file_output, shell=True)
        df_with       = pd.read_csv( constant.TEST_TRANSMISSION_FILE, comment="#", sep=",", skipinitialspace=True )
        df_with       = df_with[ df_with[ "time_infected"] == end_time ].groupby( [ "infector_network"] ).size().reset_index(name="N")
        
        # now check they are line
        expect_household = df_without.loc[ constant.HOUSEHOLD, ["N"] ] * test_params[ "lockdown_house_interaction_multiplier" ]       
        np.testing.assert_allclose( df_with.loc[ constant.HOUSEHOLD, ["N"] ], expect_household, atol = sqrt( expect_household ) * sd_diff, 
                                    err_msg = "lockdown not changing household transmission as expected" )
        for oc_net in OccupationNetworkEnum:
            expect_work = df_without.loc[ constant.OCCUPATION, ["N"] ] * test_params[ f"lockdown_occupation_multiplier{oc_net.name}" ]       
            np.testing.assert_allclose( df_with.loc[ constant.OCCUPATION, ["N"] ], expect_work, atol = sqrt( expect_work) * sd_diff, 
                                    err_msg = "lockdown not changing work transmission as expected" )
      
      
        expect_random = df_without.loc[ constant.RANDOM, ["N"] ] * test_params[ "lockdown_random_network_multiplier" ]       
        np.testing.assert_allclose( df_with.loc[ constant.RANDOM, ["N"] ], expect_random, atol = sqrt( expect_random ) * sd_diff, 
                                    err_msg = "lockdown not changing random transmission as expected" )
      

    def test_trace_on_symptoms(self, test_params, app_users_fraction ):
        """
        Tests that people who are traced on symptoms are
        real contacts
        """
        end_time = test_params[ "end_time" ]

        params = ParameterSet(constant.TEST_DATA_FILE, line_number=1)
        params = utils.turn_off_interventions(params, end_time)
        params = utils.set_app_users_fraction_all( params, app_users_fraction )
        params.set_param(test_params)
        params.write_params(constant.TEST_DATA_FILE)

        file_output = open(constant.TEST_OUTPUT_FILE, "w")
        completed_run = subprocess.run([constant.command], stdout=file_output, shell=True)
        df_int   = pd.read_csv( constant.TEST_INTERACTION_FILE, comment="#", sep=",", skipinitialspace=True )
        df_trace = pd.read_csv( constant.TEST_TRACE_FILE, comment="#", sep=",", skipinitialspace=True )

        # prepare the interaction data to get all household interations
        df_int.rename( columns = { "ID_1":"index_ID", "ID_2":"traced_ID"}, inplace = True )
        df_int[ "household" ] = ( df_int[ "house_no_1" ] == df_int[ "house_no_2" ] )
        df_int = df_int.loc[ :, [ "index_ID", "traced_ID", "household"]]

        # don't consider ones with multiple index events
        filter_single = df_trace.groupby( ["index_ID", "days_since_index"] ).size();
        filter_single = filter_single.groupby( ["index_ID"]).size().reset_index(name="N");
        filter_single = filter_single[ filter_single[ "N"] == 1 ]

        # look at the trace token data to get all traces
        index_traced = df_trace[ ( df_trace[ "time" ] == end_time ) & ( df_trace[ "days_since_contact" ] == 0 ) ] 
        index_traced = index_traced.groupby( [ "index_ID", "traced_ID" ] ).size().reset_index(name="cons")    
        index_traced[ "traced" ] = True
        index_traced = pd.merge( index_traced, filter_single, on = "index_ID", how = "inner")

        # get all the interactions for the index cases
        index_cases  = pd.DataFrame( data = { 'index_ID': index_traced.index_ID.unique() } )
        index_inter = pd.merge( index_cases, df_int, on = "index_ID", how = "left" )             
        index_inter = index_inter.groupby( [ "index_ID", "traced_ID", "household" ]).size().reset_index(name="N")    
        index_inter[ "inter" ] = True

        # test nobody traced without an interaction
        t = pd.merge( index_traced, index_inter, on = [ "index_ID", "traced_ID" ], how = "outer" )
        n_no_inter = len( t[ t[ "inter"] != True ] )
        np.testing.assert_equal( n_no_inter, 0, "tracing someone without an interaction" )    

    
    def test_app_users_fraction(self, test_params ):
        """
        Tests that the correct number of people are assigned
        use the app and that only app users start tracing 
        and can be traced if household options are not turned on
        """
        end_time = test_params[ "end_time" ]

        params = ParameterSet(constant.TEST_DATA_FILE, line_number=1)
        params.set_param(test_params)
        params.write_params(constant.TEST_DATA_FILE)

        file_output = open(constant.TEST_OUTPUT_FILE, "w")
        completed_run = subprocess.run([constant.command], stdout=file_output, shell=True)
        df_indiv = pd.read_csv( constant.TEST_INDIVIDUAL_FILE, comment="#", sep=",", skipinitialspace=True )
        
        df_trans = pd.read_csv(constant.TEST_TRANSMISSION_FILE)
        df_indiv = pd.read_csv(constant.TEST_INDIVIDUAL_FILE)
        df_indiv = pd.merge(df_indiv, df_trans, 
            left_on = "ID", right_on = "ID_recipient", how = "left")
        
        app_users  = df_indiv[ df_indiv[ "app_user" ] == 1 ].groupby( [ "age_group" ] ).size().reset_index(name="app_users")    
        all_users  = df_indiv.groupby( [ "age_group" ] ).size().reset_index(name="all")    
        app_params = [ "app_users_fraction_0_9", "app_users_fraction_10_19",  "app_users_fraction_20_29",  
            "app_users_fraction_30_39",  "app_users_fraction_40_49", "app_users_fraction_50_59",    
            "app_users_fraction_60_69",  "app_users_fraction_70_79", "app_users_fraction_80" ]
        
        for age in constant.AGES:
            if test_params[ app_params[ age ] ] == 0 :
                users = app_users[ app_users[ "age_group"] == age ]
                np.testing.assert_equal( len( users ), 0, "nobody should have a phone in this age group" )
            else :
                n     = all_users[ all_users[ "age_group"] == age ].iloc[0,1]
                users = app_users[ app_users[ "age_group"] == age ].iloc[0,1]
                np.testing.assert_allclose( users / n, test_params[ app_params[ age ] ], atol = 0.01, err_msg = "wrong fraction of users have app in age group")
            
        df_trace     = pd.read_csv( constant.TEST_TRACE_FILE, comment="#", sep=",", skipinitialspace=True )
        index_traced = df_trace[ ( df_trace[ "time" ] == end_time ) & ( df_trace[ "days_since_contact" ] == 0 ) ] 
        index_traced = index_traced.groupby( [ "index_ID", "traced_ID" ] ).size().reset_index(name="cons")    
        index_traced = index_traced[ index_traced[ "index_ID" ] != index_traced[ "traced_ID" ] ]
        np.testing.assert_equal( len( index_traced ) > 0, True, "no tracing has occured") 
        
        df_indiv.rename( columns = { "ID":"index_ID" }, inplace = True )
        test = pd.merge( index_traced, df_indiv, on = "index_ID", how = "left")
        np.testing.assert_equal( len( test[ test[ "app_user" ] != 1 ] ), 0, "non-app users starting tracing" ) 
        
        df_indiv.rename( columns = { "index_ID":"traced_ID" }, inplace = True )
        test = pd.merge( index_traced, df_indiv, on = "traced_ID", how = "left")
        np.testing.assert_equal( len( test[ test[ "app_user" ] != 1 ] ), 0, "non-app users being traced" )
    
    def test_risk_score_household(self, test_params, min_age_inf, min_age_sus):
        """
        Test that if risk score for household quarantining is set to 0 for the youngest
        as either the index or traced that they are not quarantined
        """
   
        params = utils.get_params_swig()
        for param, value in test_params.items():
            params.set_param( param, value )  
        params.set_param("rng_seed", 1)      
        model  = utils.get_model_swig( params )
        
        # now update the risk scoring map
        for age_inf in range( constant.N_AGE_GROUPS ):
            for age_sus in range( constant.N_AGE_GROUPS ):
                if ( age_inf < min_age_inf ) | (age_sus < min_age_sus ):
                    model.set_risk_score_household( age_inf, age_sus, 0 )
        
        # step through the model and write the relevant files the end
        for time in range( test_params[ "end_time" ]  ):
            model.one_time_step();    
        model.write_individual_file()
        model.write_trace_tokens()
  
        df_indiv = pd.read_csv( constant.TEST_INDIVIDUAL_FILE, comment="#", sep=",", skipinitialspace=True )
        df_trace = pd.read_csv( constant.TEST_TRACE_FILE, comment="#", sep=",", skipinitialspace=True )

        # find the index case for the new time_step
        index_traced = df_trace[ ( df_trace[ "time" ] == test_params[ "end_time" ]  ) & ( df_trace[ "days_since_index" ] == 0 ) ] 
        index_traced = index_traced.groupby( [ "index_ID", "traced_ID" ] ).size().reset_index(name="cons")    

        # get the age and house_no
        age_house        = df_indiv.loc[ :,["ID", "age_group", "house_no"]]
        index_age_house  = age_house.rename( columns = { "ID":"index_ID",  "house_no":"index_house_no",  "age_group":"index_age_group"})
        traced_age_house = age_house.rename( columns = { "ID":"traced_ID", "house_no":"traced_house_no", "age_group":"traced_age_group"})

        index_traced = pd.merge( index_traced, index_age_house,  on = "index_ID",  how = "left")
        index_traced = pd.merge( index_traced, traced_age_house, on = "traced_ID", how = "left")
            
        # now perform checks
        np.testing.assert_equal( len( index_traced ) > 50, 1, "less than 50 traced people, in-sufficient to test" )
        np.testing.assert_equal( min( index_traced[ "index_age_group"] ),  min_age_inf,  "younger people than minimum allowed are index case from which tracing has occurred" )
        np.testing.assert_equal( min( index_traced[ "traced_age_group"] ), min_age_sus, "younger people than minimum allowed are traced" )
        np.testing.assert_equal( max( index_traced[ "index_age_group"] ),  constant.N_AGE_GROUPS-1,  "oldest age group are not index cases" )
        np.testing.assert_equal( max( index_traced[ "traced_age_group"] ), constant.N_AGE_GROUPS-1,  "oldest age group are not traced" )
       
    def test_risk_score_age(self, test_params, min_age_inf, min_age_sus):
        """
        Test that if risk score quarantining is set to 0 for the youngest
        as either the index or traced that they are not quarantined
        """
   
        params = utils.get_params_swig()
        for param, value in test_params.items():
            params.set_param( param, value )  
        model  = utils.get_model_swig( params )
        
        # now update the risk scoring map
        for day in range( constant.MAX_DAILY_INTERACTIONS_KEPT ):
            for age_inf in range( constant.N_AGE_GROUPS ):
                for age_sus in range( constant.N_AGE_GROUPS ):
                    if ( age_inf < min_age_inf ) | (age_sus < min_age_sus ):
                        model.set_risk_score( day, age_inf, age_sus, 0 )
        
        # step through the models and write the relevant files at the end
        for time in range( test_params[ "end_time" ]  ):
            model.one_time_step();    
        model.write_individual_file()
        model.write_trace_tokens()
  
        df_indiv = pd.read_csv( constant.TEST_INDIVIDUAL_FILE, comment="#", sep=",", skipinitialspace=True )
        df_trace = pd.read_csv( constant.TEST_TRACE_FILE, comment="#", sep=",", skipinitialspace=True )

        # find the index case for the new time_step
        index_traced = df_trace[ ( df_trace[ "time" ] == test_params[ "end_time" ]  ) & ( df_trace[ "days_since_index" ] == 0 ) ] 
        index_traced = index_traced.groupby( [ "index_ID", "traced_ID" ] ).size().reset_index(name="cons")    

        # get the age and house_no
        age_house        = df_indiv.loc[ :,["ID", "age_group", "house_no"]]
        index_age_house  = age_house.rename( columns = { "ID":"index_ID",  "house_no":"index_house_no",  "age_group":"index_age_group"})
        traced_age_house = age_house.rename( columns = { "ID":"traced_ID", "house_no":"traced_house_no", "age_group":"traced_age_group"})

        index_traced = pd.merge( index_traced, index_age_house,  on = "index_ID",  how = "left")
        index_traced = pd.merge( index_traced, traced_age_house, on = "traced_ID", how = "left")
            
        # now perform checks
        np.testing.assert_equal( len( index_traced ) > 50, 1, "less than 50 traced people, in-sufficient to test" )
        np.testing.assert_equal( min( index_traced[ "index_age_group"] ),  min_age_inf,  "younger people than minimum allowed are index case from which tracing has occurred" )
        np.testing.assert_equal( min( index_traced[ "traced_age_group"] ), min_age_sus, "younger people than minimum allowed are traced" )
        np.testing.assert_equal( max( index_traced[ "index_age_group"] ),  constant.N_AGE_GROUPS-1,  "oldest age group are not index cases" )
        np.testing.assert_equal( max( index_traced[ "traced_age_group"] ), constant.N_AGE_GROUPS-1,  "oldest age group are not traced" )
       
    def test_risk_score_days_since_contact(self, test_params, days_since_contact):
        """
        Test that if risk score quarantining is set to be 0 for days greater
        than days since contact
        """
   
        params = utils.get_params_swig()
        for param, value in test_params.items():
            params.set_param( param, value )  
        model  = utils.get_model_swig( params )
        
        # now update the risk scoring map
        for day in range( constant.MAX_DAILY_INTERACTIONS_KEPT ):
            for age_inf in range( constant.N_AGE_GROUPS ):
                for age_sus in range( constant.N_AGE_GROUPS ):
                    if day > days_since_contact:
                        model.set_risk_score( day, age_inf, age_sus, 0 )
        
        # step through the model and write the trace tokens at the end
        for time in range( test_params[ "end_time" ]  ):
            model.one_time_step();    
        model.write_trace_tokens()
  
        df_trace = pd.read_csv( constant.TEST_TRACE_FILE, comment="#", sep=",", skipinitialspace=True )

        # find the index case for the new time_step
        index_traced = df_trace[ ( df_trace[ "time" ] == test_params[ "end_time" ]  ) & ( df_trace[ "days_since_index" ] == 0 ) ] 
        index_traced = index_traced.groupby( [ "index_ID", "traced_ID", "days_since_contact" ] ).size().reset_index(name="cons")    
       
        # now perform checks
        np.testing.assert_equal( len( index_traced ) > 50, 1, "less than 50 traced people, in-sufficient to test" )
        np.testing.assert_equal( max( index_traced[ "days_since_contact"] ) <= days_since_contact, 1,  "tracing contacts from longer ago than risk score allows" )
       
    def test_risk_score_multiple_contact(self, test_params, days_since_contact, required_interactions):
        """
        Test that if risk score quarantining is set to be 0 for days greater
        than days since contact and per_interaction_score for days less or equal,
        make sure we only quarantine people who have sufficient multiple contacts
        """
        
        per_interaction_score = 1 / required_interactions + 0.0001
        
        params = utils.get_params_swig()
        for param, value in test_params.items():
            params.set_param( param, value )  
        model  = utils.get_model_swig( params )
        
        # now update the risk scoring map
        for day in range( constant.MAX_DAILY_INTERACTIONS_KEPT ):
            for age_inf in range( constant.N_AGE_GROUPS ):
                for age_sus in range( constant.N_AGE_GROUPS ):
                    model.set_risk_score( day, age_inf, age_sus, per_interaction_score )
                    if day > days_since_contact:
                        model.set_risk_score( day, age_inf, age_sus, 0 )
        
        # step through time until we need to start to save the interactions each day
        for time in range( test_params[ "end_time" ] - days_since_contact - 1 ):
            model.one_time_step();   
       
        # now get the interactions each day  
        df_inter = []
        for time in range( days_since_contact + 1 ):
            model.one_time_step();
            model.write_interactions_file();
            df_temp = pd.read_csv( constant.TEST_INTERACTION_FILE, comment="#", sep=",", skipinitialspace=True )
            df_temp[ "days_since_symptoms" ] = days_since_contact - time
            df_inter.append(df_temp)
        df_inter = pd.concat( df_inter )
        df_inter.rename( columns = { "ID_1":"index_ID", "ID_2":"traced_ID"}, inplace = True )

        # get the individuals who have the app
        model.write_individual_file()
        df_indiv  = pd.read_csv( constant.TEST_INDIVIDUAL_FILE, comment="#", sep=",", skipinitialspace=True )
        app_users = df_indiv.loc[ :,["ID", "app_user"]]
     
        # only consider interactions between those with the app
        app_users = app_users.rename( columns = { "ID":"index_ID", "app_user":"index_app_user"})
        df_inter  = pd.merge( df_inter, app_users, on = 'index_ID', how = "left" )
        app_users = app_users.rename( columns = { "index_ID":"traced_ID", "index_app_user":"traced_app_user"})
        df_inter  = pd.merge( df_inter, app_users, on = 'traced_ID', how = "left" )
        df_inter  = df_inter[ ( df_inter[ "index_app_user" ] == True ) & ( df_inter[ "traced_app_user" ] == True ) ]
                
        # calculate the number of pairwise interactions of the relevant number of days
        df_inter = df_inter.groupby( [ "index_ID", "traced_ID" ] ).size().reset_index(name="n_interactions")
     
        # now look at the number of people asked to quarnatine
        model.write_trace_tokens()
        df_trace = pd.read_csv( constant.TEST_TRACE_FILE, comment="#", sep=",", skipinitialspace=True )

        # find the index case for the new time_step
        index_traced = df_trace[ ( df_trace[ "time" ] == test_params[ "end_time" ]  ) & ( df_trace[ "days_since_index" ] == 0 ) ] 
        index_traced = index_traced.groupby( [ "index_ID", "traced_ID" ] ).size().reset_index(name="cons")    
        index_cases  = pd.DataFrame( data = { 'index_ID': index_traced.index_ID.unique() } )

        # now for the index cases get all the individual with with they had sufficient interactions
        index_inter = pd.merge( index_cases, df_inter, on = "index_ID", how = "left" )
        index_inter = index_inter[ index_inter[ "n_interactions"] >= required_interactions]
            
        df_all = pd.merge( index_inter, index_traced, on = [ "index_ID", "traced_ID"], how = "outer")           
              
        # now perform checks
        np.testing.assert_equal( len( index_traced ) > 50, 1, "less than 50 traced people, in-sufficient to test" )
        np.testing.assert_equal( len( index_inter ), len( index_traced ), "incorrect number of people traced" )
        np.testing.assert_equal( len( index_inter ), len( df_all ), "incorrect number of people traced" )

    def test_quarantine_household_on_trace_positive_not_symptoms(self, test_params ):
        """
        Test that we quarantine people's household only on a positive test
        and on symptoms we don't ask them to quarantine
        
        Note: we need to set dropout to 0 otherwise some people drop out between 
        amber and read and their households are not quarantined
        
        Also, we need to set mean time to hospital to a large number, otherwise if they were 
        hospitalised at the time the red signal went out it won't be transmitted on (however
        the household would be quarantined anyway since they are a first order contact)
        
        When testing that households are not quarantined on amber we need to set a 
        tolerance due to the fact that it is possible for 2 people in the same house
        to be direct contacts of an index case
        
        """
        
        tol = 0.01
         
        params = utils.get_params_swig()
        for param, value in test_params.items():
            params.set_param( param, value )  
        model  = utils.get_model_swig( params )
           
        # step through time until we need to start to save the interactions each day
        for time in range( test_params[ "end_time" ] ):
            model.one_time_step();   
       
        # get the individuals who have the app
        model.write_individual_file()
        model.write_transmissions()
        df_trans = pd.read_csv(constant.TEST_TRANSMISSION_FILE)
        df_indiv = pd.read_csv(constant.TEST_INDIVIDUAL_FILE)
        df_indiv = pd.merge(df_indiv, df_trans, 
            left_on = "ID", right_on = "ID_recipient", how = "left")
                
        house_no  = df_indiv.loc[ :,["ID", "house_no"]]
        house_no.rename( columns = { "ID":"traced_ID", "house_no":"traced_house_no"}, inplace = True )
        total_house = house_no.groupby( ["traced_house_no"]).size().reset_index(name="total_per_house")
        is_case   = df_indiv.loc[ :,["ID", "is_case", "house_no"]]
        is_case.rename( columns = { "ID":"index_ID"}, inplace = True )

        # now look at the number of people asked to quarantine
        model.write_trace_tokens()
        df_trace = pd.read_csv( constant.TEST_TRACE_FILE, comment="#", sep=",", skipinitialspace=True )

        # add on house_no and case status to the transmissions and count the number of traced per house
        df_trace = pd.merge( df_trace, house_no, on = "traced_ID", how = "left")
        df_trace = pd.merge( df_trace, is_case, on = "index_ID", how = "left")
        df_trace[ "same_house" ] = ( df_trace[ "house_no"] == df_trace[ "traced_house_no"] ) 
        trace_grouped = df_trace.groupby( ["index_ID", "is_case","same_house","traced_house_no"]).size().reset_index(name="n_per_house")
      
        # for those who are not cases, we should not have traced household members 
        not_case =  trace_grouped[ ( trace_grouped[ "same_house"] == False ) & ( trace_grouped[ "is_case"] == 0 ) ]      
        np.testing.assert_equal( len( not_case ) > 50, 1, "less than 50 index cases, in-sufficient to test" )
        np.testing.assert_equal( sum( not_case[ "n_per_house"] > 1 ) / len( not_case )  < tol, 1, "traced more than one person in a household based on symptoms" )
    
        # for cases we we should have traced everyone in the household of the traded
        case = trace_grouped[ trace_grouped[ "is_case"] == 1 ]
        case = pd.merge( case, total_house, on = "traced_house_no", how = "left")
        case[ "hh_not_q"] = case[ "total_per_house"] - case[ "n_per_house"]
        case = case[ ( case[ "same_house"] == False ) ];
        np.testing.assert_equal( len( case ) > 50, 1, "less than 50 index cases, in-sufficient to test" )
        np.testing.assert_equal( sum( ( case[ "hh_not_q"] != 0 ) ), 0, "member of household of first-order contact not traced on positive" )
                
        
    
    
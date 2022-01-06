import pytest
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
from typing import List, Tuple

from dmLib import Design, gaussianFunc, uniformFunc, MarginNode, Performance, MarginNetwork, InputSpec, Behaviour, compute_cdf

# Input set 1
@pytest.fixture
def stochastic_inputs() -> Tuple[gaussianFunc,gaussianFunc]:
    # Target threshold
    mu = np.array([4.0,])
    Sigma = np.array([[0.3**2,],])
    threshold = gaussianFunc(mu, Sigma, 'T1')

    # decided value (capability)
    mu = np.array([4.6,])
    Sigma = np.array([[0.3**2,],])
    decided_value = gaussianFunc(mu, Sigma, 'B1')

    return threshold, decided_value

@pytest.fixture
def deterministic_inputs():
    # Target threshold
    threshold = 4.0

    # decided value (capability)
    decided_value = 5.8

    return threshold, decided_value

@pytest.fixture
def Impact_test_inputs():
    # test decided values and target thresholds for checking impact matrix calculation
    dv_vector = np.array([0.5,0.5,0.25])
    tt_vector = np.array([0.25,0.25,0.75])

    return dv_vector,tt_vector

@pytest.fixture
def Absorption_test_inputs():
    # test decided values for checking absorption matrix calculation
    dv_vector = np.array([4.0,2.0,2.0])

    return dv_vector

@pytest.fixture
def deterministic_specs():
    # Define input specs
    centers = np.array([1.2,1.0])
    s1 = InputSpec(centers[0],'S1',symbol='T1',inc = -1e-0,inc_type='rel')
    s2 = InputSpec(centers[1],'S2',symbol='T2',inc = -1e-0,inc_type='rel')
    input_specs = [s1,s2]

    return centers,input_specs

@pytest.fixture
def stochastic_specs():
    # Define input specs
    centers = np.array([1.2,1.0])
    ranges = np.ones(2) * 0.1
    dist = uniformFunc(centers,ranges)
    s1 = InputSpec(centers[0],'S1',symbol='T1',inc = -1e-0,inc_type='rel',distribution=dist,cov_index=0)
    s2 = InputSpec(centers[1],'S2',symbol='T2',inc = -1e-0,inc_type='rel',distribution=dist,cov_index=1)
    input_specs = [s1,s2]

    return dist,centers,ranges,input_specs

@pytest.fixture
def man_components():
    # Define behaviour models
    class B1(Behaviour):
        def __call__(self,s1,s2):
            # Analytical behaviour models in terms of input specs
            tt1_model = lambda spec : (spec[0]**2) + (2*spec[0]) + (spec[1])
            tt2_model = lambda spec : spec[0] + 2*spec[1]
            tt3_model = lambda spec : spec[0] + spec[1]

            self.threshold = [tt1_model((s1,s2)),tt2_model((s1,s2)),tt3_model((s1,s2))]

            return self.threshold

    class B2(Behaviour):

        def __init__(self, key: str = ''):
            super().__init__(key=key)
            self.p1_model = lambda dv : (dv[0]**2) + (dv[1]**2) + (2*dv[2]**2)
            self.p2_model = lambda dv : dv[0] + 2*dv[1] + dv[2]

        def __call__(self,dv1,dv2,dv3):
            # Analytical test performance models in terms of decided values
            self.performance = [self.p1_model((dv1,dv2,dv3)),self.p2_model((dv1,dv2,dv3))]

            return self.threshold

    b1 = B1('B1')
    b2 = B2('B1')
    behaviours = [b1,b2,]

    # Define performances
    p1 = Performance('P1')
    p2 = Performance('P1')
    performances = [p1,p2]

    # Define margin nodes
    e1 = MarginNode('E1',type='must_exceed')
    e2 = MarginNode('E2',type='must_exceed')
    e3 = MarginNode('E3',type='must_exceed')
    margin_nodes = [e1,e2,e3]

    return behaviours, performances, margin_nodes

@pytest.fixture
def noise():
    # Gaussian noise for adding stochasticity
    return gaussianFunc(0.0,0.00125)

def test_deterministic_MarginNode(deterministic_inputs):
    """
    Tests the MarginNode excess calculation method for deterministic threshold and behaviour
    """

    # # DEBUG:
    # # Target threshold
    # threshold = 4.0

    # # decided value (capability)
    # decided_value = 5.8

    # example_mean_std = (threshold, decided_value)

    ######################################################
    # Defining a MarginNode object

    threshold, decided_value = deterministic_inputs

    ######################################################
    # Check excess calculation for one sample
    ThermalNode = MarginNode('EM1')
    ThermalNode(decided_value,threshold)
    assert ThermalNode.values == np.array([decided_value-threshold])

    ######################################################
    # Check return for multiple inputs
    ThermalNode.reset()
    ThermalNode(np.ones(10)*decided_value,np.ones(10)*threshold)
    assert (ThermalNode.values == np.ones(10) * (decided_value-threshold)).all()

def test_stochastic_MarginNode(stochastic_inputs):
    """
    Tests the MarginNode excess calculation method for stochastic threshold and behaviour
    """

    # # DEBUG:
    # # Target threshold
    # mu = np.array([4.0,])
    # Sigma = np.array([[0.3**2,],])
    # threshold = gaussianFunc(mu, Sigma, 'T1')

    # # decided value (capability)
    # mu = np.array([4.6,])
    # Sigma = np.array([[0.3**2,],])
    # decided_value = gaussianFunc(mu, Sigma, 'B1')

    # stochastic_inputs = (threshold, decided_value)

    ######################################################

    # Defining a MarginNode object
    threshold, decided_value = stochastic_inputs
    decided_value.samples
    
    ######################################################
    # Check excess calculation for one sample
    ThermalNode = MarginNode('EM1')
    ThermalNode(decided_value(),threshold())
    assert ThermalNode.values == decided_value.samples-threshold.samples

    ######################################################
    # Check sampling accuracy of mean and standard deviaction of excess

    ThermalNode.reset()
    decided_value.reset()
    threshold.reset()

    mu_excess = decided_value.mu - threshold.mu # calculate composite random variable mean
    Sigma_excess = decided_value.Sigma + (((-1)**2) * threshold.Sigma) # calculate composite random variable variance

    ThermalNode(decided_value(10000),threshold(10000))
    
    # Check that means and variances of excess
    assert np.math.isclose(np.mean(ThermalNode.values), mu_excess.squeeze(), rel_tol=1e-1)
    assert np.math.isclose(np.var(ThermalNode.values), Sigma_excess.squeeze(), rel_tol=1e-1)

    ######################################################
    # Check that CDF computation is correct
    ThermalNode(decided_value(10000),threshold(10000))
    bin_centers, cdf, excess_limit, reliability = compute_cdf(ThermalNode.values,bins=500,
        cutoff=ThermalNode.cutoff,buffer_limit=ThermalNode.buffer_limit)

    test_excess_pdf = norm(loc=mu_excess,scale=np.sqrt(Sigma_excess))
    test_reliability = 1 - test_excess_pdf.cdf(0).squeeze() 
    test_excess_limit = test_excess_pdf.ppf(0.9).squeeze()
    test_excess_cdf = test_excess_pdf.cdf(bin_centers).squeeze()

    # ThermalNode.view_cdf(xlabel='Excess')
    # ThermalNode.axC.plot(bin_centers,test_excess_cdf,'--r')
    # ThermalNode.figC.show()

    assert np.math.isclose(reliability, test_reliability, rel_tol=1e-1)
    assert np.math.isclose(excess_limit, test_excess_limit, rel_tol=1e-1)
    assert np.allclose(cdf, test_excess_cdf, atol=1e-1)

    ######################################################
    # Check visualization
    # ThermalNode.value_dist(1000)
    # ThermalNode.value_dist.view()

def test_deterministic_ImpactMatrix(man_components,Impact_test_inputs):
    """
    Tests the ImpactMatrix calculation method for deterministic threshold and decided values
    """
    
    # # DEBUG:
    # # Define behaviour models
    # class B1(Behaviour):
    #     def __call__(self,s1,s2):
    #         # Analytical behaviour models in terms of input specs
    #         tt1_model = lambda spec : (spec[0]**2) + (2*spec[0]) + (spec[1])
    #         tt2_model = lambda spec : spec[0] + 2*spec[1]
    #         tt3_model = lambda spec : spec[0] + spec[1]

    #         self.threshold = [tt1_model((s1,s2)),tt2_model((s1,s2)),tt3_model((s1,s2))]

    #         return self.threshold

    # class B2(Behaviour):

    #     def __init__(self, key: str = ''):
    #         super().__init__(key=key)
    #         self.p1_model = lambda dv : (dv[0]**2) + (dv[1]**2) + (2*dv[2]**2)
    #         self.p2_model = lambda dv : dv[0] + 2*dv[1] + dv[2]

    #     def __call__(self,dv1,dv2,dv3):
    #         # Analytical test performance models in terms of decided values
    #         self.performance = [self.p1_model((dv1,dv2,dv3)),self.p2_model((dv1,dv2,dv3))]

    #         return self.threshold

    # b1 = B1('B1')
    # b2 = B2('B1')
    # behaviours = [b1,b2,]

    # # Define performances
    # p1 = Performance('P1')
    # p2 = Performance('P1')
    # performances = [p1,p2]

    # # Define margin nodes
    # e1 = MarginNode('E1',type='must_exceed')
    # e2 = MarginNode('E2',type='must_exceed')
    # e3 = MarginNode('E3',type='must_exceed')
    # margin_nodes = [e1,e2,e3]

    # man_components = [behaviours, performances, margin_nodes]

    # # test decided values and target thresholds for checking impact matrix calculation
    # dv_vector = np.array([0.5,0.5,0.25])
    # tt_vector = np.array([0.25,0.25,0.75])

    # Impact_test_inputs = (dv_vector, tt_vector)

    ######################################################
    # Construct MAN

    behaviours, performances, margin_nodes  = man_components
    dv_vector, tt_vector                    = Impact_test_inputs

    # Define the MAN
    class MAN(MarginNetwork):
        def forward(self):

            # retrieve MAN components
            e1 = self.margin_nodes[0]
            e2 = self.margin_nodes[1]
            e3 = self.margin_nodes[2]

            # get performances
            p1 = self.performances[0]
            p2 = self.performances[1]

            # get behaviour
            b1 = self.behaviours[0]
            b2 = self.behaviours[1]

            # Execute behaviour models
            b2(dv_vector[0],dv_vector[1],dv_vector[2])

            # Compute excesses
            e1(tt_vector[0],dv_vector[0])
            e2(tt_vector[1],dv_vector[1])
            e3(tt_vector[2],dv_vector[2])

            # Compute performances
            p1(b2.performance[0])
            p2(b2.performance[1])

    man = MAN([],[],[],behaviours,margin_nodes,performances,'MAN_test')

    ######################################################
    # Create training data and train response surface
    n_samples = 100
    excess_space = Design(np.zeros(len(margin_nodes)),np.ones(len(margin_nodes)),n_samples,'LHS').unscale()

    p_space = np.empty((n_samples,len(performances)))
    p_space[:,0] = np.apply_along_axis(man.behaviours[1].p1_model,axis=1,arr=excess_space+dv_vector) # mat + vec is automatically broadcasted
    p_space[:,1] = np.apply_along_axis(man.behaviours[1].p2_model,axis=1,arr=excess_space+dv_vector) # mat + vec is automatically broadcasted

    man.train_performance_surrogate(n_samples=100,ext_samples=(excess_space,p_space))
    man.forward()
    man.compute_impact()

    # Check outputs
    input = np.tile(tt_vector,(len(margin_nodes),1))

    p = np.empty((len(margin_nodes),len(performances)))
    p[:,0] = np.apply_along_axis(man.behaviours[1].p1_model,axis=1,arr=input)
    p[:,1] = np.apply_along_axis(man.behaviours[1].p2_model,axis=1,arr=input)

    np.fill_diagonal(input,dv_vector)

    p_t = np.empty((len(margin_nodes),len(performances)))
    p_t[:,0] = np.apply_along_axis(man.behaviours[1].p1_model,axis=1,arr=input)
    p_t[:,1] = np.apply_along_axis(man.behaviours[1].p2_model,axis=1,arr=input)

    test_impact = (p - p_t) / p_t

    # test_impact = np.array([
    #     [ 0.42857143,  0.16666667],
    #     [ 0.42857143,  0.4       ],
    #     [-0.61538462, -0.22222222]
    #     ])

    assert np.allclose(man.impact_matrix.impact, test_impact, rtol=1e-3)

def test_stochastic_ImpactMatrix(man_components,Impact_test_inputs,noise):
    """
    Tests the ImpactMatrix calculation method for stochastic threshold and decided values
    """
    
    # # DEBUG:
    # # Define behaviour models
    # class B1(Behaviour):
    #     def __call__(self,s1,s2):
    #         # Analytical behaviour models in terms of input specs
    #         tt1_model = lambda spec : (spec[0]**2) + (2*spec[0]) + (spec[1])
    #         tt2_model = lambda spec : spec[0] + 2*spec[1]
    #         tt3_model = lambda spec : spec[0] + spec[1]

    #         self.threshold = [tt1_model((s1,s2)),tt2_model((s1,s2)),tt3_model((s1,s2))]

    #         return self.threshold

    # class B2(Behaviour):

    #     def __init__(self, key: str = ''):
    #         super().__init__(key=key)
    #         self.p1_model = lambda dv : (dv[0]**2) + (dv[1]**2) + (2*dv[2]**2)
    #         self.p2_model = lambda dv : dv[0] + 2*dv[1] + dv[2]

    #     def __call__(self,dv1,dv2,dv3):
    #         # Analytical test performance models in terms of decided values
    #         self.performance = [self.p1_model((dv1,dv2,dv3)),self.p2_model((dv1,dv2,dv3))]

    #         return self.threshold

    # b1 = B1('B1')
    # b2 = B2('B1')
    # behaviours = [b1,b2,]

    # # Define performances
    # p1 = Performance('P1')
    # p2 = Performance('P1')
    # performances = [p1,p2]

    # # Define margin nodes
    # e1 = MarginNode('E1',type='must_exceed')
    # e2 = MarginNode('E2',type='must_exceed')
    # e3 = MarginNode('E3',type='must_exceed')
    # margin_nodes = [e1,e2,e3]

    # man_components = [behaviours, performances, margin_nodes]

    # # test decided values and target thresholds for checking impact matrix calculation
    # dv_vector = np.array([0.5,0.5,0.25])
    # tt_vector = np.array([0.25,0.25,0.75])

    # Impact_test_inputs = (dv_vector, tt_vector)

    # noise = gaussianFunc(0.0,0.00125)

    ######################################################
    # Construct MAN

    behaviours, performances, margin_nodes  = man_components
    dv_vector, tt_vector                    = Impact_test_inputs

    # Define the MAN
    class MAN(MarginNetwork):
        def forward(self):

            # retrieve MAN components
            e1 = self.margin_nodes[0]
            e2 = self.margin_nodes[1]
            e3 = self.margin_nodes[2]

            # get performances
            p1 = self.performances[0]
            p2 = self.performances[1]

            # get behaviour
            b1 = self.behaviours[0]
            b2 = self.behaviours[1]

            # Execute behaviour models
            b2(dv_vector[0],dv_vector[1],dv_vector[2])

            # Compute excesses
            e1(tt_vector[0]+noise(),dv_vector[0]+noise())
            e2(tt_vector[1]+noise(),dv_vector[1]+noise())
            e3(tt_vector[2]+noise(),dv_vector[2]+noise())

            # Compute performances
            p1(b2.performance[0])
            p2(b2.performance[1])

    man = MAN([],[],[],behaviours,margin_nodes,performances,'MAN_test')

    ######################################################
    # Create training data and train response surface
    n_samples = 100
    excess_space = Design(-np.ones(len(margin_nodes)),np.ones(len(margin_nodes)),n_samples,'LHS').unscale()

    p_space = np.empty((n_samples,len(performances)))
    p_space[:,0] = np.apply_along_axis(man.behaviours[1].p1_model,axis=1,arr=excess_space+dv_vector) # mat + vec is automatically broadcasted
    p_space[:,1] = np.apply_along_axis(man.behaviours[1].p2_model,axis=1,arr=excess_space+dv_vector) # mat + vec is automatically broadcasted

    man.train_performance_surrogate(n_samples=100,ext_samples=(excess_space,p_space))

    n_runs = 1000
    for n in range(n_runs):
        man.forward()
        man.compute_impact()

    mean_impact = np.mean(man.impact_matrix.impacts,axis=2)

    # Check outputs
    input = np.tile(tt_vector,(len(margin_nodes),1))

    p = np.empty((len(margin_nodes),len(performances)))
    p[:,0] = np.apply_along_axis(man.behaviours[1].p1_model,axis=1,arr=input)
    p[:,1] = np.apply_along_axis(man.behaviours[1].p2_model,axis=1,arr=input)

    np.fill_diagonal(input,dv_vector)

    p_t = np.empty((len(margin_nodes),len(performances)))
    p_t[:,0] = np.apply_along_axis(man.behaviours[1].p1_model,axis=1,arr=input)
    p_t[:,1] = np.apply_along_axis(man.behaviours[1].p2_model,axis=1,arr=input)

    test_impact = (p - p_t) / p_t

    # test_impact = np.array([
    #     [ 0.42857143,  0.16666667],
    #     [ 0.42857143,  0.4       ],
    #     [-0.61538462, -0.22222222]
    #     ])

    assert np.allclose(mean_impact, test_impact, rtol=1e-1)

    ######################################################
    # Check reset functionality

    for performance in man.performances:
        assert len(performance.values) == n_runs

    for node in man.margin_nodes:
        assert len(node.values) == n_runs

    man.reset(5)

    for performance in man.performances:
        assert len(performance.values) == n_runs - 5

    for node in man.margin_nodes:
        assert len(node.values) == n_runs - 5

    ######################################################
    # Check visualization
    # man.view_perf(e_indices=[1,2],p_index=1)
    # man.impact_matrix.view(2,1)

def test_deterministic_Absorption(man_components,deterministic_specs,Absorption_test_inputs):
    """
    Tests the Absorption calculation method for deterministic specifications
    """

    # # DEBUG:
    # # Define input specs
    # centers = np.array([1.2,1.0])
    # s1 = InputSpec(centers[0],'S1',symbol='T1',inc = -1e-0,inc_type='rel')
    # s2 = InputSpec(centers[1],'S2',symbol='T2',inc = -1e-0,inc_type='rel')
    # input_specs = [s1,s2]
    # deterministic_specs = [centers,input_specs]

    # # Define behaviour models
    # class B1(Behaviour):
    #     def __call__(self,s1,s2):
    #         # Analytical behaviour models in terms of input specs
    #         tt1_model = lambda spec : (spec[0]**2) + (2*spec[0]) + (spec[1])
    #         tt2_model = lambda spec : spec[0] + 2*spec[1]
    #         tt3_model = lambda spec : spec[0] + spec[1]

    #         self.threshold = [tt1_model((s1,s2)),tt2_model((s1,s2)),tt3_model((s1,s2))]

    #         return self.threshold

    # class B2(Behaviour):
    #     def __call__(self,dv1,dv2,dv3):
    #         # Analytical test performance models in terms of decided values
    #         p1_model = lambda dv : (dv[0]**2) + (dv[1]**2) + (2*dv[2]**2)
    #         p2_model = lambda dv : dv[0] + 2*dv[1] + dv[2]

    #         self.performance = [p1_model((dv1,dv2,dv3)),p2_model((dv1,dv2,dv3))]

    #         return self.threshold

    # b1 = B1('B1')
    # b2 = B2('B1')
    # behaviours = [b1,b2,]

    # # Define performances

    # p1 = Performance('P1')
    # p2 = Performance('P1')
    # performances = [p1,p2]

    # # Define margin nodes
    # e1 = MarginNode('E1',type='must_exceed')
    # e2 = MarginNode('E2',type='must_exceed')
    # e3 = MarginNode('E3',type='must_exceed')
    # margin_nodes = [e1,e2,e3]

    # man_components = [behaviours, performances, margin_nodes]

    # # test decided values and target thresholds for checking impact matrix calculation
    # dv_vector = np.array([4.0,2.0,2.0])
    # Absorption_test_inputs = dv_vector

    ######################################################
    # Construct MAN
    dv_vector                               = Absorption_test_inputs
    behaviours, performances, margin_nodes  = man_components
    centers,input_specs                     = deterministic_specs

    # Define the MAN
    class MAN(MarginNetwork):

        def forward(self):
            
            # retrieve input specs
            s1 = self.input_specs[0]
            s2 = self.input_specs[1]

            # get behaviour
            b1 = self.behaviours[0]
            b2 = self.behaviours[1]

            # retrieve margin nodes
            e1 = self.margin_nodes[0]
            e2 = self.margin_nodes[1]
            e3 = self.margin_nodes[2]

            # get performance
            p1 = self.performances[0]
            p2 = self.performances[1]

            # Execute behaviour models
            b1(s1.value,s2.value)
            b2(dv_vector[0],dv_vector[1],dv_vector[2])

            # Compute excesses
            e1(b1.threshold[0],dv_vector[0])
            e2(b1.threshold[1],dv_vector[1])
            e3(b1.threshold[2],dv_vector[2])

            # Compute performances
            p1(b2.performance[0])
            p2(b2.performance[1])

    man = MAN([],input_specs,[],behaviours,margin_nodes,performances,'MAN_test')

    ######################################################
    # Create training data and train response surface
    b1, b2 = behaviours

    man.forward()
    man.compute_absorption()

    mean_absorption = np.mean(man.absorption_matrix.absorptions,axis=2)

    # Check outputs

    s1_limit = np.array([
        -1 + np.sqrt(1+dv_vector[0]-centers[1]**2),
        (dv_vector[1]-2*centers[1]),
        (dv_vector[2]-centers[1]),
    ])
    
    s2_limit = np.array([
        dv_vector[0]-(centers[0]**2)-(2*centers[0]),
        (dv_vector[1]-centers[0]) / 2,
        dv_vector[2]-centers[0],
    ])

    s1_limit = np.max(s1_limit)
    s2_limit = np.max(s2_limit)
    spec_limit = np.array([s1_limit,s2_limit])

    # deterioration matrix
    signs = np.array([-1,-1])
    nominal_specs = np.array([centers[0],centers[1]])
    deterioration = signs*(spec_limit - nominal_specs) / nominal_specs
    deterioration_matrix = np.tile(deterioration,(len(margin_nodes),1))

    #deterioration_matrix = [len(margin_nodes), len(input_specs)]

    # threshold matrix
    nominal_tt = np.array(b1(centers[0],centers[1]))
    nominal_tt = np.reshape(nominal_tt,(len(margin_nodes),-1))
    target_thresholds = np.tile(nominal_tt,(1,len(input_specs)))

    #target_thresholds = [len(margin_nodes), len(input_specs)]

    # Compute performances at the spec limit for each margin node
    new_tt_1 = np.array(b1(s1_limit,centers[1]))
    new_tt_2 = np.array(b1(centers[0],s2_limit))

    new_tt_1 = np.reshape(new_tt_1,(len(margin_nodes),-1))
    new_tt_2 = np.reshape(new_tt_2,(len(margin_nodes),-1))
    change_matrix = np.empty((len(margin_nodes),0))
    change_matrix = np.hstack((change_matrix,new_tt_1))
    change_matrix = np.hstack((change_matrix,new_tt_2))

    #change_matrix = [len(margin_nodes), len(input_specs)]

    test_absorption =abs(change_matrix - target_thresholds) / (target_thresholds * deterioration_matrix)
    # test_absorption = np.array([
    #     [ 1.04132231  , 0.20661157],
    #     [ 0.375       , 0.625     ],
    #     [0.54545455   , 0.45454545]
    #     ])

    assert np.allclose(mean_absorption, test_absorption, rtol=1e-1)

    ######################################################
    # Check visualization
    # man.absorption_matrix.view(0,0)
    # man.absorption_matrix.view(1,0)
    # man.absorption_matrix.view(2,0)

    # man.absorption_matrix.view(0,1)
    # man.absorption_matrix.view(1,1)
    # man.absorption_matrix.view(2,1)

def test_stochastic_Absorption(man_components,stochastic_specs,Absorption_test_inputs):
    """
    Tests the Absorption calculation method for stochastic specifications
    """
    
    # # DEBUG:
    # # Define input specs
    # centers = np.array([1.2,1.0])
    # s1 = InputSpec(centers[0],'S1',symbol='T1',inc = -1e-0,inc_type='rel')
    # s2 = InputSpec(centers[1],'S2',symbol='T2',inc = -1e-0,inc_type='rel')
    # input_specs = [s1,s2]
    # deterministic_specs = [centers,input_specs]

    # # Define behaviour models
    # class B1(Behaviour):
    #     def __call__(self,s1,s2):
    #         # Analytical behaviour models in terms of input specs
    #         tt1_model = lambda spec : (spec[0]**2) + (2*spec[0]) + (spec[1])
    #         tt2_model = lambda spec : spec[0] + 2*spec[1]
    #         tt3_model = lambda spec : spec[0] + spec[1]

    #         self.threshold = [tt1_model((s1,s2)),tt2_model((s1,s2)),tt3_model((s1,s2))]

    #         return self.threshold

    # class B2(Behaviour):
    #     def __call__(self,dv1,dv2,dv3):
    #         # Analytical test performance models in terms of decided values
    #         p1_model = lambda dv : (dv[0]**2) + (dv[1]**2) + (2*dv[2]**2)
    #         p2_model = lambda dv : dv[0] + 2*dv[1] + dv[2]

    #         self.performance = [p1_model((dv1,dv2,dv3)),p2_model((dv1,dv2,dv3))]

    #         return self.threshold

    # b1 = B1('B1')
    # b2 = B2('B1')
    # behaviours = [b1,b2,]

    # # Define performances

    # p1 = Performance('P1')
    # p2 = Performance('P1')
    # performances = [p1,p2]

    # # Define margin nodes
    # e1 = MarginNode('E1',type='must_exceed')
    # e2 = MarginNode('E2',type='must_exceed')
    # e3 = MarginNode('E3',type='must_exceed')
    # margin_nodes = [e1,e2,e3]

    # man_components = [behaviours, performances, margin_nodes]

    # # test decided values and target thresholds for checking impact matrix calculation
    # dv_vector = np.array([4.0,2.0,2.0])
    # Absorption_test_inputs = dv_vector

    ######################################################
    # Construct MAN
    dv_vector                               = Absorption_test_inputs
    behaviours, performances, margin_nodes  = man_components
    dist,centers,ranges,input_specs         = stochastic_specs

    s1,s2 = input_specs

    class MAN(MarginNetwork):
        def randomize(self):
            dist()
            s1()
            s2()

        def forward(self):

            # retrieve input specs
            s1 = self.input_specs[0]
            s2 = self.input_specs[1]

            # get behaviour
            b1 = self.behaviours[0]
            b2 = self.behaviours[1]

            # retrieve margin nodes
            e1 = self.margin_nodes[0]
            e2 = self.margin_nodes[1]
            e3 = self.margin_nodes[2]

            # get performance
            p1 = self.performances[0]
            p2 = self.performances[1]

            # Execute behaviour models
            b1(s1.value,s2.value)
            b2(dv_vector[0],dv_vector[1],dv_vector[2])

            # Compute excesses
            e1(b1.threshold[0],dv_vector[0])
            e2(b1.threshold[1],dv_vector[1])
            e3(b1.threshold[2],dv_vector[2])

            # Compute performances
            p1(b2.performance[0])
            p2(b2.performance[1])

    man = MAN([],input_specs,[],behaviours,margin_nodes,performances,'MAN_test')

    ######################################################
    # Create training data and train response surface

    b1,b2 = behaviours

    n_runs = 100
    for n in range(n_runs):
        man.randomize()
        man.forward()
        man.compute_absorption()

    mean_absoprtion = np.mean(man.absorption_matrix.absorptions,axis=2)

    # Check outputs
    
    s1_limit = np.array([
        -1 + np.sqrt(1+dv_vector[0]-centers[1]**2),
        (dv_vector[1]-2*centers[1]),
        (dv_vector[2]-centers[1]),
    ])
    
    s2_limit = np.array([
        dv_vector[0]-(centers[0]**2)-(2*centers[0]),
        (dv_vector[1]-centers[0]) / 2,
        dv_vector[2]-centers[0],
    ])

    s1_limit = np.max(s1_limit)
    s2_limit = np.max(s2_limit)
    spec_limit = np.array([s1_limit,s2_limit])

    # deterioration matrix
    signs = np.array([-1,-1])
    nominal_specs = np.array([centers[0],centers[1]])
    deterioration = signs*(spec_limit - nominal_specs) / nominal_specs
    deterioration_matrix = np.tile(deterioration,(len(margin_nodes),1))

    #deterioration_matrix = [len(margin_nodes), len(input_specs)]

    # threshold matrix
    nominal_tt = np.array(b1(centers[0],centers[1]))
    nominal_tt = np.reshape(nominal_tt,(len(margin_nodes),-1))
    target_thresholds = np.tile(nominal_tt,(1,len(input_specs)))

    #target_thresholds = [len(margin_nodes), len(input_specs)]

    # Compute performances at the spec limit for each margin node
    new_tt_1 = np.array(b1(s1_limit,centers[1]))
    new_tt_2 = np.array(b1(centers[0],s2_limit))

    new_tt_1 = np.reshape(new_tt_1,(len(margin_nodes),-1))
    new_tt_2 = np.reshape(new_tt_2,(len(margin_nodes),-1))
    change_matrix = np.empty((len(margin_nodes),0))
    change_matrix = np.hstack((change_matrix,new_tt_1))
    change_matrix = np.hstack((change_matrix,new_tt_2))

    #change_matrix = [len(margin_nodes), len(input_specs)]

    test_absorption =abs(change_matrix - target_thresholds) / (target_thresholds * deterioration_matrix)
    # test_absorption = np.array([
    #     [ 1.04132231  , 0.20661157],
    #     [ 0.375       , 0.625     ],
    #     [0.54545455   , 0.45454545]
    #     ])

    ######################################################
    # Check visualization
    # man.absorption_matrix.view_det(0)
    # man.absorption_matrix.view_det(1)

    # man.absorption_matrix.view(0,0)
    # man.absorption_matrix.view(1,0)
    # man.absorption_matrix.view(2,0)

    # man.absorption_matrix.view(0,1)
    # man.absorption_matrix.view(1,1)
    # man.absorption_matrix.view(2,1)

    assert np.allclose(mean_absoprtion, test_absorption, rtol=1e-0)
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patches
from scipy.optimize import minimize_scalar,fsolve

from dmLib import triangularFunc, fuzzySet, fuzzyRule, fuzzySystem
from dmLib import Design
from dmLib import FixedParam, DesignParam, InputSpec, Behaviour, Performance, MarginNode, MarginNetwork
from dmLib import Distribution, gaussianFunc

# define fixed parameters
i1 = FixedParam(4.17E-05    ,'I1',description='Coefficient of thermal expansion'    ,symbol='alpha' )
i2 = FixedParam(156.3E3     ,'I2',description='Youngs modulus'                      ,symbol='E'     )
i3 = FixedParam(8.19e-06    ,'I3',description='Material density'                    ,symbol='rho'   )
i4 = FixedParam(346.5       ,'I4',description='Radius of the hub'                   ,symbol='r1'    )
i5 = FixedParam(536.5       ,'I5',description='Radius of the shroud'                ,symbol='r2'    )
i6 = FixedParam(1.0         ,'I6',description='Column effective length factor'      ,symbol='K'     )
fixed_params = [i1,i2,i3,i4,i5,i6]

# define design parameters
d1 = DesignParam(130.0  ,'D1'   ,universe=(70.0,130.0)  ,description='vane length'  ,symbol='w'     )
d2 = DesignParam(20.0   ,'D2'   ,universe=(0.5,20.0)    ,description='vane height'  ,symbol='h'     )
d3 = DesignParam(85.0   ,'D1'   ,universe=(0.0,90.0)    ,description='lean angle'   ,symbol='theta' )
design_params = [d1,d2,d3]

# T1,T2 distribution
mu = np.array([370,580])
Sigma = np.array([
    [50, 25],
    [75, 100],
    ])
Requirement = gaussianFunc(mu, Sigma, 'temp')

# define input specifications
s1 = InputSpec(Requirement  ,'S1'   ,cov_index=0    ,description='nacelle temperature'      ,symbol='T1'        , change_dir = '-')
s2 = InputSpec(Requirement  ,'S2'   ,cov_index=1    ,description='gas surface temperature'  ,symbol='T2'        , change_dir = '+')
s3 = InputSpec(460.0        ,'S3'                   ,description='yield stress'             ,symbol='sigma_y'   , change_dir = '-')
input_specs = [s1,s2,s3]

# define the behaviour models

# this is the length model
class B1(Behaviour):
    def __call__(self,theta,r1,r2):
        def f(L):
            return (L**2) + 2*r1*L*np.cos(np.deg2rad(theta)) - ((r2**2) - (r1**2))
        
        def f_prime(L):
            return 2*L + 2*r1*np.cos(np.deg2rad(theta))
        
        lb = r2-r1
        ub = np.sqrt(r2**2 - r1**2)
        # length=minimize_scalar(f,bounds=(lb,ub),method='bounded')
        length=fsolve(f,lb + (ub-lb)*0.5)[0]
        self.intermediate = length

# this is the weight model
class B2(Behaviour):
    def __call__(self,rho,w,h,L):
        weight = rho*w*h*L
        self.performance = weight

# this is the axial stress model
class B3(Behaviour):
    def __call__(self,alpha,E,T1,T2,w,h,theta):
        force = (E*w*h*alpha)*(T2-T1)*np.cos(np.deg2rad(theta))
        sigma_a = (E*alpha)*(T2-T1)*np.cos(np.deg2rad(theta))
        self.decided_value = [force/1000,sigma_a]

# this is the bending stress model
class B4(Behaviour):
    def __call__(self,alpha,E,T1,T2,h,theta,L):
        sigma_m = ((3*E*h)/(2*L))*(alpha*(T2-T1)*np.sin(np.deg2rad(theta)))
        self.decided_value = sigma_m

# this is the buckling model
class B5(Behaviour):
    def __call__(self,E,K,w,h,L):
        f_buckling = ((np.pi**2)*E*w*(h**3)) / (12*((K*L)**2))
        self.threshold = f_buckling/1000

b1 = B1('B1')
b2 = B2('B2')
b3 = B3('B3')
b4 = B4('B4')
b5 = B5('B4')
behaviours = [b1,b2,b3,b4,b5]

# Define margin nodes
e1 = MarginNode('E1',type='must_not_exceed')
e2 = MarginNode('E2',type='must_not_exceed')
e3 = MarginNode('E3',type='must_not_exceed')
margin_nodes = [e1,e2,e3]

# Define performances
p1 = Performance('P1',type='more_is_better')
performances = [p1,]

# Define the MAN
class MAN(MarginNetwork):
    def forward(self):

        Requirement()

        # retrieve MAN components
        d1 = self.design_params[0] # w
        d2 = self.design_params[1] # h
        d3 = self.design_params[2] # theta

        s1 = self.input_specs[0] # T1 (stochastic)
        s2 = self.input_specs[1] # T2 (stochastic)
        s3 = self.input_specs[2] # sigma_y 

        i1 = self.fixed_params[0] # alpha
        i2 = self.fixed_params[1] # E
        i3 = self.fixed_params[2] # rho
        i4 = self.fixed_params[3] # r1
        i5 = self.fixed_params[4] # r2
        i6 = self.fixed_params[5] # K

        b1 = self.behaviours[0] # calculates length
        b2 = self.behaviours[1] # calculates weight
        b3 = self.behaviours[2] # calculates axial force and stress
        b4 = self.behaviours[3] # calculates bending stress
        b5 = self.behaviours[4] # calculates buckling load

        e1 = self.margin_nodes[0] # margin against buckling (F,F_buckling)
        e2 = self.margin_nodes[1] # margin against axial failure (sigma_a,sigma_y)
        e3 = self.margin_nodes[2] # margin against bending failure (sigma_m,sigma_y)

        p1 = self.performances[0] # weight

        # Execute behaviour models
        b1(d3.value,i4.value,i5.value)
        b2(i3.value,d1.value,d2.value,b1.intermediate)
        b3(i1.value,i2.value,s1(),s2(),d1.value,d2.value,d3.value)
        b4(i1.value,i2.value,s1(),s2(),d2.value,d3.value,b1.intermediate)
        b5(i2.value,i6.value,d1.value,d2.value,b1.intermediate)

        # Compute excesses
        e1(b3.decided_value[0],b5.threshold)
        e2(b3.decided_value[1],s3())
        e3(b4.decided_value,s3())

        # Compute performances
        p1(b2.performance)

man = MAN(design_params,input_specs,fixed_params,
    behaviours,margin_nodes,performances,'MAN_1')

# Create surrogate model for estimating threshold performance
man.train_performance_surrogate(n_samples=300,sampling_freq=20)
man.view_perf(d_indices=[0,1],p_index=0)
man.view_perf(d_indices=[0,2],p_index=0)
man.view_perf(d_indices=[1,2],p_index=0)

# Perform Monte-Carlo simulation
for n in range(10000):
    man.forward()
    man.compute_impact()

# View distribution of excess
man.margin_nodes[0].view()
man.margin_nodes[1].view()
man.margin_nodes[2].view()

# View distribution of Impact on Performance
man.impact_matrix.view(0,0)
man.impact_matrix.view(1,0)
man.impact_matrix.view(2,0)

# man.reset()
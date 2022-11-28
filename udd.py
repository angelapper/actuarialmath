"""Fractional ages

Copyright 2022, Terence Lim

MIT License
"""
import pandas as pd
from actuarialmath.fractional import Fractional
from actuarialmath.mthly import Mthly

class UDD(Mthly):
    """UDD: 1/Mthly shortcuts with uniform distribution of deaths assumption

    - m (int) : number of payments per year
    - life (Fractional) : original fractional survival and mortality functions
    """
    _help = ['alpha', 'beta', 'frame']

    def __init__(self, m: int, life: Fractional, **kwargs):
        super().__init__(m=m, life=life, **kwargs)
        self.alpha_m = self.alpha(m=m, i=self.life.interest.i)
        self.beta_m = self.beta(m=m, i=self.life.interest.i)

    @staticmethod
    def alpha(m: int, i: float) -> float:
        """1/Mthly UDD interest rate beta function value
        - m (int) : number of payments per year
        - i (float) : annual interest rate
        """
        d = i / (1 + i)
        i_m = Fractional.Interest.mthly(m=m, i=i)
        i_d = Fractional.Interest.mthly(m=m, d=d)
        return abs(i*d / ( i_m * i_d))

    @staticmethod
    def beta(m: int, i: float) -> float:
        """1/Mthly UDD interest rate alpha function value
        - m (int) : number of payments per year
        - i (float) : annual interest rate
        """
        d = i / (1 + i)
        i_m = Fractional.Interest.mthly(m=m, i=i)
        i_d = Fractional.Interest.mthly(m=m, d=d)
        return abs((i - i_m) / (i_m * i_d))

    def whole_life_insurance(self, x: int, s: int = 0, moment: int = 1, 
                             b: int = 1) -> float:
        """1/Mthly UDD Whole life insurance: A_x"""
        assert moment in [1, 2, Fractional.VARIANCE]
        if moment == Fractional.VARIANCE:
            return ((self.whole_life_insurance(x, s=s, moment=2)
                     - self.whole_life_insurance(x, s=s)**2) * b**2)
        A = self.life.whole_life_insurance(x, s=s, moment=moment)
        i = self.life.interest.i
        if moment == 2:
            i = self.interest.double_force(i)
        i_m = self.life.interest.mthly(m=self.m, i=i)        
        return A * i / i_m

    def endowment_insurance(self, x: int, s: int = 0, t: int = 1, b: int = 1, 
                            endowment: int = -1, moment: int = 1) -> float:
        """1/Mthly UDD Endowment insurance = term insurance + pure endowment"""
        assert moment in [1, 2, Fractional.VARIANCE]
        if moment == Fractional.VARIANCE:
            return (self.endowment_insurance(x, s=s, t=t, endowment=endowment, 
                                             b=b, moment=2)
                     - self.endowment_insurance(x, s=s, t=t, endowment=endowment,
                                                b=b)**2)
        E = self.E_x(x, s=s, t=t, moment=moment)
        A = self.term_insurance(x, s=s, t=t, b=b, moment=moment)
        return A  + E * (b if endowment < 0 else endowment)**moment


    def term_insurance(self, x: int, s: int = 0, t: int = 1, b: int = 1, 
                       moment: int = 1) -> float:
        """1/Mthly UDD Term insurance: A_x:t"""
        assert moment in [1, 2, Fractional.VARIANCE]
        if moment == Fractional.VARIANCE:
            return (self.term_insurance(x, s=s, t=t, b=b, moment=2)
                     - self.term_insurance(x, s=s, t=t, b=b)**2)
        A = self.life.term_insurance(x, s=s, t=t, b=b, moment=moment)
        i = self.life.interest.i
        if moment == 2:
            i = self.interest.double_force(i)
        i_m = self.life.interest.mthly(m=self.m, i=i)        
        return A * (i / i_m)

    def whole_life_annuity(self, x: int, s: int = 0, b: int = 1, 
                           variance: bool = False) -> float:
        """1/Mthly UDD Whole life annuity: a_x"""

        if variance:  # short cut for variance of whole life
            A1 = self.whole_life_insurance(x, s=s, moment=1)
            A2 = self.whole_life_insurance(x, s=s, moment=2)
            return (b**2 * (A2 - A1**2) / self.d**2)
        a = self.life.whole_life_annuity(x, s=s)
        return b * (a * self.alpha_m - self.beta_m)
            
    def temporary_annuity(self, x: int, s: int = 0, t: int = Fractional.WHOLE, 
                          b: int = 1, variance: bool = False) -> float:
        """1/Mthly UDD Temporary life annuity: a_x:t"""

        if variance:  # short cut for variance of temporary life annuity
            A1 = self.temporary_insurance(x, s=s, t=t)
            A2 = self.temporary_insurance(x, s=s, t=t, moment=2)
            return (b**2 * (A2 - A1**2) / self.d**2)

        # difference of whole life on (x) and deferred whole life on (x+t)
        if t < 0:
            return self.whole_life_annuity(x, b=b, s=s)  # UDD
        a = self.life.temporary_annuity(x, s=s, t=t)
        return b * (a*self.alpha_m - self.beta_m*(1 - self.E_x(x, s=s, t=t)))

    def deferred_annuity(self, x: int, s: int = 0, u: int = 0, 
                         t: int = Fractional.WHOLE, b: int = 1,
                         variance: bool = False) -> float:
        """1/Mthly UDD Deferred life annuity n|t_a_x =  n+t_a_x - n_a_x"""
        if self.max_term(x+s, n) < n:
            return 0.
        if variance:  # short cut for variance of temporary life annuity
            A1 = self.endowment_insurance(x, s=s, t=t)
            A2 = self.endowment_insurance(x, s=s, t=t, moment=2)
            return (b**2 * (A2 - A1**2) / self.d**2)

        a = self.life.deferred_annuity(x, s=s, u=u, t=t)
        return (a * self.alpha_m - self.beta_m * self.E_x(x, s=s, t=u)) * b

    @staticmethod
    def frame(i: float = 0.05):
        """Display 1/mthly UDD interest function values
        - i (float) : annual interest rate
        """
        interest = Fractional.Interest(i=i)
        out = pd.DataFrame(columns=["i(m)", "d(m)", "i/i(m)", "d/d(m)", 
                                    "alpha(m)", "beta(m)"],
                           index=[1, 2, 4, 12, 0], 
                           dtype=float)
        for m in out.index:
            i_m = Fractional.Interest.mthly(m=m, i=interest.i)
            d_m = Fractional.Interest.mthly(m=m, d=interest.d)
            out.loc[m] = [i_m, d_m, interest.i/i_m, interest.d/d_m, 
                          UDD.alpha(m=m, i=interest.i), 
                          UDD.beta(m=m, i=interest.i)]
        return out.round(5)


if __name__ == "__main__":
    from actuarialmath.sult import SULT
    from actuarialmath.recursion import Recursion
    print(UDD.help())
    
    print("SOA Question 7.9:  (A) 38100")
    sult = SULT(udd=True)
    x, n, t = 45, 20, 10
    a = UDD(m=12, life=sult).temporary_annuity(x+10, t=n-10)
    print(a)
    A = UDD(m=0, life=sult).endowment_insurance(x+10, t=n-10)
    print(A)
    print(A*100000 - a*12*253)
    policy = sult.Policy(premium=253*12, endowment=100000, benefit=100000)
    print(sult.gross_future_loss(A=A, a=a, policy=policy))
    print()

    print("SOA Question 6.49:  (C) 86")
    sult = SULT(udd=True)
    a = UDD(m=12, life=sult).temporary_annuity(40, t=20)
    A = sult.whole_life_insurance(40, discrete=False)
    P = sult.gross_premium(a=a, A=A, benefit=100000, initial_policy=200,
                           renewal_premium=0.04, initial_premium=0.04)
    print(P/12)
    print()

    print("SOA Question 6.38:  (B) 11.3")
    x, n = 0, 10
    life = Recursion(interest=dict(i=0.05))
    life.set_A(0.192, x=x, t=n, endowment=1, discrete=False)
    life.set_E(0.172, x=x, t=n)
    a = life.temporary_annuity(x, t=n, discrete=False)
    print(a)

    def fun(a):      # solve for discrete annuity, given continuous
        life = Recursion(interest=dict(i=0.05))
        life.set_a(a, x=x, t=n).set_E(0.172, x=x, t=n)
        return UDD(m=0, life=life).temporary_annuity(x, t=n)
    a = life.solve(fun, target=a, guess=a)  # discrete annuity
    P = life.gross_premium(a=a, A=0.192, benefit=1000)
    print(P)
    print()

    print("SOA Question 6.32:  (C) 550")
    x = 0
    life = Recursion(interest=dict(i=0.05)).set_a(9.19, x=x)
    benefits = UDD(m=0, life=life).whole_life_insurance(x)
    payments = UDD(m=12, life=life).whole_life_annuity(x)
    print(benefits, payments)
    print(life.gross_premium(a=payments, A=benefits, benefit=100000)/12)
    print()

    print("SOA Question 6.22:  (C) 102")
    life = SULT(udd=True)
    a = UDD(m=12, life=life).temporary_annuity(45, t=20)
    A = UDD(m=0, life=life).whole_life_insurance(45)
    print(life.gross_premium(A=A, a=a, benefit=100000)/12)
    print()

    print("Interest Functiona at i=0.05")
    print("----------------------------")
    print(UDD.frame(i=0.05))
    print()

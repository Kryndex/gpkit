"Implements heatmapped equations to highlight sensitivities."
import numpy as np
from gpkit.nomials import MonomialEquality
from gpkit.small_scripts import nomial_latex_helper


BLUE = np.array([16, 131, 246])/255.0
RED = np.array([211, 24, 16])/255.0
GRAY = 0.7*np.ones(3)


def colorfn_gen(scale, power=0.66):
    "Generates color gradient of a given power law."
    scale = float(scale)

    def colorfn(senss):
        "Turns sensitivities into color along a power-law gradient."
        if senss < 0:
            senss = -senss
            color = BLUE
        else:
            color = RED
        blended_color = GRAY + (color-GRAY)*(senss/scale)**power
        return "[rgb]{%.2f,%.2f,%.2f}" % tuple(blended_color)
    return colorfn

# pylint: disable=too-many-locals
def signomial_print(sig, sol, colorfn, paintby="constants", idx=None):
    "For pretty printing with Sympy"
    mstrs = []
    for c, exp in zip(sig.cs, sig.exps):
        pos_vars, neg_vars = [], []
        for var, x in exp.items():
            varlatex = var.latex()
            if paintby == "constants":
                senss = (sol["sensitivities"]["constants"][var]
                         if var in sol["sensitivities"]["constants"]
                         else 0.0)
                colorstr = colorfn(senss)
                varlatex = "\\textcolor%s{%s}" % (colorstr, varlatex)
            if x > 0:
                pos_vars.append((varlatex, x))
            elif x < 0:
                neg_vars.append((varlatex, x))

        mstrs.append(nomial_latex_helper(c, pos_vars, neg_vars))

    if paintby == "monomials":
        mstrs_ = []
        for mstr in mstrs:
            senss = sol["sensitivities"]["monomials"][idx]
            idx += 1
            colorstr = colorfn(senss)
            mstrs_.append("\\textcolor%s{%s}" % (colorstr, mstr))
        return " + ".join(sorted(mstrs_)), idx
    else:
        return " + ".join(sorted(mstrs))


class SensitivityMap(object):
    """Latex representations of a model heatmapped by its latest sensitivities

    Arguments
    ---------
    model : Model
        The Model object that the Map will be based on

    paintby : string
        The unit of colouring. Must be one of "constants", "monomials", or
        "posynomials".

    Usage
    -----
    from IPython.display import display
    for key in m.solution["sensitivities"]:
        print key
        display(SensitivityMap(m, paintby=key))
    """

    def __init__(self, model, paintby="constants"):
        self.model = model
        self.costlatex = model.cost.latex()
        self.paintby = paintby

    @property
    def solution(self):
        "Gets solution, indexing into a sweep if necessary."
        if not hasattr(self.model, "solution"):
            self.model.solve()
        if len(self.model.solution) > 1:
            return self.model.solution.atindex(0)  # TODO: support sweeps
        else:
            return self.model.solution

    def _repr_latex_(self):
        "iPython LaTeX representation."
        return "$$\\require{color}\n"+self.latex+"\n$$"

    @property
    def latex(self, paintby=None):
        "LaTeX representation."
        if not paintby:
            paintby = self.paintby
        return "\n".join(["\\color[gray]{%.2f}" % GRAY[0],
                          "\\begin{array}{ll}",
                          "\\text{}",
                          "\\text{minimize}",
                          "    & %s \\\\" % self.costlatex,
                          "\\text{subject to}"] +
                         self.constraint_latex_list(paintby) +
                         ["\\end{array}"])

    # pylint: disable=too-many-locals
    def constraint_latex_list(self, paintby):
        "Generates LaTeX for constraints."
        constraint_latex_list = []
        sol = self.solution
        if self.paintby == "constants":
            senss = abs(np.array(sol["sensitivities"]["constants"].values()))
        else:
            idx = len(self.model.cost.exps) if paintby == "monomials" else 1
            senss = sol["sensitivities"][paintby][idx:]
        colorfn = colorfn_gen(max(senss))

        for i, constr in enumerate(self.model):
            if self.paintby == "constants":
                left = signomial_print(constr.left, sol, colorfn, paintby)
                right = signomial_print(constr.right, sol, colorfn, paintby)
                constr_tex = ("    & %s \\\\" %
                              (left + constr.latex_opers[constr.oper] + right))
            else:
                if isinstance(constr, MonomialEquality):
                    constrs = [constr.leq, constr.geq]
                else:
                    constrs = [constr]
                constr_texs = []
                for constr in constrs:
                    # TODO: not the right way to check if Signomial
                    rhs = "\\leq 0" if constr.any_nonpositive_cs else "\\leq 1"
                    if self.paintby == "monomials":
                        tex, idx = signomial_print(constr, sol, colorfn,
                                                   paintby, idx)
                    elif self.paintby == "posynomials":
                        color = colorfn(senss[i])
                        tex = signomial_print(constr, None, None, paintby)
                        tex = "\\textcolor%s{%s}" % (color, tex)
                    constr_texs.append("    & %s %s\\\\" % (tex, rhs))
                constr_tex = "\n".join(constr_texs)
            constraint_latex_list.append(constr_tex)
        return constraint_latex_list

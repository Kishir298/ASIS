"""
Calculator engine: operation dispatch, verification, resource limits.

Single entry point owned by A.S.I.S. All computation is local
(SymPy + standard library); the engine never touches the network and
never downloads anything. Results are verified independently where a
cheap independent check exists, and the verification record says
exactly what was checked.
"""

from __future__ import annotations

import math

from asis.calculator import errors
from asis.calculator.formatting import format_exact, format_number
from asis.calculator.models import CalculatorResult
from asis.calculator.validation import check_expression

OPERATIONS = (
    "calculate",
    "simplify",
    "expand",
    "factor",
    "collect",
    "substitute",
    "solve",
    "solve_system",
    "inequality",
    "differentiate",
    "partial",
    "gradient",
    "integrate",
    "limit",
    "series",
    "ode",
    "trig",
    "complex",
    "matrix",
    "vector",
    "geometry",
    "triangle",
    "statistics",
    "probability",
    "number_theory",
    "convert_units",
    "constant",
    "physics",
    "engineering",
    "finance",
)

DEFAULT_PRECISION = 10


class CalculatorEngine:
    """Deterministic local mathematics entry point."""

    def __init__(
        self,
        *,
        max_expression_chars: int = 2_000,
        max_matrix_size: int = 10,
        precision: int = DEFAULT_PRECISION,
        angle_mode: str = "radians",
    ) -> None:
        self._max_chars = max(1, int(max_expression_chars))
        self._max_matrix = max(1, int(max_matrix_size))
        self._precision = max(0, int(precision))
        if angle_mode not in ("radians", "degrees", "gradians"):
            raise errors.invalid_expression(f"unknown angle mode '{angle_mode}'")
        self._angle_mode = angle_mode

    @property
    def angle_mode(self) -> str:
        return self._angle_mode

    def _expression(self, text: str) -> str:
        return check_expression(text, max_chars=self._max_chars)

    def _dataset(self, raw) -> str:
        # Datasets never reach the symbolic parser (plain float split),
        # so they validate under a larger linear-time budget.
        from asis.calculator.validation import check_expression as check

        text = raw if isinstance(raw, str) else str(raw or "")
        return check(text, max_chars=100_000)

    def _result(
        self,
        operation: str,
        expression: str,
        *,
        exact=None,
        numeric=None,
        units=None,
        variables=(),
        steps=(),
        verification=None,
        warnings=(),
    ) -> CalculatorResult:
        exact_text = format_exact(exact) if exact is not None else None
        number = None
        if numeric is not None:
            try:
                number = format_number(float(numeric), precision=self._precision)
            except (TypeError, ValueError):
                number = None
        return CalculatorResult(
            operation=operation,
            expression=expression,
            exact_result=exact_text,
            numeric_result=number,
            units=units,
            variables=tuple(variables),
            steps=tuple(steps),
            verification=verification,
            warnings=tuple(warnings),
        )

    # -- dispatch ---------------------------------------------------------
    def calculate(self, operation: str, params: dict | None = None) -> CalculatorResult:
        """Run one calculator operation over validated string params."""
        name = (operation or "").strip().lower()
        if name not in OPERATIONS:
            raise errors.invalid_expression(f"unknown operation '{name}'")
        args = dict(params or {})
        handler = getattr(self, f"_op_{name}")
        return handler(args)

    # -- arithmetic / scientific -------------------------------------------
    def _op_calculate(self, args: dict) -> CalculatorResult:
        from asis.calculator.evaluator import evaluate

        expression = self._expression(args.get("expression", ""))
        angle = str(args.get("angle_mode", self._angle_mode))
        exact, numeric = evaluate(expression, angle_mode=angle)
        verification = self._verify_numeric(expression, numeric, angle)
        return self._result(
            "calculate",
            expression,
            exact=exact,
            numeric=numeric,
            verification=verification,
        )

    def _verify_numeric(self, expression: str, numeric, angle: str) -> dict | None:
        """Independent re-evaluation via code generation (separate path).

        The already-parsed SymPy object (never the raw string) is compiled
        through ``lambdify`` against the plain ``math`` module — a different
        evaluation route from the symbolic simplifier, with no eval/exec
        of user input anywhere in the package.
        """
        if numeric is None:
            return None
        try:
            import sympy

            from asis.calculator.parser import parse

            expr = parse(expression)
            if expr.free_symbols:
                return None
            value = float(sympy.lambdify((), expr, "math")())
            if not math.isfinite(value):
                return {"method": "independent float re-evaluation", "match": None}
            match = math.isclose(value, float(numeric), rel_tol=1e-9, abs_tol=1e-12)
            return {"method": "independent float re-evaluation", "match": bool(match)}
        except Exception:
            return {"method": "independent float re-evaluation", "match": None}

    def _op_trig(self, args: dict) -> CalculatorResult:
        from asis.calculator.evaluator import trig

        name = str(args.get("function", "")).strip().lower()
        raw_args = args.get("arguments", "")
        if isinstance(raw_args, str):
            items = [part.strip() for part in raw_args.split(";") if part.strip()]
        else:
            items = [str(item) for item in (raw_args or [])]
        for item in items:
            self._expression(item)
        angle = str(args.get("angle_mode", self._angle_mode))
        exact, numeric = trig(name, items, angle_mode=angle)
        return self._result(
            "trig",
            f"{name}({', '.join(items)})",
            exact=exact,
            numeric=numeric,
        )

    def _op_complex(self, args: dict) -> CalculatorResult:
        from asis.calculator.evaluator import complex_op

        name = str(args.get("function", "")).strip().lower()
        raw_args = args.get("arguments", "")
        if isinstance(raw_args, str):
            items = [part.strip() for part in raw_args.split(";") if part.strip()]
        else:
            items = [str(item) for item in (raw_args or [])]
        for item in items:
            self._expression(item)
        exact, numeric = complex_op(name, items)
        return self._result(
            "complex",
            f"{name}({', '.join(items)})",
            exact=exact,
            numeric=numeric,
        )

    def _op_constant(self, args: dict) -> CalculatorResult:
        from asis.calculator.constants import constant_value
        from asis.calculator.evaluator import evaluate

        name = str(args.get("name", "")).strip()
        if not name:
            raise errors.invalid_expression("constant needs a name")
        value_expr, unit, description = constant_value(name)
        exact, numeric = evaluate(value_expr)
        return self._result(
            "constant",
            name,
            exact=exact,
            numeric=numeric,
            units=unit,
            steps=(description,),
        )

    # -- symbolic -----------------------------------------------------------
    def _op_simplify(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        result = symbolic.simplify_expr(expression)
        return self._result("simplify", expression, exact=result)

    def _op_expand(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        return self._result(
            "expand", expression, exact=symbolic.expand_expr(expression)
        )

    def _op_factor(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        factored = symbolic.factor_expr(expression)
        verification = self._verify_factor(expression, factored)
        return self._result(
            "factor", expression, exact=factored, verification=verification
        )

    def _verify_factor(self, expression: str, factored: str) -> dict | None:
        try:
            from asis.calculator.parser import parse

            same = bool(
                (
                    parse(f"({expression}) - ({factored})").simplify()
                    if hasattr(parse(expression), "simplify")
                    else None
                )
                == 0
            )
        except Exception:
            return {"method": "expand-and-compare", "match": None}
        try:
            import sympy

            same = sympy.simplify(parse(expression) - parse(factored)) == 0
            return {"method": "expand-and-compare", "match": bool(same)}
        except Exception:
            return {"method": "expand-and-compare", "match": None}

    def _op_collect(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        variable = str(args.get("variable", "")).strip()
        if not variable:
            raise errors.invalid_expression("collect needs a variable")
        return self._result(
            "collect",
            expression,
            exact=symbolic.collect_expr(expression, variable),
            variables=(variable,),
        )

    def _op_substitute(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        variable = str(args.get("variable", "")).strip()
        value = self._expression(args.get("value", ""))
        if not variable:
            raise errors.invalid_expression("substitute needs a variable")
        return self._result(
            "substitute",
            expression,
            exact=symbolic.substitute(expression, variable, value),
            variables=(variable,),
        )

    def _op_solve(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        equation = self._expression(args.get("equation", ""))
        variable = str(args.get("variable", "x")).strip() or "x"
        outcome = symbolic.solve_equation(equation, variable)
        verification = self._verify_solutions(equation, variable, outcome)
        if outcome["status"] == "infinite":
            return self._result(
                "solve",
                equation,
                exact="infinitely many solutions",
                variables=(variable,),
                verification=verification,
                warnings=("identity equation: every value solves it",),
            )
        solutions = outcome["solutions"]
        numeric = self._solution_numeric(solutions)
        return self._result(
            "solve",
            equation,
            exact=", ".join(solutions),
            numeric=numeric,
            variables=(variable,),
            steps=tuple(f"{variable} = {item}" for item in solutions),
            verification=verification,
        )

    def _solution_numeric(self, solutions: list) -> float | None:
        if len(solutions) != 1:
            return None
        try:
            from asis.calculator.parser import parse_number

            return parse_number(solutions[0])
        except errors.CalculatorError:
            return None

    def _verify_solutions(
        self, equation: str, variable: str, outcome: dict
    ) -> dict | None:
        """Substitute each solution back into the equation independently."""
        if outcome.get("status") != "exact":
            return None
        try:
            from asis.calculator.parser import parse

            left_text, right_text = equation.split("=", 1)
            left, right = parse(left_text.strip()), parse(right_text.strip())
            import sympy

            checked = []
            for item in outcome["solutions"]:
                value = parse(item)
                residual = complex(
                    sympy.N(left.subs(variable, value) - right.subs(variable, value))
                )
                checked.append(abs(residual) < 1e-9)
            return {"method": "back-substitution", "match": bool(all(checked))}
        except Exception:
            return {"method": "back-substitution", "match": None}

    def _op_solve_system(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        raw_equations = args.get("equations", "")
        raw_variables = args.get("variables", "")
        equations = self._split_list(raw_equations, "equations")
        variables = self._split_list(raw_variables, "variables")
        equations = [self._expression(item) for item in equations]
        outcome = symbolic.solve_system(equations, variables)
        if outcome["status"] == "infinite":
            return self._result(
                "solve_system",
                "; ".join(equations),
                exact="infinitely many solutions",
                variables=tuple(variables),
            )
        steps = tuple(
            ", ".join(f"{key} = {value}" for key, value in entry.items())
            for entry in outcome["solutions"]
        )
        return self._result(
            "solve_system",
            "; ".join(equations),
            exact="; ".join(steps),
            variables=tuple(variables),
            steps=steps,
        )

    @staticmethod
    def _split_list(raw, name: str) -> list[str]:
        if isinstance(raw, str):
            items = [part.strip() for part in raw.split(";") if part.strip()]
        else:
            items = [str(item).strip() for item in (raw or []) if str(item).strip()]
        if not items:
            raise errors.invalid_expression(f"{name} must not be empty")
        return items

    def _op_inequality(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        variable = str(args.get("variable", "x")).strip() or "x"
        outcome = symbolic.solve_inequality(expression, variable)
        if outcome["status"] == "infinite":
            return self._result(
                "inequality",
                expression,
                exact="(-oo, oo)",
                variables=(variable,),
            )
        return self._result(
            "inequality",
            expression,
            exact=outcome["solution"],
            variables=(variable,),
        )

    def _op_differentiate(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        variable = str(args.get("variable", "x")).strip() or "x"
        try:
            order = int(str(args.get("order", "1")))
        except ValueError as exc:
            raise errors.invalid_expression("order must be an integer") from exc
        result = symbolic.differentiate(expression, variable, order)
        verification = self._verify_derivative(expression, variable, result)
        return self._result(
            "differentiate",
            expression,
            exact=result,
            variables=(variable,),
            verification=verification,
        )

    def _verify_derivative(
        self, expression: str, variable: str, result: str
    ) -> dict | None:
        """Compare the symbolic derivative against finite differences."""
        try:
            import sympy

            from asis.calculator.parser import parse

            func = sympy.lambdify(variable, parse(expression), "math")
            derived = sympy.lambdify(variable, parse(result), "math")
            points = (0.5, 1.5, 2.5)
            matches = []
            for point in points:
                try:
                    expected = (func(point + 1e-6) - func(point - 1e-6)) / 2e-6
                    matches.append(
                        math.isclose(
                            float(derived(point)), float(expected), rel_tol=1e-4
                        )
                    )
                except Exception:
                    return {"method": "finite-difference", "match": None}
            return {"method": "finite-difference", "match": bool(all(matches))}
        except Exception:
            return {"method": "finite-difference", "match": None}

    def _op_partial(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        variables = self._split_list(args.get("variables", ""), "variables")
        parts = symbolic.partial_derivatives(expression, variables)
        steps = tuple(f"d/d{name} = {value}" for name, value in parts.items())
        return self._result(
            "partial",
            expression,
            exact="; ".join(steps),
            variables=tuple(variables),
            steps=steps,
        )

    def _op_gradient(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        variables = self._split_list(args.get("variables", ""), "variables")
        values = symbolic.gradient(expression, variables)
        return self._result(
            "gradient",
            expression,
            exact=f"[{', '.join(values)}]",
            variables=tuple(variables),
        )

    def _op_integrate(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        variable = str(args.get("variable", "x")).strip() or "x"
        lower = args.get("lower")
        upper = args.get("upper")
        lower_text = self._expression(str(lower)) if lower not in (None, "") else None
        upper_text = self._expression(str(upper)) if upper not in (None, "") else None
        result = symbolic.integrate(expression, variable, lower_text, upper_text)
        verification = None
        if lower_text is not None:
            verification = self._verify_definite_integral(
                expression, variable, lower_text, upper_text, result
            )
        numeric = self._solution_numeric([result]) if lower_text else None
        return self._result(
            "integrate",
            expression,
            exact=result,
            numeric=numeric,
            variables=(variable,),
            verification=verification,
        )

    def _verify_definite_integral(
        self,
        expression: str,
        variable: str,
        lower: str,
        upper: str,
        result: str,
    ) -> dict | None:
        """Compare against Simpson-rule quadrature independently."""
        try:
            import sympy

            from asis.calculator.parser import parse, parse_number

            func = sympy.lambdify(variable, parse(expression), "math")
            low, high = float(parse_number(lower)), float(parse_number(upper))
            steps = 2000
            width = (high - low) / steps
            total = float(func(low)) + float(func(high))
            for index in range(1, steps):
                weight = 4 if index % 2 else 2
                total += weight * float(func(low + index * width))
            quadrature = total * width / 3
            expected = float(parse_number(result))
            return {
                "method": "simpson-quadrature",
                "match": bool(math.isclose(quadrature, expected, rel_tol=1e-4)),
            }
        except Exception:
            return {"method": "simpson-quadrature", "match": None}

    def _op_limit(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        variable = str(args.get("variable", "x")).strip() or "x"
        point = self._expression(args.get("point", "0"))
        direction = str(args.get("direction", "both")).strip() or "both"
        result = symbolic.limit_expr(expression, variable, point, direction)
        numeric = self._solution_numeric([result])
        return self._result(
            "limit",
            expression,
            exact=result,
            numeric=numeric,
            variables=(variable,),
        )

    def _op_series(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        expression = self._expression(args.get("expression", ""))
        variable = str(args.get("variable", "x")).strip() or "x"
        point = self._expression(args.get("point", "0"))
        try:
            order = int(str(args.get("order", "6")))
        except ValueError as exc:
            raise errors.invalid_expression("order must be an integer") from exc
        return self._result(
            "series",
            expression,
            exact=symbolic.series(expression, variable, point, order),
            variables=(variable,),
        )

    def _op_ode(self, args: dict) -> CalculatorResult:
        from asis.calculator import symbolic

        equation = self._expression(args.get("equation", ""))
        function = str(args.get("function", "f")).strip() or "f"
        variable = str(args.get("variable", "x")).strip() or "x"
        outcome = symbolic.solve_ode(equation, function, variable)
        return self._result(
            "ode",
            equation,
            exact="; ".join(outcome["solutions"]),
            variables=(variable,),
        )

    # -- linear algebra -------------------------------------------------------
    def _op_matrix(self, args: dict) -> CalculatorResult:
        from asis.calculator import linalg

        name = str(args.get("detail", args.get("operation", ""))).strip().lower()
        raw = args.get("matrices", "")
        if isinstance(raw, str):
            items = [part.strip() for part in raw.split("||") if part.strip()]
        else:
            items = [str(item) for item in (raw or [])]
        for item in items:
            self._expression(item)
        outcome = linalg.matrix_op(name, items, max_size=self._max_matrix)
        verification = None
        if name == "inverse" and items:
            verification = self._verify_inverse(items[0], outcome.get("result", ""))
        numeric = outcome.get("numeric")
        return self._result(
            "matrix",
            " || ".join(items),
            exact=outcome.get("result"),
            numeric=numeric,
            verification=verification,
        )

    def _verify_inverse(self, original: str, inverted: str) -> dict | None:
        """Check A·A⁻¹ = I independently."""
        try:
            import sympy

            from asis.calculator import linalg

            left = linalg.parse_matrix(original, max_size=self._max_matrix)
            right = linalg.parse_matrix(inverted, max_size=self._max_matrix)
            product = left * right
            identity = sympy.eye(left.rows)
            match = bool(sympy.simplify(product - identity).is_zero_matrix)
            return {"method": "A-multiply-inverse-equals-I", "match": match}
        except Exception:
            return {"method": "A-multiply-inverse-equals-I", "match": None}

    def _op_vector(self, args: dict) -> CalculatorResult:
        from asis.calculator import linalg

        name = str(args.get("detail", args.get("operation", ""))).strip().lower()
        raw = args.get("vectors", "")
        if isinstance(raw, str):
            items = [part.strip() for part in raw.split("||") if part.strip()]
        else:
            items = [str(item) for item in (raw or [])]
        for item in items:
            self._expression(item)
        outcome = linalg.vector_op(name, items, max_size=self._max_matrix)
        return self._result(
            "vector",
            " || ".join(items),
            exact=outcome.get("result"),
            numeric=outcome.get("numeric"),
        )

    # -- geometry ---------------------------------------------------------------
    def _op_geometry(self, args: dict) -> CalculatorResult:
        from asis.calculator import geometry

        shape = str(args.get("shape", "")).strip()
        if not shape:
            raise errors.invalid_expression("geometry needs a shape")
        params = {
            str(key): str(value)
            for key, value in dict(args.get("params", {}) or {}).items()
        }
        for value in params.values():
            self._expression(value)
        outcome = geometry.geometry(shape, params)
        exact = ", ".join(
            f"{key} = {value}" for key, value in outcome.items() if key != "shape"
        )
        return self._result("geometry", shape, exact=exact)

    def _op_triangle(self, args: dict) -> CalculatorResult:
        from asis.calculator import geometry

        params = {
            str(key): str(value)
            for key, value in dict(args.get("params", {}) or {}).items()
        }
        for value in params.values():
            self._expression(value)
        outcome = geometry.triangle_solve(params)
        steps = tuple(
            f"solution {index + 1}: "
            + ", ".join(f"{key} = {round(value, 6)}" for key, value in entry.items())
            for index, entry in enumerate(outcome["solutions"])
        )
        warnings = (
            ("ambiguous SSA case: multiple valid solutions",)
            if outcome.get("ambiguous")
            else ()
        )
        return self._result(
            "triangle",
            ", ".join(f"{k}={v}" for k, v in params.items()),
            exact=" | ".join(steps),
            steps=steps,
            warnings=warnings,
        )

    # -- statistics / probability / number theory ----------------------------------
    def _op_statistics(self, args: dict) -> CalculatorResult:
        from asis.calculator import stats

        name = str(args.get("function", "")).strip().lower()
        data = self._dataset(args.get("data", ""))
        sample = str(args.get("sample", "true")).strip().lower() not in (
            "false",
            "0",
            "no",
        )
        if name == "describe":
            outcome = stats.describe(data, sample=sample)
            exact = ", ".join(f"{key} = {value}" for key, value in outcome.items())
            return self._result("statistics", data, exact=exact)
        if name == "weighted_mean":
            weights = self._dataset(args.get("weights", ""))
            value = stats.weighted_mean(data, weights)
            return self._result("statistics", data, exact=str(value), numeric=value)
        if name == "percentile":
            percent = self._expression(args.get("percent", ""))
            value = stats.percentile(data, percent)
            return self._result("statistics", data, exact=str(value), numeric=value)
        if name == "covariance":
            other = self._dataset(args.get("other", ""))
            value = stats.covariance(data, other, sample=sample)
            return self._result("statistics", data, exact=str(value), numeric=value)
        if name == "correlation":
            other = self._dataset(args.get("other", ""))
            value = stats.correlation(data, other)
            return self._result("statistics", data, exact=str(value), numeric=value)
        raise errors.invalid_expression(f"unknown statistics function '{name}'")

    def _op_probability(self, args: dict) -> CalculatorResult:
        from asis.calculator import stats

        name = str(args.get("function", "")).strip().lower()

        def get(key):
            return self._expression(args.get(key, ""))

        if name == "factorial":
            value = stats.factorial_of(get("n"))
            return self._result(
                "probability", get("n"), exact=str(value), numeric=float(value)
            )
        if name == "permutations":
            value = stats.permutations(get("n"), get("r"))
            return self._result(
                "probability",
                f"n={get('n')}, r={get('r')}",
                exact=str(value),
                numeric=float(value),
            )
        if name == "combinations":
            value = stats.combinations(get("n"), get("r"))
            return self._result(
                "probability",
                f"n={get('n')}, r={get('r')}",
                exact=str(value),
                numeric=float(value),
            )
        if name == "binomial":
            value = stats.binomial_probability(
                get("trials"), get("successes"), get("p")
            )
            return self._result(
                "probability", "binomial", exact=str(value), numeric=value
            )
        if name == "bayes":
            value = stats.bayes(get("prior"), get("likelihood"), get("evidence"))
            return self._result("probability", "bayes", exact=str(value), numeric=value)
        if name == "expected_value":
            value = stats.expected_value(
                self._dataset(args.get("values", "")),
                self._dataset(args.get("probs", "")),
            )
            return self._result(
                "probability", "expected value", exact=str(value), numeric=value
            )
        raise errors.invalid_expression(f"unknown probability function '{name}'")

    def _op_number_theory(self, args: dict) -> CalculatorResult:
        from asis.calculator import stats

        name = str(args.get("function", "")).strip().lower()

        def get(key):
            return self._expression(args.get(key, ""))

        if name == "is_prime":
            value = stats.is_prime(get("n"))
            return self._result("number_theory", get("n"), exact=str(value))
        if name == "factor":
            factors = stats.prime_factors(get("n"))
            return self._result(
                "number_theory",
                get("n"),
                exact=" * ".join(str(item) for item in factors),
                steps=(f"factors: {factors}",),
            )
        if name == "gcd":
            values = self._split_list(get("values"), "values")
            result = stats.gcd_of(*values)
            return self._result(
                "number_theory",
                ", ".join(values),
                exact=str(result),
                numeric=float(result),
            )
        if name == "lcm":
            values = self._split_list(get("values"), "values")
            result = stats.lcm_of(*values)
            return self._result(
                "number_theory",
                ", ".join(values),
                exact=str(result),
                numeric=float(result),
            )
        if name == "mod_pow":
            result = stats.mod_pow(get("base"), get("exponent"), get("modulus"))
            return self._result(
                "number_theory",
                "modular exponentiation",
                exact=str(result),
                numeric=float(result),
            )
        if name == "mod_inverse":
            result = stats.mod_inverse(get("a"), get("modulus"))
            return self._result(
                "number_theory",
                "modular inverse",
                exact=str(result),
                numeric=float(result),
            )
        if name == "fibonacci":
            result = stats.fibonacci(get("n"))
            return self._result("number_theory", f"fib({get('n')})", exact=str(result))
        if name == "divisors":
            found = stats.divisors(get("n"))
            return self._result(
                "number_theory",
                get("n"),
                exact=", ".join(str(item) for item in found),
            )
        raise errors.invalid_expression(f"unknown number theory function '{name}'")

    # -- units / applied -----------------------------------------------------------
    def _op_convert_units(self, args: dict) -> CalculatorResult:
        from asis.calculator import units

        value = self._expression(args.get("value", ""))
        source = str(args.get("from", "")).strip()
        target = str(args.get("to", "")).strip()
        if not source or not target:
            raise errors.invalid_expression("convert_units needs value, from, to")
        outcome = units.convert(value, source, target)
        verification = self._verify_round_trip(
            outcome["result"], outcome["to"], value, outcome["from"]
        )
        return self._result(
            "convert_units",
            f"{value} {source} to {target}",
            exact=str(outcome["result"]),
            numeric=outcome["result"],
            units=target,
            verification=verification,
        )

    def _verify_round_trip(
        self, value, unit, original_text: str, original_unit: str
    ) -> dict | None:
        """Convert back and compare with the original value."""
        try:
            from asis.calculator import units
            from asis.calculator.parser import parse_number

            back = units.convert(str(value), unit, original_unit)["result"]
            expected = parse_number(original_text)
            return {
                "method": "round-trip conversion",
                "match": bool(math.isclose(back, expected, rel_tol=1e-9)),
            }
        except Exception:
            return {"method": "round-trip conversion", "match": None}

    def _applied_params(self, args: dict) -> dict[str, str]:
        params = dict(args.get("params", {}) or {})
        cleaned = {
            str(key): self._expression(str(value)) for key, value in params.items()
        }
        return cleaned

    def _op_physics(self, args: dict) -> CalculatorResult:
        from asis.calculator import applied

        formula = str(args.get("formula", "")).strip()
        if not formula:
            raise errors.invalid_expression("physics needs a formula")
        outcome = applied.physics(formula, self._applied_params(args))
        return self._result(
            "physics",
            formula,
            exact=str(outcome["result"]),
            numeric=outcome["result"],
            units=outcome.get("unit"),
            steps=(outcome.get("formula", ""),),
        )

    def _op_engineering(self, args: dict) -> CalculatorResult:
        from asis.calculator import applied

        name = str(args.get("calculation", "")).strip()
        if not name:
            raise errors.invalid_expression("engineering needs a calculation")
        outcome = applied.engineering(name, self._applied_params(args))
        return self._result(
            "engineering",
            name,
            exact=str(outcome["result"]),
            numeric=outcome["result"],
            units=outcome.get("unit"),
            steps=(outcome.get("formula", ""),),
        )

    def _op_finance(self, args: dict) -> CalculatorResult:
        from asis.calculator import applied

        name = str(args.get("calculation", "")).strip()
        if not name:
            raise errors.invalid_expression("finance needs a calculation")
        outcome = applied.finance(name, self._applied_params(args))
        steps = tuple(
            part
            for part in (outcome.get("formula", ""), outcome.get("assumptions", ""))
            if part
        )
        return self._result(
            "finance",
            name,
            exact=str(outcome["result"]),
            numeric=outcome["result"],
            units=outcome.get("unit"),
            steps=steps,
        )


def build_engine_from_settings(settings_obj=None) -> CalculatorEngine:
    """Build the configured engine (limits, precision, angle mode)."""
    if settings_obj is None:
        from asis.configuration.settings import settings as settings_obj
    calc = settings_obj.calculator
    return CalculatorEngine(
        max_expression_chars=calc.max_expression_chars,
        max_matrix_size=calc.max_matrix_size,
        precision=calc.precision,
        angle_mode=calc.angle_mode,
    )

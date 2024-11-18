import unittest
import sys
import json
import re
import ast
import operator
from io import StringIO
from unittest.mock import patch

constants = {}
name_pattern = re.compile(r'^[A-Z_]+$')
operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

def eval_expr(expr):
    def _eval(node):
        if isinstance(node, ast.Constant):  # <number>
            return node.value
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            left = _eval(node.left)
            right = _eval(node.right)
            return operators[type(node.op)](left, right)
        else:
            raise TypeError(node)
    return _eval(ast.parse(expr, mode='eval').body)

def parse_json(value):
    if isinstance(value, dict):
        items = []
        for key, val in value.items():
            if key == "define":
                # Handling define statements
                define_match = re.match(r'\(define\s+([A-Z_]+)\s+(.+)\)', val)
                if define_match:
                    name, constant_value = define_match.groups()
                    if not name_pattern.match(name):
                        raise ValueError(f"Invalid constant name '{name}'.")
                    constants[name] = constant_value.strip()
                continue  # Skip adding "define" to output
            if not name_pattern.match(key):
                raise ValueError(f"Invalid name '{key}'. Names must consist of uppercase letters A-Z and underscores.")

            # Recursive processing
            parsed_value = parse_json(val)
            items.append(f" {key} : {parsed_value}")
        return "$[\n" + ",\n".join(items) + "\n]"
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        # Replace constants inside the string
        value = re.sub(r'!\{([A-Z_]+)\}', lambda m: constants.get(m.group(1), m.group(0)), value)
        try:
            # Try to evaluate the expression
            computed_value = eval_expr(value)
            return str(computed_value)
        except Exception:
            # Return as a string if evaluation fails
            return f'"{value}"'
    else:
        raise ValueError(f"Unsupported value type: {value}")

# Unit tests
class TestConfigConverter(unittest.TestCase):

    def setUp(self):
        # Reset constants before each test
        self.original_constants = constants.copy()
        constants.clear()

    def tearDown(self):
        # Restore constants after each test
        constants.update(self.original_constants)

    def test_define_constant(self):
        # Test defining a constant
        input_json = {
            "define": "(define PI 3.14)",
            "VALUE": "!{PI}"
        }
        expected_output = "$[\n VALUE : 3.14\n]"
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)
        self.assertEqual(constants['PI'], '3.14')

    def test_invalid_constant_name(self):
        # Test invalid constant name
        input_json = {
            "define": "(define invalidName 42)"
        }
        with self.assertRaises(ValueError):
            parse_json(input_json)
    def test_invalid_name(self):
        # Test invalid key name
        input_json = {
            "InvalidName": "42"
        }
        with self.assertRaises(ValueError):
            parse_json(input_json)

    def test_integer_value(self):
        # Test integer value parsing
        input_json = {
            "VALUE": 100
        }
        expected_output = "$[\n VALUE : 100\n]"
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_string_value(self):
        # Test string value parsing
        input_json = {
            "MESSAGE": "Hello World"
        }
        expected_output = '$[\n MESSAGE : "Hello World"\n]'
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_expression_evaluation(self):
        # Test arithmetic expression evaluation
        input_json = {
            "RESULT": "2 + 3 * 4"
        }
        expected_output = "$[\n RESULT : 14\n]"
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_nested_structure(self):
        # Test nested dictionaries
        input_json = {
            "CONFIG": {
                "SETTING": "42",
                "NESTED": {
                    "VALUE": "100"
                }
            }
        }
        expected_output = "$[\n CONFIG : $[\n SETTING : \"42\",\n NESTED : $[\n VALUE : \"100\"\n]\n]\n]"
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_constant_in_expression(self):
        # Test constant usage in expressions
        input_json = {
            "define": "(define MAX_VALUE 256)",
            "LIMIT": "!{MAX_VALUE} - 1"
        }
        expected_output = "$[\n LIMIT : 255\n]"
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_undefined_constant(self):
        # Test usage of an undefined constant
        input_json = {
            "VALUE": "!{UNDEFINED}"
        }
        expected_output = '$[\n VALUE : "!{UNDEFINED}"\n]'
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_complex_expression(self):
        # Test complex arithmetic expression
        input_json = {
            "RESULT": "(2 + 3) * (4 - 1)"
        }
        expected_output = "$[\n RESULT : 15\n]"
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_modulo_operator(self):
        # Test modulo operator
        input_json = {
            "REMAINDER": "10 % 3"
        }
        expected_output = "$[\n REMAINDER : 1\n]"
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_power_operator(self):
        # Test power operator
        input_json = {
            "POWER": "2 ** 3"
        }
        expected_output = "$[\n POWER : 8\n]"
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_floor_division(self):
        # Test floor division operator
        input_json = {
            "DIVISION": "7 // 2"
        }
        expected_output = "$[\n DIVISION : 3\n]"
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_invalid_expression(self):
        # Test invalid arithmetic expression
        input_json = {
            "RESULT": "2 + "
        }
        expected_output = '$[\n RESULT : "2 + "\n]'
        output = parse_json(input_json)
        self.assertEqual(output, expected_output)

    def test_unsupported_value_type(self):
        # Test unsupported value type (e.g., list)
        input_json = {
            "LIST": [1, 2, 3]
        }
        with self.assertRaises(ValueError):
            parse_json(input_json)

if __name__ == '__main__':
    unittest.main()

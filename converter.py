import sys
import json
import argparse
import re
import ast
import operator

# Словарь для хранения констант
constants = {}

# Обновленное регулярное выражение для имени
name_pattern = re.compile(r'^[A-Z_]+$')

# Поддерживаемые операторы для вычисления выражений
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
    """
    Безопасное вычисление арифметических выражений
    """

    def _eval(node):
        if isinstance(node, ast.Constant):  # <число>
            return node.value
        elif isinstance(node, ast.BinOp):  # <левый операнд> <оператор> <правый операнд>
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
                # Обработка объявления константы
                define_match = re.match(r'\(define\s+([A-Z_]+)\s+(.+)\)', val)
                if define_match:
                    name, constant_value = define_match.groups()
                    if not name_pattern.match(name):
                        raise ValueError(f"Invalid constant name '{name}'.")
                    constants[name] = constant_value.strip()
                    print(f"Defined constant: {name} = {constants[name]}")
                continue  # Пропускаем добавление в output для "define"
            if not name_pattern.match(key):
                raise ValueError(f"Invalid name '{key}'. Names must consist of uppercase letters A-Z and underscores.")

            # Рекурсивная обработка значений
            parsed_value = parse_json(val)
            items.append(f" {key} : {parsed_value}")
        return "$[\n" + ",\n".join(items) + "\n]"
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        # Замена констант внутри строки
        value = re.sub(r'!\{([A-Z_]+)\}', lambda m: constants.get(m.group(1), m.group(0)), value)
        try:
            # Пытаемся вычислить выражение
            computed_value = eval_expr(value)
            return str(computed_value)
        except Exception:
            # Если вычислить не удалось, возвращаем как строку
            return f'"{value}"'
    else:
        raise ValueError(f"Unsupported value type: {value}")


def main():
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='Convert JSON to custom configuration language.')
    parser.add_argument('-o', '--output', required=True, help='Path to the output file.')
    args = parser.parse_args()

    # Чтение входного JSON или текста
    try:
        input_text = sys.stdin.read()
        print("Original Input Text:")
        print(input_text)

        json_data = json.loads(input_text)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error processing input: {e}")
        sys.exit(1)

    # Преобразование JSON в конфигурационный язык
    try:
        output = parse_json(json_data)
    except ValueError as e:
        print(f"Error processing input: {e}")
        sys.exit(1)

    # Запись результата в файл
    try:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Output written to {args.output}")
    except IOError as e:
        print(f"File writing error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

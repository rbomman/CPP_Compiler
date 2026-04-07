import unittest
from contextlib import redirect_stdout
from io import StringIO

from compiler import compile_source, execute_program


class CompilerIntegrationTests(unittest.TestCase):
    def compile_and_run(self, source):
        instructions = compile_source(source)
        self.assertIsNotNone(instructions, "Compilation failed unexpectedly.")
        result, globals_state = execute_program(instructions)
        self.assertIsNotNone(globals_state, "Execution failed unexpectedly.")
        return result, globals_state

    def compile_fails(self, source):
        output = StringIO()
        with redirect_stdout(output):
            instructions = compile_source(source)
        self.assertIsNone(instructions, "Compilation unexpectedly succeeded.")
        return output.getvalue()

    def execute_fails(self, source):
        instructions = compile_source(source)
        self.assertIsNotNone(instructions, "Compilation failed unexpectedly.")
        output = StringIO()
        with redirect_stdout(output):
            result, globals_state = execute_program(instructions)
        self.assertIsNone(result, "Execution unexpectedly succeeded.")
        self.assertIsNone(globals_state, "Execution unexpectedly returned globals.")
        return output.getvalue()

    def test_pointer_write_through_scalar(self):
        result, _ = self.compile_and_run(
            """
            int main() {
                int x = 4;
                int* p = &x;
                *p = 9;
                return x;
            }
            """
        )
        self.assertEqual(result, 9)

    def test_struct_by_value_param_and_return(self):
        result, _ = self.compile_and_run(
            """
            struct Point { int x; int y; };

            struct Point copy_point(struct Point p) {
                return p;
            }

            int main() {
                struct Point a;
                struct Point b;
                a.x = 2;
                a.y = 5;
                b = copy_point(a);
                return b.y;
            }
            """
        )
        self.assertEqual(result, 5)

    def test_array_of_structs(self):
        result, _ = self.compile_and_run(
            """
            struct Point { int x; int y; };
            struct Point points[2];

            int main() {
                points[1].x = 7;
                points[1].y = 9;
                return points[1].y;
            }
            """
        )
        self.assertEqual(result, 9)

    def test_arrow_field_access(self):
        result, _ = self.compile_and_run(
            """
            struct Point { int x; int y; };

            int main() {
                struct Point p;
                struct Point* ptr = &p;
                ptr->x = 11;
                return ptr->x;
            }
            """
        )
        self.assertEqual(result, 11)

    def test_whole_struct_assignment(self):
        result, _ = self.compile_and_run(
            """
            struct Point { int x; int y; };

            int main() {
                struct Point a;
                struct Point b;
                a.x = 3;
                a.y = 8;
                b = a;
                return b.x + b.y;
            }
            """
        )
        self.assertEqual(result, 11)

    def test_out_of_bounds_array_access_reports_runtime_error(self):
        output = self.execute_fails(
            """
            int values[2];

            int main() {
                int* p = &values[0];
                return *(p + 2);
            }
            """
        )
        self.assertIn("Out-of-bounds read through pointer", output)
        self.assertIn("At instruction", output)

    def test_invalid_struct_field_reports_semantic_error(self):
        output = self.compile_fails(
            """
            struct Point { int x; };

            int main() {
                struct Point p;
                return p.y;
            }
            """
        )
        self.assertIn("has no field named 'y'", output)

    def test_runtime_error_mentions_failing_instruction(self):
        output = self.execute_fails(
            """
            int main() {
                return 1 / 0;
            }
            """
        )
        self.assertIn("Division by zero.", output)
        self.assertIn("DIV", output)


if __name__ == "__main__":
    unittest.main()

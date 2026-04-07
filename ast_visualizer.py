import argparse
from pathlib import Path

from cpp_parser import ASTNode, Parser
from lexer import tokenize


class ASTVisualizer:
    """Build text, DOT, and optional image views for the real current AST."""

    def __init__(self):
        self.node_count = 0
        self.nodes = {}
        self.edges = []

    def build(self, ast):
        self.node_count = 0
        self.nodes = {}
        self.edges = []
        self._build_graph(ast)
        return self

    def render_text(self, ast):
        return "\n".join(self._render_text_node(ast))

    def render_dot(self, ast):
        self.build(ast)
        lines = ["digraph AST {", '  rankdir="TB";', '  node [shape=box, style="rounded,filled", fillcolor="#dbeafe"];']
        for node_id, label in self.nodes.items():
            escaped = label.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            lines.append(f'  n{node_id} [label="{escaped}"];')
        for parent_id, child_id, edge_label in self.edges:
            if edge_label:
                escaped = edge_label.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'  n{parent_id} -> n{child_id} [label="{escaped}"];')
            else:
                lines.append(f"  n{parent_id} -> n{child_id};")
        lines.append("}")
        return "\n".join(lines)

    def visualize_image(self, ast, output_path=None, title="AST Visualization"):
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
        except Exception as exc:
            raise RuntimeError(
                "Image rendering requires a working matplotlib/networkx installation. "
                "Use text output or --format dot as a dependency-free fallback."
            ) from exc

        self.build(ast)
        graph = nx.DiGraph()
        for node_id, label in self.nodes.items():
            graph.add_node(node_id, label=label)
        for parent_id, child_id, edge_label in self.edges:
            graph.add_edge(parent_id, child_id, label=edge_label)

        pos = nx.spring_layout(graph, seed=42, k=1.2)
        labels = nx.get_node_attributes(graph, "label")
        edge_labels = nx.get_edge_attributes(graph, "label")

        plt.figure(figsize=(16, 10))
        nx.draw(
            graph,
            pos,
            labels=labels,
            node_color="#dbeafe",
            node_size=2600,
            font_size=8,
            arrows=True,
            arrowsize=18,
            edgecolors="#1f2937",
            linewidths=1.0,
        )
        nx.draw_networkx_edge_labels(
            graph,
            pos,
            edge_labels=edge_labels,
            font_size=7,
            font_color="#374151",
            label_pos=0.5,
        )
        plt.title(title)
        plt.axis("off")
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=200, bbox_inches="tight")
            plt.close()
            return

        plt.show()

    def _build_graph(self, node, parent_id=None, edge_label=None):
        node_id = self._new_node_id()
        self.nodes[node_id] = self._node_label(node)
        if parent_id is not None:
            self.edges.append((parent_id, node_id, edge_label or ""))

        for child_label, child_value in self._iter_children(node):
            self._build_child(child_value, node_id, child_label)

    def _build_child(self, value, parent_id, edge_label):
        if isinstance(value, list):
            list_id = self._new_node_id()
            self.nodes[list_id] = "List"
            self.edges.append((parent_id, list_id, edge_label))
            for index, item in enumerate(value):
                self._build_child(item, list_id, f"[{index}]")
            return

        if isinstance(value, tuple):
            tuple_id = self._new_node_id()
            self.nodes[tuple_id] = "Tuple"
            self.edges.append((parent_id, tuple_id, edge_label))
            for index, item in enumerate(value):
                self._build_child(item, tuple_id, f"[{index}]")
            return

        self._build_graph(value, parent_id, edge_label)

    def _render_text_node(self, node, prefix="", edge_label=None, is_last=True):
        connector = ""
        next_prefix = prefix
        if edge_label is not None:
            connector = "`-- " if is_last else "|-- "
            next_prefix = prefix + ("    " if is_last else "|   ")

        label = self._node_label(node)
        line = f"{prefix}{connector}{edge_label}: {label}" if edge_label is not None else label
        lines = [line]

        children = list(self._iter_children(node))
        for index, (child_label, child_value) in enumerate(children):
            child_last = index == len(children) - 1
            lines.extend(self._render_text_child(child_value, next_prefix, child_label, child_last))
        return lines

    def _render_text_child(self, value, prefix, edge_label, is_last):
        if isinstance(value, list):
            connector = "`-- " if is_last else "|-- "
            lines = [f"{prefix}{connector}{edge_label}: List"]
            child_prefix = prefix + ("    " if is_last else "|   ")
            for index, item in enumerate(value):
                item_last = index == len(value) - 1
                lines.extend(self._render_text_child(item, child_prefix, f"[{index}]", item_last))
            return lines

        if isinstance(value, tuple):
            connector = "`-- " if is_last else "|-- "
            lines = [f"{prefix}{connector}{edge_label}: Tuple"]
            child_prefix = prefix + ("    " if is_last else "|   ")
            for index, item in enumerate(value):
                item_last = index == len(value) - 1
                lines.extend(self._render_text_child(item, child_prefix, f"[{index}]", item_last))
            return lines

        return self._render_text_node(value, prefix, edge_label, is_last)

    def _iter_children(self, node):
        if isinstance(node, ASTNode):
            for field_name, value in vars(node).items():
                yield field_name, value
            return
        return
        yield

    def _node_label(self, node):
        if node is None:
            return "None"
        if isinstance(node, ASTNode):
            base_label = node.__class__.__name__
            highlights = self._node_highlights(node)
            return f"{base_label} | {highlights}" if highlights else base_label
        if isinstance(node, str):
            return repr(node)
        return str(node)

    def _node_highlights(self, node):
        highlights = []
        for field_name in (
            "name",
            "var_name",
            "array_name",
            "field_name",
            "operator",
            "return_type",
            "var_type",
            "struct_type",
            "element_type",
        ):
            if hasattr(node, field_name):
                value = getattr(node, field_name)
                if isinstance(value, str):
                    highlights.append(f"{field_name}={value}")
        return ", ".join(highlights[:3])

    def _new_node_id(self):
        node_id = self.node_count
        self.node_count += 1
        return node_id


def parse_source(source_text):
    tokens = tokenize(source_text)
    return Parser(tokens).parse_program()


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize the current AST for a source file.")
    parser.add_argument(
        "source",
        nargs="?",
        default="input.cpp",
        help="Source file to parse. Defaults to input.cpp.",
    )
    parser.add_argument(
        "--output",
        help="Optional output path. Supports .txt, .dot, or image formats when plotting dependencies are available.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "dot", "image"],
        default="text",
        help="Output format. Defaults to text.",
    )
    parser.add_argument(
        "--title",
        default="AST Visualization",
        help="Title used for image output.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    source_text = Path(args.source).read_text()
    ast = parse_source(source_text)
    visualizer = ASTVisualizer()

    if args.format == "text":
        rendered = visualizer.render_text(ast)
        if args.output:
            Path(args.output).write_text(rendered)
            print(f"AST text written to {args.output}")
        else:
            print(rendered)
        return

    if args.format == "dot":
        rendered = visualizer.render_dot(ast)
        if args.output:
            Path(args.output).write_text(rendered)
            print(f"AST DOT written to {args.output}")
        else:
            print(rendered)
        return

    visualizer.visualize_image(ast, output_path=args.output, title=args.title)
    if args.output:
        print(f"AST image written to {args.output}")


if __name__ == "__main__":
    main()

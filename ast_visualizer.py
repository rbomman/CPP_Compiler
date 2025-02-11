import networkx as nx
import matplotlib.pyplot as plt

# --- AST Node Definitions (Example) ---
# These should match the classes from your parser

class ASTNode:
    pass

class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

class VariableDeclaration(ASTNode):
    def __init__(self, var_type, var_name, value):
        self.var_type = var_type  # a string, e.g., "int"
        self.var_name = var_name  # a string, e.g., "a"
        self.value = value        # typically an int literal for now

class Assignment(ASTNode):
    def __init__(self, var_name, value):
        self.var_name = var_name  # a string
        self.value = value        # an int literal or a string (identifier)

class ReturnStatement(ASTNode):
    def __init__(self, value):
        self.value = value  # a string (identifier) for now

# --- AST Visualizer Class ---

class ASTVisualizer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_count = 0

    def visualize(self, ast):
        # Build the graph starting at the root AST node.
        self._build_graph(ast)
        # Use a layout algorithm for positioning nodes
        pos = nx.spring_layout(self.graph)
        labels = nx.get_node_attributes(self.graph, 'label')
        nx.draw(self.graph, pos, labels=labels, node_color='lightblue', 
                node_size=2000, font_size=10, arrows=True)
        plt.title("AST Visualization")
        plt.show()

    def _build_graph(self, node, parent_id=None, edge_label=""):
        """
        Recursively add nodes and edges to the graph.
        If node is not an AST node (i.e. a literal), treat it as a leaf.
        """
        node_id = self.node_count
        self.node_count += 1

        # Determine the label for the current node.
        node_label = self.get_node_label(node)
        if edge_label:
            node_label = f"{edge_label}: {node_label}"
        
        self.graph.add_node(node_id, label=node_label)
        if parent_id is not None:
            self.graph.add_edge(parent_id, node_id)

        # Recursively add children based on the type of AST node.
        if isinstance(node, Program):
            for stmt in node.statements:
                self._build_graph(stmt, node_id)
        elif isinstance(node, VariableDeclaration):
            # Add children for type, name, and value.
            self._build_graph(node.var_type, node_id, "type")
            self._build_graph(node.var_name, node_id, "name")
            self._build_graph(node.value, node_id, "value")
        elif isinstance(node, Assignment):
            self._build_graph(node.var_name, node_id, "name")
            self._build_graph(node.value, node_id, "value")
        elif isinstance(node, ReturnStatement):
            self._build_graph(node.value, node_id, "value")
        # For literals (strings, ints, etc.), no further children.
        elif isinstance(node, (str, int)):
            # Literal value; nothing further to do.
            pass
        else:
            # If you add more node types later, handle them here.
            pass

    def get_node_label(self, node):
        """
        Returns a string label for the given AST node or literal.
        """
        if isinstance(node, Program):
            return "Program"
        elif isinstance(node, VariableDeclaration):
            return "VarDecl"
        elif isinstance(node, Assignment):
            return "Assign"
        elif isinstance(node, ReturnStatement):
            return "Return"
        else:
            # For literals (e.g. int or str), just return their string value.
            return str(node)

# --- Example Usage ---

if __name__ == "__main__":
    # Construct an example AST corresponding to:
    # int a = 5;
    # return a;
    ast = Program([
        VariableDeclaration('int', 'a', 5),
        ReturnStatement('a')
    ])

    visualizer = ASTVisualizer()
    visualizer.visualize(ast)

import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_cytoscape as cyto
import pandas as pd
import itertools
from openai import OpenAI
import os

# -----------------------------
# Helper Functions for Parsing
# -----------------------------
def split_top_level(s):
    """
    Splits the string s on commas not inside any parentheses.
    """
    parts = []
    current = []
    depth = 0
    for char in s:
        if char == '(':
            depth += 1
            current.append(char)
        elif char == ')':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(char)
    if current:
        part = "".join(current).strip()
        if part:
            parts.append(part)
    return parts

def parse_policy(s):
    """
    Recursively parses a policy string into a tree.
    
    Basic functions supported: pk, after, older, thresh.
    Returns a dictionary-based tree.
    """
    s = s.strip()
    if '(' not in s:
        return s
    idx = s.find('(')
    fname = s[:idx].strip()
    inner = s[idx+1:-1].strip()  # content inside the outer parentheses
    if fname == "thresh":
        parts = split_top_level(inner)
        k = int(parts[0])
        children = [parse_policy(part) for part in parts[1:]]
        return {"type": "thresh", "k": k, "children": children}
    elif fname in ("pk", "after", "older"):
        arg = inner.strip()
        return {"type": fname, "value": arg}
    else:
        parts = split_top_level(inner)
        children = [parse_policy(part) for part in parts]
        return {"type": fname, "children": children}

def eval_policy(node, epoch):
    """
    Recursively evaluates the policy node for a given epoch.
    Returns a list of spending path strings that satisfy this node.
    
    Conventions:
      - pk(KEY): always available (return its string).
      - after(n) / older(n): available only if epoch >= n.
      - thresh(k, children...): returns all combinations (joined with 'AND')
        from at least k children that are available.
    """
    if isinstance(node, str):
        return [node]
    
    t = node.get("type")
    if t == "pk":
        return [f"pk({node['value']})"]
    elif t in ("after", "older"):
        n = int(node["value"])
        if epoch >= n:
            return [f"{t}({node['value']})"]
        else:
            return []
    elif t == "thresh":
        results = []
        children_paths = [eval_policy(child, epoch) for child in node["children"]]
        available = [(i, paths) for i, paths in enumerate(children_paths) if paths]
        for r in range(node["k"], len(available) + 1):
            for subset in itertools.combinations(available, r):
                for choice in itertools.product(*[paths for (i, paths) in subset]):
                    combined = " AND ".join(choice)
                    results.append(f"thresh{{{combined}}}")
        return results
    else:
        return []

def count_public_keys(path):
    """
    Counts the number of occurrences of "pk(" in a spending path.
    """
    return path.count("pk(")

def spending_paths_table(policy_str):
    """
    Returns a table (dictionary and DataFrame) for epochs 1–9,
    showing available spending paths, the number of paths,
    and the minimum number of public keys required.
    """
    tree = parse_policy(policy_str)
    table = {}
    for epoch in range(1, 10):
        paths = eval_policy(tree, epoch)
        paths = sorted(set(paths))
        num_paths = len(paths)
        if paths:
            pk_counts = [count_public_keys(path) for path in paths]
            min_pks = min(pk_counts)
        else:
            min_pks = 0
        table[epoch] = {
            "Spending Paths": paths if paths else ["None"],
            "Num Spending Paths": num_paths,
            "Min Public Keys Used": min_pks
        }
    df = pd.DataFrame([
        {"Epoch": epoch, 
         "Spending Paths": "; ".join(info["Spending Paths"]),
         "Num Spending Paths": info["Num Spending Paths"],
         "Min Public Keys Used": info["Min Public Keys Used"]}
        for epoch, info in table.items()
    ])
    return table, df

# ----------------------------------
# Helper Functions for Graph Display
# ----------------------------------
def build_graph_elements(node, parent_id=None, counter=[0]):
    """
    Recursively builds a list of elements for dash_cytoscape.
    Each node gets a unique id.
    """
    elements = []
    node_id = f"node_{counter[0]}"
    counter[0] += 1
    
    # Determine label based on node type or string literal.
    if isinstance(node, str):
        label = node
    elif isinstance(node, dict):
        if node["type"] == "thresh":
            label = f"thresh({node['k']})"
        elif node["type"] in ("pk", "after", "older"):
            label = f"{node['type']}({node.get('value','')})"
        else:
            label = node["type"]
    else:
        label = str(node)
        
    elements.append({"data": {"id": node_id, "label": label}})
    
    # Create an edge from parent to this node, if parent exists.
    if parent_id is not None:
        elements.append({"data": {"source": parent_id, "target": node_id}})
    
    # Recurse for children, if any.
    if isinstance(node, dict) and "children" in node:
        for child in node["children"]:
            elements.extend(build_graph_elements(child, parent_id=node_id, counter=counter))
    return elements

def traverse_tree_explanation(node, indent=0):
    """
    Recursively creates a text explanation of the node.
    """
    indent_str = "  " * indent
    explanation = ""
    if isinstance(node, str):
        explanation += f"{indent_str}- {node}\n"
    elif isinstance(node, dict):
        if node["type"] == "thresh":
            explanation += f"{indent_str}- Threshold node: requires {node['k']} of {len(node['children'])} conditions:\n"
            for child in node["children"]:
                explanation += traverse_tree_explanation(child, indent + 1)
        elif node["type"] in ("pk", "after", "older"):
            explanation += f"{indent_str}- {node['type']} condition: {node.get('value','')}\n"
        else:
            explanation += f"{indent_str}- {node['type']} node\n"
            if "children" in node:
                for child in node["children"]:
                    explanation += traverse_tree_explanation(child, indent+1)
    return explanation

def explain_policy(policy_str):
    """
    Returns a ChatGPT-style explanation string for the policy.
    """
    tree = parse_policy(policy_str)
    explanation = "### Policy Explanation\n\n"
    explanation += "The input policy is parsed into a tree structure with the following breakdown:\n\n"
    explanation += traverse_tree_explanation(tree)
    explanation += "\nThis policy uses threshold conditions (thresh), key signatures (pk), and timelocks (after, older) to enforce spending paths. " \
                   "Depending on the epoch (a discrete time period from 1 to 9), certain timelocks become active, " \
                   "thus enabling additional spending paths. The table below summarizes, for each epoch, which conditions " \
                   "can be satisfied and the number of public key signatures required in the minimal spending path."
    return explanation

# ---------------------
# Dash App Layout
# ---------------------
app = dash.Dash(__name__)


client = OpenAI(
  api_key=os.getenv("OPENAI_API_KEY")
)

app.layout = html.Div([
    html.H1("Policy Analyzer"),
    html.Div("Enter your policy:"),
    dcc.Textarea(
        id="policy-input",
        value=("thresh(2,pk(A9b),thresh(5,pk(PTy),thresh(1,thresh(2,pk(WoH),pk(Nnv),"
               "thresh(5,older(4),older(8),older(7),older(6),pk(Mt9))),after(8)),"
               "pk(oqZ),pk(W9c),older(7),after(9)),after(3))"),
        style={"width": "100%", "height": "100px"}
    ),
    html.Br(),
    html.Button("Submit", id="submit-button", n_clicks=0),
    html.Hr(),
    html.Div([
        html.H2("Graph Representation of Policy"),
        cyto.Cytoscape(
            id='policy-graph',
            layout={'name': 'breadthfirst'},
            style={'width': '100%', 'height': '400px'},
            elements=[]
        )
    ]),
    html.Br(),
    html.H2("Spending Paths Table (Epochs 1-9)"),
    dash_table.DataTable(
        id='paths-table',
        columns=[
            {"name": "Epoch", "id": "Epoch"},
            {"name": "Spending Paths", "id": "Spending Paths"},
            {"name": "Num Spending Paths", "id": "Num Spending Paths"},
            {"name": "Min Public Keys Used", "id": "Min Public Keys Used"}
        ],
        data=[],
        style_cell={'textAlign': 'left'},
        style_table={'overflowX': 'auto'}
    ),
    html.Br(),
    html.H2("Policy Explanation"),
    html.Div(id='policy-explanation', style={'whiteSpace': 'pre-line', 'padding': '10px', 'border': '1px solid #ccc'})
])

# ---------------------
# Dash Callbacks
# ---------------------
@app.callback(
    [Output('policy-graph', 'elements'),
     Output('paths-table', 'data'),
     Output('policy-explanation', 'children')],
    Input('submit-button', 'n_clicks'),
    State('policy-input', 'value')
)
def update_output(n_clicks, policy_str):
    if n_clicks == 0:
        # Before submission, show empty outputs or default values.
        return [], [], "Enter a policy and click Submit."
    
    # Parse the policy
    try:
        tree = parse_policy(policy_str)
    except Exception as e:
        return [], [], f"Error parsing policy: {e}"
    
    # Build graph elements
    graph_elements = build_graph_elements(tree)
    
    # Build spending paths table (as a DataFrame then dict for dash_table)
    _, df = spending_paths_table(policy_str)
    table_data = df.to_dict('records')
    
    # Generate a ChatGPT explanation
    explanation = client.responses.create(
        model="gpt-4o",
        instructions="You are a cryptography engineer with deep knowledge about threshold cryptography and cryptographic policies created with miniscript described in BIP 379 located at https://bitcoin.sipa.be/miniscript/. You have to create a short and realistic use case example based on the input table which describes the spending paths of a policy in discrete time epochs 1 to 9.",
        input=df.to_json()
        ).output_text

    
    return graph_elements, table_data, explanation

# ---------------------
# Run the App
# ---------------------
if __name__ == '__main__':
    app.run_server(debug=True)

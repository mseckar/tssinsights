import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.graph_objects as go
import sqlite3

# ---------- SQLite Integration ----------

DB_NAME = "master_policy(x,5,19).db"

def init_db():
    """Initialize the SQLite database and insert sample records if the table is empty."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PolicyTrees (
            id INTEGER PRIMARY KEY,
            policy TEXT NOT NULL,
            anonymized_miniscript TEXT NOT NULL,
            sipa_cost REAL
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM PolicyTrees")
    count = cursor.fetchone()[0]
    print(f"Loaded {count} records.")
    if count == 0:
        sample_data = [
            (
                'thresh(1, pk(a), pk(b))',
                'thresh(1, pk(anon), pk(anon))',
                10
            ),
            (
                'thresh(2, pk(x), thresh(1, pk(y), pk(z)))',
                'thresh(2, pk(anon), thresh(1, pk(anon), pk(anon)))',
                20
            ),
            (
                'thresh(3, pk(m), pk(n), pk(o))',
                'thresh(3, pk(anon), pk(anon), pk(anon))',
                30
            ),
            (
                'thresh(2, pk(p), thresh(1, pk(q), pk(r)))',
                # A more complex anonymized miniscript example:
                'thresh(2,j:and_v(and_v(and_v(v:pk(anon),v:multi(4, anon, anon, anon, anon, anon, anon, anon)),and_v(v:pk(anon),and_v(vc:or_i(pk_k(anon),or_i(pk_h(anon),or_i(pk_h(anon),or_i(pk_h(anon),pk_h(anon))))),vc:or_i(pk_k(anon),or_i(pk_h(anon),or_i(pk_h(anon),pk_h(anon))))))),thresh(2,utvc:or_i(pk_h(anon),pk_h(anon)),s:pk(anon),a:multi(4, anon, anon, anon, anon),s:pk(anon))),s:pk(anon),s:pk(anon))',
                40
            )
        ]
        cursor.executemany(
            "INSERT INTO PolicyTrees (policy, anonymized_miniscript, sipa_cost) VALUES (?, ?, ?)",
            sample_data
        )
        conn.commit()
    conn.close()

def run_sql_query(query):
    """
    Executes the provided SELECT query on the database.
    Returns both the result rows (as a list of dicts) and the column definitions.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # so we can access columns by name
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        if data:
            columns = [{"name": col, "id": col} for col in data[0].keys()]
        else:
            columns = [{"name": col[0], "id": col[0]} for col in cursor.description] if cursor.description else []
    except Exception as e:
        data = []
        columns = []
        print("SQL Query Error:", e)
    conn.close()
    return data, columns

# Initialize the database on startup.
init_db()

# ---------- Miniscript Parsing and Tree Layout Functions ----------
# We assume the miniscript is built from function calls (like thresh, and_v, multi, or_i, pk, etc.)
# with an optional prefix (e.g., "j:" or "v:") that we ignore.
# Literal tokens (like numbers or "anon") are treated as leaves.

def parse_miniscript(s):
    """Parses a miniscript string and returns an AST."""
    index = 0

    def skip_whitespace():
        nonlocal index
        while index < len(s) and s[index].isspace():
            index += 1

    def parse_identifier():
        nonlocal index
        start = index
        while index < len(s) and (s[index].isalnum() or s[index] in ['_', ':']):
            index += 1
        return s[start:index]

    def parse_expr():
        nonlocal index
        skip_whitespace()
        # Parse an identifier (which may include a prefix separated by ':')
        ident = parse_identifier()
        if not ident:
            raise ValueError(f"Expected identifier at index {index}")
        # If there is a colon, ignore the prefix.
        if ':' in ident:
            parts = ident.split(':', 1)
            func_name = parts[1]
        else:
            func_name = ident

        skip_whitespace()
        # If the next character is '(', it's a function call.
        if index < len(s) and s[index] == '(':
            index += 1  # skip '('
            args = []
            skip_whitespace()
            # Allow for empty argument list.
            if index < len(s) and s[index] == ')':
                index += 1
                return {"type": "func", "name": func_name, "args": args}
            while True:
                skip_whitespace()
                arg = parse_expr()
                args.append(arg)
                skip_whitespace()
                if index < len(s) and s[index] == ',':
                    index += 1  # skip comma
                    continue
                elif index < len(s) and s[index] == ')':
                    index += 1  # skip ')'
                    break
                else:
                    raise ValueError(f"Expected ',' or ')' at index {index}: {s[index:]}")
            return {"type": "func", "name": func_name, "args": args}
        else:
            # No '(', so it's a literal.
            return {"type": "literal", "value": func_name}

    result = parse_expr()
    return result

def assign_ids(node, next_id=[0]):
    """Recursively assigns a unique ID to each node."""
    node["id"] = next_id[0]
    next_id[0] += 1
    if node["type"] == "func":
        for child in node["args"]:
            assign_ids(child, next_id)

# Global counter for horizontal positioning.
next_x = 0

def assign_positions(node, depth=0, pos_dict=None):
    """
    Recursively assigns (x, y) positions for each node.
    - Leaf nodes (type "literal") get increasing x coordinates.
    - Internal nodes (type "func") have an x coordinate equal to the average of their children.
    - y is set to -depth so that the root appears at the top.
    """
    global next_x
    if pos_dict is None:
        pos_dict = {}
    if node["type"] == "literal":
        x = next_x
        next_x += 1
        pos_dict[node["id"]] = (x, -depth)
        return [x]
    else:
        child_x_positions = []
        for child in node["args"]:
            child_positions = assign_positions(child, depth+1, pos_dict)
            child_x_positions.extend(child_positions)
        if child_x_positions:
            avg_x = sum(child_x_positions) / len(child_x_positions)
        else:
            avg_x = next_x
            next_x += 1
        pos_dict[node["id"]] = (avg_x, -depth)
        return child_x_positions

def build_edges(node, edges=None):
    """Recursively builds a list of edges as tuples (parent_id, child_id)."""
    if edges is None:
        edges = []
    if node["type"] == "func":
        for child in node["args"]:
            edges.append((node["id"], child["id"]))
            build_edges(child, edges)
    return edges

def get_label(node):
    """
    Returns a label for the node.
    For function nodes, if the first argument is a literal number, include it.
    """
    if node["type"] == "func":
        label = node["name"]
        if node["args"]:
            first = node["args"][0]
            if first["type"] == "literal" and first["value"].isdigit():
                label += f"({first['value']})"
        return label
    elif node["type"] == "literal":
        return node["value"]

def traverse_tree(node, nodes_list):
    """Recursively collects all nodes in the tree."""
    nodes_list.append(node)
    if node["type"] == "func":
        for child in node["args"]:
            traverse_tree(child, nodes_list)

# ---------- Dash Application ----------

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H3("SQL Query for Policy Visualization (Miniscript)"),
    html.Div([
        html.Label("Enter a SELECT query:"),
        dcc.Textarea(
            id="sql-query-input",
            value="SELECT id, anonymized_miniscript, sipa_cost FROM PolicyTrees GROUP BY anonymized_miniscript, sipa_cost LIMIT 10;",
            style={"width": "100%", "height": 100}
        ),
        html.Button("Run Query", id="run-query-button", n_clicks=0)
    ], style={"padding": "10px", "border": "1px solid #ccc", "margin-bottom": "20px"}),
    
    html.H4("Query Results"),
    dash_table.DataTable(
        id="query-table",
        columns=[],
        data=[],
        row_selectable="single",
        page_current=0,
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'}
    ),
    html.H4("Policy Visualization (Anonymized Miniscript)"),
    dcc.Graph(id="policy-graph")
])

# Callback to run the user-entered SQL query and update the table.
@app.callback(
    [Output("query-table", "data"),
     Output("query-table", "columns")],
    Input("run-query-button", "n_clicks"),
    State("sql-query-input", "value")
)
def update_table(n_clicks, sql_query):
    if not sql_query:
        return [], []
    data, columns = run_sql_query(sql_query)
    return data, columns

# Callback to update the graph when a row is selected from the table.
@app.callback(
    Output("policy-graph", "figure"),
    Input("query-table", "selected_rows"),
    State("query-table", "data")
)
def update_graph(selected_rows, table_data):
    if not selected_rows or not table_data:
        return go.Figure()
    
    selected_index = selected_rows[0]
    # Use the anonymized_miniscript column for visualization.
    miniscript = table_data[selected_index].get("anonymized_miniscript", "")
    
    try:
        tree = parse_miniscript(miniscript)
    except Exception as e:
        return go.Figure(
            data=[], 
            layout=go.Layout(title=f"Error parsing miniscript: {e}")
        )
    
    # Build tree layout.
    assign_ids(tree)
    global next_x
    next_x = 0  # Reset horizontal counter.
    pos_dict = {}
    assign_positions(tree, depth=0, pos_dict=pos_dict)
    edges = build_edges(tree)
    
    # Build edge traces.
    edge_x = []
    edge_y = []
    for parent, child in edges:
        x0, y0 = pos_dict[parent]
        x1, y1 = pos_dict[child]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Gather node data.
    nodes = []
    traverse_tree(tree, nodes)
    
    node_x = []
    node_y = []
    node_text = []
    for node in nodes:
        x, y = pos_dict[node["id"]]
        node_x.append(x)
        node_y.append(y)
        node_text.append(get_label(node))
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="bottom center",
        hoverinfo='text',
        marker=dict(
            showscale=False,
            color='lightblue',
            size=30,
            line_width=2
        )
    )
    
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=f"Anonymized Miniscript Visualization (ID: {table_data[selected_index].get('id', '')})",
            font_size=16,
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)

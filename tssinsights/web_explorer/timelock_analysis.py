import itertools
import pandas as pd

def split_top_level(s):
    """
    Splits a string s on commas that are at the top level (i.e. not inside any parentheses).
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
    Recursively parses the policy string into a tree.

    Each node is represented as a dictionary:
      - For basic functions (pk, after, older):
            {"type": <name>, "value": <argument string>}
      - For thresh:
            {"type": "thresh", "k": <int>, "children": [child nodes]}
    Assumes well-formed input.
    """
    s = s.strip()
    # if the string does not contain a '(' then it is a literal (but in our policies all come as functions)
    if '(' not in s:
        return s
    # Find the function name (before the first parenthesis)
    idx = s.find('(')
    fname = s[:idx].strip()
    # Find the content inside the outermost parentheses.
    # We assume that the last character is the matching ")".
    inner = s[idx+1:-1].strip()
    # For thresh, the first argument is an integer k, and the rest are children.
    if fname == "thresh":
        parts = split_top_level(inner)
        # first part is k
        k = int(parts[0])
        children = [parse_policy(part) for part in parts[1:]]
        return {"type": "thresh", "k": k, "children": children}
    # For pk, after, older (assume a single argument)
    elif fname in ("pk", "after", "older"):
        # Remove any extra whitespace from the argument.
        arg = inner.strip()
        return {"type": fname, "value": arg}
    else:
        # For any other functions, we store the name and arguments as children.
        parts = split_top_level(inner)
        children = [parse_policy(part) for part in parts]
        return {"type": fname, "children": children}

def eval_policy(node, epoch):
    """
    Recursively evaluates the policy node for a given epoch.
    Returns a list of spending path strings that satisfy this node.

    Conventions:
      - For pk(KEY): always available. Return ["pk(KEY)"].
      - For after(n) or older(n): available only if epoch >= n.
      - For thresh(k, children...): returns all combinations of spending paths
        from at least k children, each combined by " AND ".
    """
    # Basic case: node is a literal string.
    if isinstance(node, str):
        return [node]
    
    t = node.get("type")
    if t == "pk":
        # A key is assumed to be available when needed.
        return [f"pk({node['value']})"]
    elif t in ("after", "older"):
        n = int(node["value"])
        if epoch >= n:
            return [f"{t}({node['value']})"]
        else:
            return []  # condition not satisfied at this epoch
    elif t == "thresh":
        results = []
        # Evaluate all children for the given epoch.
        children_paths = [eval_policy(child, epoch) for child in node["children"]]
        # Only consider children that produce non-empty results.
        available = [(i, paths) for i, paths in enumerate(children_paths) if paths]
        # For a thresh node, select any subset of available children of size >= k.
        for r in range(node["k"], len(available) + 1):
            for subset in itertools.combinations(available, r):
                # Choose one spending path variant from each child in the subset.
                prod = itertools.product(*[paths for (i, paths) in subset])
                for choice in prod:
                    combined = " AND ".join(choice)
                    results.append(f"thresh{{{combined}}}")
        return results
    else:
        # Unrecognized node type.
        return []

def count_public_keys(path):
    """
    Counts the number of occurrences of "pk(" in the spending path string.
    """
    return path.count("pk(")

def spending_paths_table(policy_str):
    """
    Given a policy string, returns a table (as a dictionary and as a pandas DataFrame)
    where:
       - Each row corresponds to an epoch (1 to 9)
       - "Spending Paths" column lists all available spending paths (as a semicolon-separated string)
       - "Num Spending Paths" shows the count of available spending paths at that epoch.
       - "Min Public Keys Used" shows the smallest number of public keys used among the available paths.
         (If no spending path is available, this value is set to 0.)
    """
    tree = parse_policy(policy_str)
    table = {}
    for epoch in range(1, 10):
        paths = eval_policy(tree, epoch)
        # Remove duplicates and sort them
        paths = sorted(set(paths))
        num_paths = len(paths)
        # Count public keys in each path and choose the minimal count (if any paths exist)
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
    # Convert the table to a DataFrame for easy display.
    df = pd.DataFrame([
        {
            "Epoch": epoch, 
            "Spending Paths": "; ".join(item for item in info["Spending Paths"]),
            "Num Spending Paths": info["Num Spending Paths"],
            "Min Public Keys Used": info["Min Public Keys Used"]
        }
        for epoch, info in table.items()
    ])
    return table, df

# --- Example usage ---

policy = (
    "thresh(2,pk(A9b),thresh(5,pk(PTy),thresh(1,thresh(2,pk(WoH),pk(Nnv),"
    "thresh(5,older(4),older(8),older(7),older(6),pk(Mt9))),after(8)),"
    "pk(oqZ),pk(W9c),older(7),after(9)),after(3))"
)

policy = "thresh(1,pk(anon),pk(anon))"
#policy = "and(or(pk(anon),pk(anon)),pk(anon))"

table, df = spending_paths_table(policy)

print("Spending Paths Table (as dictionary):")
for epoch in range(1, 10):
    info = table[epoch]
    print(f"Epoch {epoch}:")
    print("  Spending Paths:", info["Spending Paths"])
    print("  Num Spending Paths:", info["Num Spending Paths"])
    print("  Min Public Keys Used:", info["Min Public Keys Used"])
    print()

print("\nSpending Paths Table (as DataFrame):")
print(df)

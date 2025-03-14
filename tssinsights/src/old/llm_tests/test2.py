import itertools

def generate_trees(k, n, E, _memo=None):
    """
    Generate the set of all trees with up to n threshold nodes from root to leaf.

    That is, T_{k,n,E} = union_{d=0..n} of T_{k,d,E}, where:
      - T_{k,0,E} = { pk(e) for e in E }, and
      - For d >= 1, T_{k,d,E} = T_{k,d-1,E} union all threshold nodes whose
        children are in T_{k,d-1,E}.

    Parameters
    ----------
    k : int
        Maximum number of children in any threshold node.
    n : int
        Maximum number of threshold-node layers from root to leaf.
    E : list or set of strings
        Elements used for leaf nodes.
    _memo : dict
        Internal memoization cache (optional).

    Returns
    -------
    list of str
        A sorted list of unique string representations of all such trees.
    """
    if _memo is None:
        _memo = {}

    # If we've already computed it, return from cache
    if (k, n) in _memo:
        return _memo[(k, n)]

    # Base case: T_{k,0,E} => leaves
    if n == 0:
        leaves = [f"pk({e})" for e in E]
        result = sorted(set(leaves))
        _memo[(k, n)] = result
        return result

    # Otherwise, build T_{k,n,E} by:
    #  1) Taking everything from T_{k,n-1,E}
    #  2) Adding threshold expansions from T_{k,n-1,E}
    smaller_trees = generate_trees(k, n - 1, E, _memo)
    result_set = set(smaller_trees)

    # Generate all threshold nodes: 
    #   thresh(t, child_1, ..., child_m)
    #   with m in [1..k], t in [1..m], each child_i in T_{k,n-1,E}.
    for m in range(1, k + 1):
        # permutations of smaller_trees of length m (order matters)
        for perm in itertools.permutations(smaller_trees, m):
            # Skip the degenerate case if m=1 => t=1 => thresh(1, X) = X
            if m == 1:
                continue
            # For each t in [1..m], build thresh(t, ...)
            for t in range(1, m + 1):
                node_str = f"thresh({t}, {', '.join(perm)})"
                print(node_str)
                result_set.add(node_str)

    # Sort before storing in memo
    final_list = sorted(result_set)
    _memo[(k, n)] = final_list
    return final_list

def get_all_trees(k, n, E):
    """
    Utility to retrieve T_{k,n,E} exactly as described above:
    i.e. all trees that allow up to n threshold layers.
    
    This returns T_{k,n,E} directly, which already includes all
    T_{k,d,E} for d <= n (because of how we constructed it).
    """
    return generate_trees(k, n, E)

# ---------------
# Example usage
# ---------------
if __name__ == "__main__":
    # As in the prompt, k=2, n=2, E=["a", "b"]
    all_trees = get_all_trees(k=3, n=2, E=["a", "b"])

    print(f"Number of trees in T_2,2,[a,b]: {len(all_trees)}")
    for t in all_trees:
        print(t)
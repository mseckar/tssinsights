from multiprocessing import Pool, cpu_count
from itertools import combinations
from collections import deque
import time
import cProfile
import gc
import os

class PolicyGenerator:
    def __init__(self, base_elements, max_depth, max_width):
        self.base_elements = tuple(base_elements)  # Immutable for better memory usage
        self.max_depth = max_depth
        self.max_width = max_width
        self.cache = {}  # Memoization cache
        
    @staticmethod
    def generate_threshold_policy(threshold, elements):
        """Generate a threshold policy using string concatenation instead of join."""
        return 'thresh(' + str(threshold) + ', ' + ', '.join(elements) + ')'
    
    def generate_subtrees_optimized(self, depth, elements_subset):
        """
        Optimized subtree generation using memoization and generator expressions.
        """
        cache_key = (depth, elements_subset)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        results = set()
        
        # Base case: depth 0 or single element
        if depth == 0 or len(elements_subset) == 1:
            results.update(elements_subset)
            self.cache[cache_key] = results
            return results
        
        # Add basic elements
        results.update(elements_subset)
        
        # Generate subtrees using sliding window to reduce memory usage
        if depth > 0:
            elements_list = list(elements_subset)
            window_size = min(self.max_width, len(elements_list))
            
            for size in range(2, window_size + 1):
                for combo in combinations(elements_list, size):
                    subtrees = set()
                    for i in range(len(combo)):
                        subset = combo[:i] + combo[i+1:]
                        subtrees.update(self.generate_subtrees_optimized(depth - 1, subset))
                    
                    # Generate policies for all possible thresholds
                    for threshold in range(1, len(combo) + 1):
                        results.add(self.generate_threshold_policy(threshold, combo))
                        
                        # Add combinations with subtrees
                        for subtree in subtrees:
                            new_elements = combo[:i] + (subtree,) + combo[i+1:]
                            results.add(self.generate_threshold_policy(threshold, new_elements))
        
        self.cache[cache_key] = results
        return results

    def chunk_generator(self, chunk_size=1000):
        """Generate work chunks for parallel processing."""
        elements_chunks = [self.base_elements[i:i + chunk_size] 
                         for i in range(0, len(self.base_elements), chunk_size)]
        
        for depth in range(self.max_depth + 1):
            for elements in elements_chunks:
                yield (depth, elements)

def parallel_worker(args):
    """Optimized worker function with better memory management."""
    depth, elements = args
    generator = PolicyGenerator(elements, depth, len(elements))
    results = generator.generate_subtrees_optimized(depth, elements)
    
    # Clear worker memory
    del generator.cache
    gc.collect()
    
    return results

def generate_policy_trees_parallel_optimized(base_elements, max_depth, max_width, chunk_size=1000):
    """
    Optimized parallel policy tree generation with improved memory management and chunking.
    """
    # Calculate optimal number of processes based on CPU cores and memory
    num_processes = min(cpu_count(), os.cpu_count() or 1)
    
    # Initialize the main generator
    generator = PolicyGenerator(base_elements, max_depth, max_width)
    
    # Create process pool with maxtasksperchild to prevent memory leaks
    with Pool(processes=num_processes, maxtasksperchild=100) as pool:
        # Process chunks in parallel with progress tracking
        results_iterator = pool.imap_unordered(
            parallel_worker, 
            generator.chunk_generator(chunk_size)
        )
        
        # Combine results efficiently using a set
        all_policies = set()
        for chunk_results in results_iterator:
            all_policies.update(chunk_results)
            # Force garbage collection after processing each chunk
            gc.collect()
    
    return all_policies

def profile_generation(base_elements, max_depth, max_width):
    """Profile the policy generation for optimization analysis."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    policies = generate_policy_trees_parallel_optimized(base_elements, max_depth, max_width)
    
    profiler.disable()
    profiler.print_stats(sort='cumulative')
    
    return policies

def main():
    # Example usage with performance monitoring
    base_elements = [f"pk({chr(97 + i)})" for i in range(2)]
    max_depth = 2
    max_width = 2
    
    start_time = time.time()
    
    # Enable profiling in debug mode
    policies = profile_generation(base_elements, max_depth, max_width)
    #policies = generate_policy_trees_parallel_optimized(base_elements, max_depth, max_width)
    
    end_time = time.time()
    
    # Print results
    for policy in sorted(policies):
        print(policy)
    
    print(f"\nGenerated {len(policies)} unique policies in {end_time - start_time:.2f} seconds", 
          file=sys.stderr)

if __name__ == "__main__":
    import sys
    main()
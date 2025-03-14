from tssinsights.src.policygrammar import PolicyGrammar
from src.bucketing import Bucketing
from fuzzing_experiment_parallel import prepareEnv
import time

        
if __name__ == "__main__":
    
    depth = 19
    
    grammar_file = "base.g4"
    miniscript_file = "../miniscript/miniscript"
    output_file = f"policy(x,5,{depth})"
    
    grammar = PolicyGrammar(100000, depth, output_file, miniscript_file)
    prepareEnv(grammar_file)
    start_time = time.time()
    #grammar.generate_policy_file("temp.txt")
    #grammar.populateDBFromFile("temp.txt")
    grammar.populateDB()
    print(f"DB Population took {time.time() - start_time}")

    start_time = time.time()
    bucketing_worker = Bucketing()
    buckets = bucketing_worker.analyze(grammar)
    bucketing_worker.export_to_csv(buckets, f"../exports/{output_file}.csv")
    print(f"Bucketing took {time.time() - start_time}")
    grammar.conn.close()

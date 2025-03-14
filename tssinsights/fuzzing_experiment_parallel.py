from src.policygrammar import PolicyGrammar
from src.bucketing import Bucketing
from src.sqlitecallback import SqliteCallback
import time
import os
import multiprocessing
import subprocess
import sqlite3
import glob


def prepareEnv(name: str):
    # TODO: Generate the ANTLR file based on the input parameters
    # Placeholder: use the prewritten file
    prepare_env = "mkdir -p grammarinator_output"
    grammarinator_process = f"grammarinator-process {name} -o ./grammarinator_output --no-action"
    try:
        subprocess.run(prepare_env, shell=True, stderr=subprocess.STDOUT)
        
        # Set PYTHONPATH
        os.environ["PYTHONPATH"] = os.path.join(os.getcwd(), "grammarinator_output")
        result = subprocess.check_output("echo $PYTHONPATH", shell=True, stderr=subprocess.STDOUT)
        print(result.decode('utf-8'))
        result = subprocess.check_output(grammarinator_process, shell=True, stderr=subprocess.STDOUT)
        print(result.decode('utf-8'))
        print("Environment prepared successufully")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.output.decode('utf-8')}")


def worker_process(worker_id, sample_count, depth, miniscript_file, output_dir):
    """
    Worker function that generates policies and populates its own SQLite database.
    Each worker writes to its own DB file.
    """
    output_name = f"policy_worker_{worker_id}(x,5,{depth})"
    db_path = os.path.join(output_dir, f"{output_name}.db")
    
    grammar = PolicyGrammar(worker_id, sample_count, depth, db_path, miniscript_file)
    
    print(f"Worker {worker_id}: Starting policy generation and DB population.")
    start_time = time.time()
    grammar.populate_db()
    elapsed = time.time() - start_time
    print(f"Worker {worker_id}: DB population took {elapsed:.2f} seconds.")
    
    grammar.conn.close()


def generate_trees_parallel(sample_count: int, num_iterations: int, num_workers: int, depth: int, output_dir: str):
    full_time = time.time()
    
    for batch in range(num_iterations):
        # Create a pool of processes.
        processes = []
        for worker_id in range(num_workers):
            p = multiprocessing.Process(
                target=worker_process,
                args=(worker_id, sample_count, depth, miniscript_file, output_dir)
            )
            processes.append(p)
            p.start()
        
        # Wait for all worker processes to complete.
        for p in processes:
            p.join()
        print(f"Batch {batch} has successfuly finished")
    print(f"All workers have finished generating policies and populating their databases in {time.time() - full_time}s.")


def merge_worker_databases(master_db_path, worker_db_dir):
    # Connect to (or create) the master database.
    master_conn = sqlite3.connect(master_db_path)
    master_cursor = master_conn.cursor()
    
    # Create the PolicyTrees table in the master DB if it doesn't exist.
    master_cursor.execute('''
        CREATE TABLE IF NOT EXISTS PolicyTrees (
            id INTEGER PRIMARY KEY,
            policy TEXT,
            miniscript TEXT,
            sipa_cost INT,
            rust_miniscript TEXT,
            rust_cost INT,
            anonymized_miniscript TEXT
        )
    ''')
    master_conn.commit()

    # Find all worker databases (e.g., ending with .db in the specified directory).
    worker_dbs = glob.glob(os.path.join(worker_db_dir, "*.db"))
    print(f"Found {len(worker_dbs)} worker databases.")

    for worker_db in worker_dbs:
        print(f"Merging {worker_db}...")
        # Attach the worker database as a temporary alias.
        master_cursor.execute(f"ATTACH DATABASE '{worker_db}' AS worker_db")
        # Insert records from the worker database's PolicyTrees into the master database.
        master_cursor.execute('''
            INSERT OR IGNORE INTO PolicyTrees (policy, miniscript, sipa_cost, rust_miniscript, rust_cost, anonymized_miniscript)
            SELECT policy, miniscript, sipa_cost, rust_miniscript, rust_cost, anonymized_miniscript FROM worker_db.PolicyTrees
        ''')
        master_conn.commit()
        # Detach the worker database.
        master_cursor.execute("DETACH DATABASE worker_db")
    master_conn.close()
    print("Merging complete.")

        
    
if __name__ == "__main__":
    
    # Configuration parameters.
    sample_count = 1000
    num_iterations = 10
    num_workers = 10

    depth = 19
    grammar_file = "base.g4"
    miniscript_file = "../miniscript/miniscript"
    
    #prepareEnv(grammar_file)
    # Directory where each worker's DB file will be stored.
    output_dir = "./worker_outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    #generate_trees_parallel(sample_count, num_iterations, num_workers, depth, output_dir)
    
    master_database_path = "master_policy(x,5,19).db"
    #merge_worker_databases(master_database_path, output_dir)
    
    
    sqlite_callback = SqliteCallback(master_database_path)

    start = time.time()
    bucketing_worker = Bucketing()
    buckets = bucketing_worker.analyze(sqlite_callback)
    bucketing_worker.export_to_csv(buckets, f"report(x,5,19).csv")
    end = time.time()

    sqlite_callback.close()
    print(f"Time elapsed analyzing: {end-start}")

    

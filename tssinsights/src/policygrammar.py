import subprocess
import sqlite3
import queue
import cProfile

class PolicyGrammar():
    def __init__(self, id: int, samples: int, depth: int, name: str, miniscript_path: str) -> None:
        self.id = id
        self.process = None 
        self.input_queue = queue.Queue()
        self.running = False
        
        self.conn = sqlite3.connect(name)
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
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
        self.conn.commit()
        self.grammarinator_generate = f"unbuffer grammarinator-generate ThresholdPolicyGenerator.ThresholdPolicyGenerator -n {samples} --stdout -d {depth} | {miniscript_path}"
        self.counter = 0
                       
    def generate_policy_file(self, output_filename: str):
        """
        Runs the policy generation command and writes output to a file.
        """
        print("Starting policy generation...")
        with open(output_filename, 'w') as outfile:
            # Run the generation command and write its output to the file.
            subprocess.run(self.grammarinator_generate, shell=True, stdout=outfile, stderr=subprocess.STDOUT)
        print(f"Policy generation completed. Output saved to {output_filename}")

    def populate_db(self):
        self.cursor.execute("PRAGMA synchronous = OFF;")
        proc = subprocess.Popen(
            (self.grammarinator_generate),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        
        batch_size = 500
        batch_counter = 0
        self.cursor.execute("BEGIN TRANSACTION;")
        for line in proc.stdout: # type: ignore
            if line.startswith("X"):
                line_arr = line.split()
                policy = line_arr[-1]
                miniscript = line_arr[-2]
                sipa_cost = int(line_arr[2])
            else:
                policy = line.split()[-1][11:] # cut miniscript=
                miniscript = ""
                sipa_cost = 0
            
            batch_counter += 1
            self.counter += 1
            self.cursor.execute('''
            INSERT OR IGNORE INTO PolicyTrees (policy, miniscript, sipa_cost) VALUES (?, ?, ?)
            ''', (policy, miniscript, sipa_cost))

            if batch_counter % batch_size == 0:
                self.conn.commit()
                self.cursor.execute("BEGIN TRANSACTION;")
                print(f"Worker {self.id}: Processed a batch of {batch_counter} policies")

        self.conn.commit()  # Final commit for any remaining rows.
        proc.stdout.close() # type: ignore
        print(f"Worker {self.id}: Processed a total of {self.counter} policies")
 
    def populate_db_from_file(self, input_filename: str, batch_size: int = 1000):
        print("Starting DB population from file...")
        count = 0
        batch = []
        
        with open(input_filename, 'r') as infile:
            for line in infile:
                # Process each line to extract policy, miniscript, and cost.
                if line.startswith("X"):
                    line_arr = line.split()
                    policy = line_arr[-1]
                    miniscript = line_arr[-2]
                    sipa_cost = int(line_arr[2])
                else:
                    policy = line.split()[-1][11:]  # remove prefix "miniscript=" if present.
                    miniscript = ""
                    sipa_cost = 0
                
                batch.append((policy, miniscript, sipa_cost))
                count += 1
                
                # When batch is full, insert into DB
                if count % batch_size == 0:
                    self.cursor.executemany('''
                        INSERT OR IGNORE INTO PolicyTrees (policy, miniscript, sipa_cost)
                        VALUES (?, ?, ?)
                    ''', batch)
                    self.conn.commit()
                    batch = []
                    print(f"Inserted {count} records so far...")
        
        # Insert any remaining records
        if batch:
            self.cursor.executemany('''
                INSERT OR IGNORE INTO PolicyTrees (policy, miniscript, sipa_cost)
                VALUES (?, ?, ?)
            ''', batch)
            self.conn.commit()

        print(f"DB population complete. Processed a total of {count} policies.")

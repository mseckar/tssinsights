# from tssinsights.src.sqlitecallback import SqliteCallback
import re, csv

class Bucketing():
    
    def __init__(self) -> None:
        pass
    
    def anonymize(self, sqlitecallback):
        sqlitecallback.cursor.execute("SELECT id, miniscript FROM PolicyTrees")
        rows = sqlitecallback.cursor.fetchall()
        
        for row in rows:
            script_id, miniscript = row
            
            if miniscript is None:
                continue
            
            #Multi(x, anon *)
            anonymized = re.sub(r'multi\((\d+),([^)]+)\)', 
                                lambda m: f"multi({m.group(1)}, " + ", ".join(['anon'] * len(m.group(2).split(','))) + ")",
                                miniscript)
            #pk(anon), pk_h(anon) and pk_k(anon)
            anonymized = re.sub(r'pk\([^)]+\)', 'pk(anon)', anonymized)
            anonymized = re.sub(r'pk_h\([^)]+\)', 'pk_h(anon)', anonymized)
            anonymized = re.sub(r'pk_k\([^)]+\)', 'pk_k(anon)', anonymized)

            sqlitecallback.cursor.execute(
                "UPDATE PolicyTrees SET anonymized_miniscript = ? WHERE id = ?",
                (anonymized, script_id)
            )
        sqlitecallback.conn.commit()

    
    def analyze(self, sqlitecallback):
        
        self.anonymize(sqlitecallback)
        
        sqlitecallback.cursor.execute('''
        SELECT GROUP_CONCAT(policy), anonymized_miniscript, COUNT(*) as count, GROUP_CONCAT(miniscript) as miniscripts, GROUP_CONCAT(sipa_cost) as sipa_cost
        FROM PolicyTrees
        GROUP BY anonymized_miniscript
        HAVING count >= 1
        ORDER BY count DESC
        ''')
        
        return sqlitecallback.cursor.fetchall()

    def export_to_stdout(self, clusters):
        for cluster in clusters:
            print("Common Structure; Anonymized; Count; Miniscripts", "Sipa_cost")
            print(f"{cluster[0]}; {cluster[1]}; {cluster[2]}; {cluster[3]}")

    def export_to_csv(self, clusters, outfile: str = "exports/report.csv"):
        with open(outfile, 'w', newline='') as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["Common Structure", "Anonymized", "Count", "Miniscripts", "Sipa_cost"])
            writer.writerows(clusters)


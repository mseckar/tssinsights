# Grammarinator
Install the expect package and grammarinator or use the provided venv
```bash
pip install grammarinator
apt install expect
```
Process the grammar and generate the outputs (make sure the output folder is in the PYTHONPATH environment variable)
```bash
mkdir -p grammarinator_output; export PYTHONPATH=$(pwd)/grammarinator_output
grammarinator-process adjusted.g4 -o ./grammarinator_output --no-action
unbuffer grammarinator-generate ThresholdPolicyGenerator.ThresholdPolicyGenerator -n 10000 --stdout -d 10 > output.txt
```
10k in 6 sec
100k in 6 mins
200k in 14 mins
300k in 23 mins

214k in 13354s = 3.7h

100k (really 6k) in 5080.404547452927
35k (really 25.3k) in 1668.08 on 7 workers

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME  COMMAND                                                                                                                                                                                                             
48005 root      20   0  763812 759684   1484 R 100.0   2.3  15:40.47 miniscript                                                                                                                                                                                                          
48007 root      20   0 2801256   2.7g   1548 R 100.0   8.5  15:23.59 miniscript                                                                                                                                                                                                          
48019 root      20   0  696832 692764   1548 R 100.0   2.1  15:16.95 miniscript                                                                                                                                                                                                          
48020 root      20   0   21.5g  21.5g   1480 R 100.0  68.8  15:17.17 miniscript                                                                                                                                                                                                          
48022 root      20   0 1925496   1.8g   1560 R 100.0   5.9  15:42.13 miniscript                                                                                                                                                                                                          
32056 root      20   0  379.2g 133036  25136 S   5.6   0.4   4:53.98 node                                                                                                                                                                                                                
48341 root      20   0 2399416  11872   4460 S   1.7   0.0   0:14.45 grammarinator-g                                                                                                                                                                                                     
48079 root      20   0 2407612   7032   3588 S   1.0   0.0   0:17.89 grammarinator-g                                                                                                                                                                                                     
76816 root      20   0   11.3g  52304  19796 S   0.7   0.2   2:09.53 node                                                                                                                                                                                                                
48175 root      20   0   34820  22032   3984 S   0.3   0.1   0:00.82 grammarinator-g                                                                                                                                                                                                     
48357 root      20   0   34820  22528   4484 S   0.3   0.1   0:00.57 grammarinator-g                                                                                                                                                                                                     
48483 root      20   0   35076  22244   4144 S   0.3   0.1   0:00.45 grammarinator-g                                                                                                                                                                                                     
48529 root      20   0   35076  22328   4120 S   0.3   0.1   0:00.48 grammarinator-g                                                                                                                                                                                                     


7 workers, 30 rounds of 5k policies cca 20k policies in 3000s = 6.6 p/s
10 workers, 100 rounds of 1k policies cca 15k policies in 1878s = 7.9 p/s
one worker ca 6gb ram for miniscript

generation took ca 35 hours
merging took under 1 minute
bucketing took 157s

SELECT anonymized_miniscript, COUNT(*) as count, GROUP_CONCAT(policy), GROUP_CONCAT(miniscript) as miniscripts, GROUP_CONCAT(sipa_cost) as sipa_cost
        FROM PolicyTrees
        GROUP BY anonymized_miniscript
        HAVING count >= 1
        ORDER BY count DESC
        LIMIT 30
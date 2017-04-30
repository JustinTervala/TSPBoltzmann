This program solves the Travelling Salseman problem using a Boltzmann Machine. To see command line options, run 

    python tsp.py --help

A sample run might look like this:

    python tsp.py --penalty 500 --bonus 50 --temp 10000 --mintemp 1 --decay 0.99

which is equivalent to the following

    python tsp.py -p 500 -b 50 -t 10000 -m 1 -d 0.99
    
The output will be:

  jtervala@ubuntu:~/Documents/JHU/tsp$ python tsp.py --penalty 500 --bonus 50 --temp 10000 --mintemp 1 --decay 0.9999
  Using penalty:  500.0		bonus:  50.0
  starting temp.: 10000.0		min. temp.: 1.0		decay rate: 0.9999

  Execution required 1 attempt. 
       1   2   3   4   5
   A | - | O | - | - | - |
   B | - | - | O | - | - |
   C | - | - | - | - | O |
   D | O | - | - | - | - |
   E | - | - | - | O | - |


  Final Path:	D -> A -> B -> E -> C -> D		(Distance: 66)


If the -q option is chosen, the result will be:

  jtervala@ubuntu:~/Documents/JHU/tsp$ python tsp.py --penalty 500 --bonus 50 --temp 10000 --mintemp 1 --decay 0.9999 -q

  Final Path:	C -> E -> B -> A -> D -> C		(Distance: 66)

By default the program uses a JSON file named distances.json to get the distances between the city. This can be made as 
a triangular matrix (see the example distances.json for the format). By default the program also displays the status of
the net to a console. This can be disabled to greatly increase performance usng the -q option.


How the weights were determined:
Weights were used in such a way to inhibit invalid configurations of the program. As such weights between same cities in
different epochs as well as different cities in the same epoch were penalized with a value passed in by the --penalty
option in the command line. This penalty should be much larger than the maximum distance between two cities without 
being too large as to effectively "lock in" the first valid configuration of nodes found by the system. The weight from 
a node to itself was declared to be zero. The only distances considered were between nodes in adjacent epochs (only 
nodes in epoch+1 were considered), all other weights were assumed to be zero.

In addition to the penalty, a bonus was assigned to a node when it was activated. This allowed the concensus function to
be negative when nodes were activated. This allowed the system to gravitate away from a solution in which no nodes were 
enabled.  This bonus must be smaller than the penalty, and I found that it was best if it was roughtly as large as the 
maximum distance. 

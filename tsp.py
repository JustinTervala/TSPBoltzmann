import argparse
from copy import deepcopy
import math
import random
import sys
from time import sleep
try:
  import json
except ImportError:
  import simplejson as json


class Net(object):
  """
  Sets up a square net of boolean values.
  """
  def __init__(self, num_elements, labels):
    self.dim = num_elements
    self.size = self.dim * self.dim
    # nested list comprehension to efficiently construct a square array of dimention num_cities filled with random bools
    self.net = [[random.choice([True, False]) for _ in range(num_elements)] 
             for _ in range(num_elements)]  # just use _ for unused variable name
    self.labels = labels 
    self.header = '{0}{1}'.format(' '.ljust(7), ' '.ljust(3).join([str(epoch+1) for epoch in range(self.dim)]))
  
  def __iter__(self):
    """
    Simple generator to replace a bunch of nested for loops. 
    """
    for i in range(self.dim):
      for j in range(self.dim):
        yield i, j, self.net[i][j]
  
  def flip(self, i, j):
    self.net[i][j] = not self.net[i][j]
  
  def square_iter(self, start_row=0, start_col=0, end_row=None, end_col=None):
    """
    Simple generator to replace a bunch of nested for loops using arbirary starting points. 
    """
    for i in range(start_row, (end_row if end_row else self.dim)):
      for j in range(start_col, (end_col if end_col else self.dim)):
        yield i, j, self.net[i][j]
  
  def row_iter(self):
    """
    Simple generator to iterate over the rows
    """
    for row in self.net:
      yield row 
  
  def __str__(self):
    """
    String representation overload.
    """
    # I know the oneliners ake this a bit impeneratrable, but it works.
    def condense_list(index, list_in):
      return '{0} | {1} |'.format(self.labels[index][:4].rjust(4), 
                                  ' | '.join([('O' if x else '-') for x in list_in]))
    table = '\n'.join([condense_list(i, x) for i, x in enumerate(self.net)])
    return '{0}\n{1}\n'.format(self.header, table)
  
  def __getitem__(self, pos):
    return self.net[pos[0]][pos[1]]
    
  def num_enabled(self):
    return sum(x for _, _, x in self.__iter__() if x)


class BoltzmannTsp(object):
  """
  Class which encapsulates solving the Travelling Salesman problem with a Boltzmann Machine
  """
    
  def __init__(self, penalty, bonus, distances_filename, quiet=False):
    self.import_distances(distances_filename)
    self.penalty = penalty
    self.bonus = bonus
    self.quiet = quiet
    self.net = Net(self.num_cities, self.cities)
    if not self.quiet:
      print('Using penalty:  {0}\t\tbonus:  {1}'.format(self.penalty, self.bonus))
    self.calculate_concensus()
    self.min_net = self.net
    
    
  def import_distances(self, filename):
    """
    Imports the distances from the given distances JSON file
    """
    with open(filename, 'r') as distances_file:
      self.distances = json.loads(distances_file.read())
    # We expect not all distances to be intiialized (like a triangular matrix), 
    # so we will fill out the rest of the entry
    self.cities = self.distances.keys()
    self.cities.sort()
    for city in self.cities:
      for city_entry, distance_entry in self.distances.items():
        if city not in distance_entry and city != city_entry:
          self.distances[city_entry][city] = self.distances[city][city_entry]
    self.num_cities = len(self.cities)
    self.index_city_map = {index: city for index, city in enumerate(self.cities)} 
    
  def reset(self):
    """
    Resets the network to randomly-initialized values
    """
    self.net = [[random.choice([True, False]) for _ in range(self.num_cities)] 
                 for _ in range(self.num_cities)]  # just use _ for unused variable name
    self.calculate_concensus()
  
  def calculate_concensus(self):
    """
    Calculates the concensus of the net
    """
    weight_term, bias_term = 0., 0.
    for start_city, start_epoch, start_net_element in self.net:
      if start_net_element:  # The following computations require starting_net_element to be True. (Saves some extra computations steps)
        bias_term += self.bonus  # Add a constant if the element is enabled. 
        
        for end_city, end_epoch, end_net_element in self.net.square_iter(start_col=start_epoch):
          weight = self.calculate_weight(start_city, start_epoch, end_city, end_epoch)
          weight_term += weight * start_net_element * end_net_element
    self.concensus = weight_term - bias_term 
                    
  def find_optimal_path(self, temp, min_temp=100, decay_rate=0.95, max_attempts=10):
    """
    Primary entry point of the class. Solves teh travelling salesman problem.
    """
    if not self.quiet:
      print('starting temp.: {0}\t\tmin. temp.: {1}\t\tdecay rate: {2}'.format(temp, min_temp, decay_rate))
    self.__find_optimal_path(temp, min_temp, decay_rate)
    count = 1
    # This is a hacky way of continuing the process if the best-found solution is not valid
    while not self.is_valid_path() and count <= max_attempts:
      self.__find_optimal_path(temp, min_temp, decay_rate)
      count += 1
    if not self.quiet:
      print('\nExecution required {0} attempt{1}. {2}\n{3}'.format(count, 
                                                                   's' if count > 1 else '', 
                                                                   'Try changing some parameters' if count > 1 else '', 
                                                                   self.net))
                                                                   
  def __find_optimal_path(self, temp, min_temp, decay_rate):
    min_concensus = self.concensus
    while temp >= min_temp:
      if not self.quiet:
        print('')
        sys.stdout.write('{0}\n\nTemp:  {1}\t\tConcensus:  {2}\t(min. {3})\n'.format(self.net, temp, self.concensus, min_concensus))
      
      city, epoch = self.pick_random_net_indices()  # pick a random value
      pre_candidate = self.concensus  # store the current value of the consensus
      self.net.flip(city, epoch)
      self.calculate_concensus()  # recalculate the concensus
      delta_concensus = self.concensus - pre_candidate
      
      if not BoltzmannTsp.accept_change(delta_concensus, temp):  # if we do not accept change, revert to previous state
        self.concensus = pre_candidate
        self.net.flip(city, epoch)
      temp *= decay_rate  # Reduce the temp by a constant factor
      
      if not self.quiet:
        self.erase_net()
        sleep(0.003)  # needed so the display is stable (it still isn't fully stable, but I don't want to sleep longer)

      if self.concensus < min_concensus:
        min_concensus = self.concensus
        self.min_net = deepcopy(self.net)  # deep copy the net to avoid mutability issues
    
    self.net = self.min_net

  def calculate_weight(self, start_city, start_epoch, end_city, end_epoch):
    """
    Calculates the weight between two nodes
    """
    if start_city == end_city:
      return self.penalty if start_epoch != end_epoch else 0  # there is a penalty for same city at different epochs unless nodes are the same
    elif start_epoch == end_epoch:
      return self.penalty  # There is a penalty for different city at the same epochs
    elif end_epoch == start_epoch + 1:  # We only need to compare one epoch with the next epoch for the weights
      return self.lookup_weight(start_city, end_city)  # Properly look up the weight
    else:
      return 0  # Default 
        
  def calculate_concensus_change(self, city, epoch):
    """
    Currently unusued. Should be able to use it instead of recalculating the whole concensus. Still can't get it to work
    """
    change = (not self.net[city][epoch]) - self.net[city][epoch]
    weight_sum = 0
    for start_city, start_epoch, start_element in self.net:
      if start_element:
        weight_sum += self.calculate_weight(start_city, start_epoch, city, epoch) * start_element
    return change * (weight_sum - self.bonus) 
        
  @staticmethod
  def accept_change(concensus_change, temp):
    """
    Determines if you should accept the change or not
    """
    try:
      return random.random() <= (1. / (1. + math.exp(concensus_change/temp)))
    except OverflowError:
      return False
        
  def pick_random_net_indices(self):
    """
    Nice one-liner to use divmod to return a tuple of (result, remainder) from a random int between 0 and num_cities^2-1
    divided by the number of cities
    """
    return divmod(random.randint(0, self.num_cities * self.num_cities - 1), self.num_cities)
        
  def lookup_weight(self, start_city, end_city):
    """
    Looks up the distance between two weights using indices. Converts indices to named cities to use with distance dict
    """
    return self.distances[self.index_city_map[start_city]][self.index_city_map[end_city]]
    
  def is_valid_path(self):
    """
    One-liner to determine if the net is valid. 
    """
    return (self.net.num_enabled() == self.num_cities  # assert total number of nodes enabled is correct
            and all(True in city for city in self.min_net.row_iter()))  # asserts each city is enabled in some epoch
    
  def determine_path(self):
    """
    Extracts a path as a list from the net
    """
    city_epoch_dict = {}
    for i, city in enumerate(self.net.row_iter()):
      epoch = city.index(True)
      city_epoch_dict[self.index_city_map[i]] = epoch
    # switch key-value pairs
    epoch_city_dict = {value: key for key, value in city_epoch_dict.items()}
    path = [epoch_city_dict[i] for i in range(self.num_cities)]
    path.append(path[0])
    return path
  
  def calculate_path_length(self, path=''):
    """
    Calculates the length of a path using the distances
    """
    return sum(self.distances[path[i]][path[i+1]] for i in range(len(path)-1))

  def net_to_str(self, status=''):
    """
    String representation of the net. I know it looks bad with my oneliners everywhere, but it works.
    """
    return '{0}\n{1}\n{2}'.format(header, self.net, status) 
  
  def erase_net(self):
    """
    Use ASCII escape sequences to replace the strings on the screen
    """
    sys.stdout.write("\033[F")
    for _ in range(self.num_cities+4):
      sys.stdout.write("\r\033[K\033[F")
     
     
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Solution to the Travelling Salesman problem using a Boltzmann Machine',
                                     add_help=True)
    parser.add_argument('-f', '--file', help='Distances JSON input file', default='distances.json') 
    parser.add_argument('-p', '--penalty', type=float, help='Penalty associated with violating constraints.') 
    parser.add_argument('-b', '--bonus', type=float, help='Bonus associated with visiting a node (to prevent not moving)')
    parser.add_argument('-t', '--temp', type=float, help='Initial temperature')
    parser.add_argument('-m', '--mintemp', type=float, help='Minimum temperature')
    parser.add_argument('-d', '--decay', type=float, help='Temperature decay rate', default=0.999)
    parser.add_argument('-i', '--maxiter', type=int, help='Maximum iterations', default=10)
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet the output (greatly improves performance)')
 
    args = parser.parse_args()
    assert args.bonus < args.penalty  # Bonsu should be less than penalty or the results won't converge
    tsp = BoltzmannTsp(args.penalty, args.bonus, args.file, quiet=args.quiet)
    tsp.find_optimal_path(args.temp, min_temp=args.mintemp, decay_rate=args.decay)
    path = tsp.determine_path()
    print('\nFinal Path:\t{0}\t\t(Distance: {1})\n'.format(' -> '.join(path), tsp.calculate_path_length(path)))

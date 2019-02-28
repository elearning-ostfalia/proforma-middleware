# Info: dies ist der erste (denkbare) Schritt zu einem Lasttest
# 
# 'start' erlaubt das Erzeugen von ganz vielen Threads, die
# parallel abarbeitet (je nachdem, wieviele paralelle Threads 
# möglich sind)

from multiprocessing.dummy import Pool, TimeoutError
import time

max_parallel_threads = 20
number_of_tasks = max_parallel_threads * 10

def my_function(x):
    starting_time = time.clock()    
    print str(x) + ' S'
    time.sleep(0.5)
    print str(x) + ' E'
    ending_time = time.clock()
    elapsed_microseconds = ending_time - starting_time    
    return elapsed_microseconds # x*x

def start():
    pool = Pool(max_parallel_threads)
    
    # results = pool.map(service, tasks)
    results = pool.map(my_function, range(number_of_tasks))
    print 'map started'
    
    # results = pool.map(f, [1, 2, 3, 4, 5, 6, 7])
    pool.close()
    print 'map closed'
    pool.join()
    print results
    print 'finished'


def f(x):
    return x*x

def start1():
    pool = Pool(processes=4)              # start 4 worker processes

    # print "[0, 1, 4,..., 81]"
    print "[0, 1, 4,..., 81]"
    print pool.map(f, range(10))

    print "same numbers in arbitrary order"
    for i in pool.imap_unordered(f, range(10)):
        print i

    print "evaluate f(20) asynchronously"
    res = pool.apply_async(f, (20,))      # runs in *only* one process
    print res.get(timeout=1)              # prints "400"

    # evaluate "os.getpid()" asynchronously
    #res = pool.apply_async(os.getpid, ()) # runs in *only* one process
    #print res.get(timeout=1)              # prints the PID of that process

    # launching multiple evaluations asynchronously *may* use more processes
    #multiple_results = [pool.apply_async(os.getpid, ()) for i in range(4)]
    #print [res.get(timeout=1) for res in multiple_results]

    print "make a single worker sleep for 10 secs"
    res = pool.apply_async(time.sleep, (10,))
    try:
        print res.get(timeout=5)
    except TimeoutError:
        print "We lacked patience and got a multiprocessing.TimeoutError"

start()

grammar ThresholdPolicyTimelocks;

@members {
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.timeLockStack = []
    self.hasTimeLock = False

def pushTimeLock(self):
    self.timeLockStack.append(self.hasTimeLock)
    self.hasTimeLock = False

def popTimeLock(self):
    self.hasTimeLock = self.timeLockStack.pop()
}


policy : {self.hasTimeLock = False} nonLeaf EOF ;
nonLeaf : thresh1 | thresh2 | thresh3 | thresh4 | thresh5 ;
node : 
    leaf | 
    {not self.hasTimeLock}? older | 
    {not self.hasTimeLock}? after | 
    {self.pushTimeLock()} nonLeaf {self.popTimeLock()} ; // Push a temporary flag level

node_no_timelock:
    leaf |
    {self.pushTimeLock()} nonLeaf {self.popTimeLock()} ;

leaf : 'pk(' ID ')' ;

//Time Locks
older : 'older(' TIME ')' {self.hasTimeLock = True} ;
after : 'after(' TIME ')' {self.hasTimeLock = True} ;

thresh1 : 'thresh(1,' node_no_timelock (',' node)+ ')' ; // Excludes the timelock and thresh(1, pk()) degenerate cases
thresh2 : 'thresh(2,' node (',' node)+ ')' ;
thresh3 : 'thresh(3,' node ',' node (',' node)+ ')' ;
thresh4 : 'thresh(4,' node ',' node ',' node (',' node)+ ')' ;
thresh5 : 'thresh(5,' node ',' node ',' node ',' node (',' node)+ ')' ;

ID : [a-zA-Z0-9] [a-zA-Z0-9] [a-zA-Z0-9] ;
//TIME : [0-5] [0-9] ;
TIME : [1-9] ;

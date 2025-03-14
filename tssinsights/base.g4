grammar ThresholdPolicy;

policy : nonLeaf EOF;
nonLeaf : thresh1 | thresh2 | thresh3 | thresh4 | thresh5;
node : leaf | nonLeaf;

leaf : 'pk(' ID ')' ;

thresh1 : 'thresh(1,' nodeList2 ')' ;  //Excludes the degenerate case
thresh2 : 'thresh(2,' nodeList2 ')' ;
thresh3 : 'thresh(3,' nodeList3 ')' ;
thresh4 : 'thresh(4,' nodeList4 ')' ;
thresh5 : 'thresh(5,' nodeList5 ')' ;

nodeList2 : node ',' node (',' node)* ;
nodeList3 : node ',' node ',' node (',' node)* ;
nodeList4 : node ',' node ',' node ',' node (',' node)* ;
nodeList5 : node ',' node ',' node ',' node ',' node (',' node)* ;

ID : [a-zA-Z0-9] [a-zA-Z0-9] [a-zA-Z0-9] ;

"""Deterministic audit fixtures for Candidate B execution semantics. No exchange access."""
from feature_walkforward import sim
from analyze_mtf_5y import aggregate,HOUR

CFG=("turn","none","none",2.5,6.,12,"both")
def bars(n=230):
    return [(i*4*HOUR,100.,101.,99.,100.) for i in range(n)]
def feats(n=230):
    f=[None]*n
    f[211]={"turn":True,"side":1,"atr":2.}
    return f
def test_next_open_entry():
    r=bars(); f=feats()
    r[211]=(r[211][0],100.,100.,1.,100.) # extreme signal candle low must NOT trigger stop
    r[212]=(r[212][0],110.,111.,109.,110.)
    r[213]=(r[213][0],110.,111.,104.,105.) # entry 110, stop 105
    t,_=sim(r,f,CFG,0,len(r))
    assert len(t)==1,(t,_)
    assert abs(t[0][1]-((105/110-1)-.0015))<1e-9,t
def test_stop_wins_same_bar():
    r=bars();f=feats()
    r[212]=(r[212][0],100.,120.,90.,110.)
    t,_=sim(r,f,CFG,0,len(r))
    assert len(t)==1 and abs(t[0][1]-(-.05-.0015))<1e-9,t
def test_4h_boundary():
    r=[(i*HOUR,100.,101.,99.,100.) for i in range(12)]
    a=aggregate(r,4)
    assert len(a)==2, a # conservative aggregate() drops final bucket
    assert [x[0] for x in a]==[0,4*HOUR],a
def test_split_entry_boundary():
    r=bars();f=feats()
    t,_=sim(r,f,CFG,0,212)
    assert not t,t
if __name__=="__main__":
    for t in (test_next_open_entry,test_stop_wins_same_bar,test_4h_boundary,test_split_entry_boundary):
        t();print("PASS",t.__name__)

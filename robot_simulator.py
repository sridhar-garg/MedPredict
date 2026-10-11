"""Deterministic grid-world, A* mobile robot dispatch and controlled benchmarks.

Triage scores, patients, robot movements and obstacles are ALL SIMULATED.
No actual patient risk inference, navigation hardware or clinical decision support.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
import heapq
import math
import numpy as np

SIZE=(18,12)
Point=tuple[int,int]


def obstacles(extra=()):
    points=set()
    for x in range(3,15):
        if x not in (5,12):points.add((x,4))
    for y in range(6,11):
        if y != 8:points.add((9,y))
    return points | set(extra)


def astar(start:Point, target:Point, blocked, size=SIZE):
    if start in blocked or target in blocked:return None
    q=[(abs(start[0]-target[0])+abs(start[1]-target[1]),0,start)]
    parent={}; best={start:0}
    while q:
        _,cost,pos=heapq.heappop(q)
        if cost>best[pos]:continue
        if pos==target:
            path=[pos]
            while path[-1]!=start:path.append(parent[path[-1]])
            return path[::-1]
        for n in [(pos[0]+1,pos[1]),(pos[0]-1,pos[1]),(pos[0],pos[1]+1),(pos[0],pos[1]-1)]:
            if not(0<=n[0]<size[0] and 0<=n[1]<size[1]) or n in blocked:continue
            g=cost+1
            if g<best.get(n,math.inf):
                best[n]=g;parent[n]=pos
                h=abs(n[0]-target[0])+abs(n[1]-target[1])
                heapq.heappush(q,(g+h,g,n))
    return None


@dataclass(frozen=True)
class PatientTask:
    uid:int
    xy:Point
    visible_priority:float
    uncertainty:float
    simulation_urgent:bool


def make_scenario(seed=13, n=9, extra=()):
    rng=np.random.default_rng(seed)
    blocked=obstacles(extra)
    starts=((0,0),(17,11))
    open_spots=[(x,y) for x in range(1,SIZE[0]-1) for y in range(1,SIZE[1]-1)
                if (x,y) not in blocked and (x,y) not in starts]
    idx=rng.choice(len(open_spots),size=n,replace=False)
    tasks=[]
    for uid,i in enumerate(idx):
        truth=bool(rng.random()<.38)
        noisy=float(np.clip((.82 if truth else .19)+rng.normal(0,.19),.03,.97))
        uncertainty=float(np.clip(rng.beta(2.,4.),0.,1.))
        tasks.append(PatientTask(uid,open_spots[i],noisy,uncertainty,truth))
    return starts,blocked,tasks


def run_dispatch(seed=13, strategy='carebot', robots=2, extra=(), robot_failure=False):
    if strategy not in ('carebot','nearest') or robots not in (1,2):raise ValueError('Invalid scenario config')
    start, blocked, tasks=make_scenario(seed,extra=extra)
    loc=list(start[:robots]);time=[0.]*robots
    pending=list(tasks);events=[];paths=[]
    while pending:
        possible=[]
        for ri in range(robots):
            if robot_failure and ri==0 and len(events)>=2:continue
            for t in pending:
                route=astar(loc[ri],t.xy,blocked)
                if route is None:continue
                travel=len(route)-1
                if strategy=='nearest':
                    merit=(-travel-time[ri],-ri,-t.uid)
                else:


                    weight=1+5*t.visible_priority+1.2*t.uncertainty
                    merit=(weight/(1+travel+.28*time[ri]),-time[ri],-t.uid)
                possible.append((merit,ri,t,route,travel))
        if not possible:break
        _,ri,t,route,travel=max(possible,key=lambda v:v[0])
        arrival=time[ri]+travel
        time[ri]=arrival+2
        loc[ri]=t.xy
        pending.remove(t)
        paths.append({'robot':ri,'patient':t.uid,'path':route})
        events.append({'patient':t.uid,'robot':ri,'priority_proxy':round(t.visible_priority,3),
                       'uncertainty':round(t.uncertainty,3),
                       'synthetic_urgent':t.simulation_urgent,
                       'arrival_minutes':arrival,'travel_steps':travel,
                       'xy':t.xy})
    if not events:raise ValueError('No reachable tasks')
    urgent=[e['arrival_minutes'] for e in events if e['synthetic_urgent']]
    weighted=sum(e['arrival_minutes']*(1+5*e['priority_proxy']) for e in events)/sum(1+5*e['priority_proxy'] for e in events)
    return {'events':events,'paths':paths,'obstacles':sorted(blocked),
      'patient_tasks':tasks,'robot_starts':start[:robots],
      'metrics':{'seen':len(events),'total_tasks':len(tasks),
                 'total_travel_steps':sum(e['travel_steps'] for e in events),
                 'mean_urgent_response_minutes':round(float(np.mean(urgent)),2) if urgent else None,
                 'mean_priority_weighted_response_minutes':round(float(weighted),2),
                 'finish_minutes':round(max(time),2)}}


@lru_cache(maxsize=15)
def benchmark(num_scenarios=40, first_seed=17, robots=2, robot_failure=False):
    if not 10<=num_scenarios<=100:raise ValueError('10–100 scenarios')
    cases=[]
    for seed in range(first_seed,first_seed+num_scenarios):
        a=run_dispatch(seed,'nearest',robots,robot_failure=robot_failure)
        b=run_dispatch(seed,'carebot',robots,robot_failure=robot_failure)
        cases.append({'seed':seed,**{f'{prefix}_{k}':v for prefix,r in [('baseline',a),('carebot',b)] for k,v in r['metrics'].items()}})
    keys=['mean_urgent_response_minutes','mean_priority_weighted_response_minutes',
          'total_travel_steps','finish_minutes']
    out={'n_scenarios':num_scenarios,'num_robots':robots,'robot_failure':robot_failure,
         'note':'All patient urgency and travel times are simulated; scores are not clinical validity evidence',
         'mean_metrics':{},'cases':cases}
    for k in keys:
        vals=[]
        for col in ['baseline','carebot']:
            arr=[c[f'{col}_{k}'] for c in cases if c[f'{col}_{k}'] is not None]
            vals.append(round(float(np.mean(arr)),3) if arr else None)
        out['mean_metrics'][k]={'nearest_first':vals[0],'risk_uncertainty_aware':vals[1]}
    return out

if __name__=='__main__':
    import json
    x=benchmark()
    print(json.dumps({k:v for k,v in x.items() if k!='cases'},indent=2))

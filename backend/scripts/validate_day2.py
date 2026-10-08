"""Day 2 offline validation on 200 synthetic candidates."""
from __future__ import annotations
import json, math, random
from pathlib import Path

from app.domain.irt import probability, fisher_information, estimate_theta, grade_for_theta
from app.domain.items.templates.numeric import generate

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data"/"validation"
OUT.mkdir(parents=True,exist_ok=True)

SPECS=["backend","frontend","mobile","data","devops","qa"]
GRADES={"junior":-1.2,"middle":0.1,"senior":1.15,"lead":2.25}

TASK_FAMILIES = {
    "backend": ["algorithms", "sql", "api", "concurrency", "cache"],
    "frontend": ["js_ts", "browser", "layout", "state", "http"],
    "mobile": ["lifecycle", "async", "storage", "battery", "mobile_networking"],
    "data": ["sql_analytics", "statistics", "classification", "pipeline", "quality"],
    "devops": ["linux", "devops_networking", "cicd", "containers", "observability"],
    "qa": ["boundaries", "pairwise", "api_assertions", "requirements", "automation"],
}

def make_pool(spec):
    pool=[]
    for grade,b0 in GRADES.items():
        for family_index, family in enumerate(TASK_FAMILIES[spec]):
            for v in range(6):
                global_v = family_index * 6 + v
                a=round(2.0+(global_v%10)*0.12,3)
                b=round(b0+(global_v-14)*0.025,3)
                code=f"{spec}_{family}_v{v:02d}_{grade}"
                pool.append((code,a,b))
    return pool

def run_cat(theta_true, pool, seed):
    rng=random.Random(seed)
    theta=0.0
    answered=[]
    remaining=pool[:]
    for step in range(15):
        code,a,b=max(remaining,key=lambda x:fisher_information(theta,x[1],x[2]))
        remaining=[x for x in remaining if x[0]!=code]
        p=probability(theta_true,a,b)
        u=int(rng.random()<p)
        answered.append((u,a,b))
        theta=estimate_theta(answered,theta).theta
        se=estimate_theta(answered,theta).se
        if step+1>=8 and se<0.3:
            break
    state=estimate_theta(answered,theta)
    return state.theta,state.se,grade_for_theta(state.theta),len(answered)

def corr(xs,ys):
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    num=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    den=math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
    return num/den if den else 0.0

def main():
    rng=random.Random(20261007)
    source = ROOT/"data"/"synthetic"/"candidates.json"
    if source.exists():
        candidates=json.loads(source.read_text(encoding="utf-8"))[:200]
    else:
        candidates=[{"theta":max(-2.5,min(3.0,rng.gauss(0,1.25))),"specialization":SPECS[i%len(SPECS)]} for i in range(200)]
    rows=[]
    for i,candidate in enumerate(candidates):
        true_theta=float(candidate["theta"])
        spec=str(candidate["specialization"])
        pool=make_pool(spec)
        r1=run_cat(true_theta,pool,100000+i)
        # Different form: reverse the deterministic tie ordering by shuffling pool.
        pool2=pool[:]
        random.Random(200000+i).shuffle(pool2)
        r2=run_cat(true_theta,pool2,300000+i)
        rows.append({"true_theta":true_theta,"run1":r1,"run2":r2})
    t=[r["true_theta"] for r in rows]
    x=[r["run1"][0] for r in rows]
    y=[r["run2"][0] for r in rows]
    rmse=math.sqrt(sum((a-b)**2 for a,b in zip(t,x))/len(t))
    report={
        "n_candidates":200,
        "test_retest_correlation":corr(x,y),
        "grade_agreement":sum(r["run1"][2]==r["run2"][2] for r in rows)/len(rows),
        "rmse_theta":rmse,
        "mean_items_run1":sum(r["run1"][3] for r in rows)/len(rows),
        "mean_items_run2":sum(r["run2"][3] for r in rows)/len(rows),
        "goals":{"correlation":0.85,"grade_agreement":0.80,"rmse":0.35},
    }
    (OUT/"day2_test_retest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()

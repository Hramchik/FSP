import csv, json, random
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"data"/"synthetic"; LAB=ROOT/"data"/"labels"; OUT.mkdir(parents=True,exist_ok=True); LAB.mkdir(parents=True,exist_ok=True)
r=random.Random(20261006)
specs=["backend","frontend","mobile","data","devops","qa"]; grades=["junior","middle","senior","lead"]
skills={"backend":["python","go","postgresql","sql","api-design"],"frontend":["typescript","javascript","react"],"mobile":["java","typescript","sql"],"data":["python","sql","statistics","pytorch"],"devops":["linux","docker","kubernetes","ci-cd"],"qa":["python","pytest","sql"]}
events=["Региональный чемпионат ФСП","Всероссийский чемпионат ФСП","Студенческий кубок ФСП"]
level=["regional","national","student"]
cs=[]
for i in range(200):
    theta=max(-2.5,min(3.0,r.gauss(0,1.25))); spec=r.choice(specs)
    cs.append({"id":i+1,"pseudo":f"A-{1000+i:04d}","theta":round(theta,4),"specialization":spec,"skills":r.sample(skills[spec],k=min(len(skills[spec]),r.randint(2,len(skills[spec])))),"fsp":i<120,"city":r.choice(["Berlin","Moscow","Saint Petersburg","Kazan","Yekaterinburg"]),"years_experience":max(0,round(theta+2+r.random()*2,1))})
json.dump(cs,open(OUT/"candidates.json","w",encoding="utf8"),ensure_ascii=False,indent=2)
v=[]
for i in range(30):
    spec=r.choice(specs); grade=r.choice(grades); req=r.sample(skills[spec],k=min(3,len(skills[spec])))
    v.append({"id":i+1,"title":f"{spec.title()} {grade} engineer #{i+1}","specialization":spec,"grade":grade,"skills":req,"description":f"Нужен специалист {spec}, уровень {grade}. Стек: {', '.join(req)}."})
json.dump(v,open(OUT/"vacancies.json","w",encoding="utf8"),ensure_ascii=False,indent=2)
with open(LAB/"relevance_labels.csv","w",newline="",encoding="utf8") as f:
    w=csv.writer(f); w.writerow(["vacancy_id","candidate_id","annotator_a","annotator_b","adjudicated"])
    for vac in v:
        pool=[c for c in cs if c["specialization"]==vac["specialization"]]; pool=r.sample(pool,k=min(20,len(pool)))
        for c in pool:
            base=2 if (c["theta"]>=-0.5 and c["specialization"]==vac["specialization"] and set(vac["skills"]).intersection(c["skills"])) else (1 if c["specialization"]==vac["specialization"] else 0)
            a=max(0,min(2,base+r.choice([-1,0,0,0,1]))); b=max(0,min(2,base+r.choice([-1,0,0,0,1]))); adj=round((a+b)/2)
            w.writerow([vac["id"],c["id"],a,b,adj])
print(f"generated {len(cs)} candidates, {len(v)} vacancies, {sum(1 for _ in open(LAB/'relevance_labels.csv',encoding='utf8'))-1} labels")

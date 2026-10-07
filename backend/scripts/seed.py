import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import Specialization, Category, Skill, SkillAlias, User, CandidateProfile, EmployerProfile, UserRole
from app.core.security import hash_password

SPECS={"backend":"Бэкенд-разработка","frontend":"Фронтенд-разработка","mobile":"Мобильная разработка","data":"Данные и ML","devops":"DevOps и инфраструктура","qa":"Тестирование"}
GRADES=[("junior",None,-0.5),("middle",-0.5,0.7),("senior",0.7,1.8),("lead",1.8,None)]
SKILLS=["python","go","java","typescript","javascript","react","postgresql","sql","docker","kubernetes","linux","ci-cd","statistics","pytorch","pytest","api-design"]
ALIASES={"golang":"go","postgres":"postgresql","postgresql":"postgresql","ts":"typescript","js":"javascript"}
async def main():
 async with SessionLocal() as db:
  if not await db.scalar(select(Specialization).limit(1)):
   specs={}
   for code,name in SPECS.items():
    s=Specialization(code=code,name=name); db.add(s); await db.flush(); specs[code]=s
    for grade,lo,hi in GRADES: db.add(Category(specialization_id=s.id,grade=grade,theta_min=lo,theta_max=hi))
   skills={}
   for code in SKILLS: sk=Skill(code=code,name=code); db.add(sk); await db.flush(); skills[code]=sk
   for alias,code in ALIASES.items(): db.add(SkillAlias(skill_id=skills[code].id,alias=alias))
  if not await db.scalar(select(User).where(User.email=="demo.candidate@fsp.local")):
   u=User(email="demo.candidate@fsp.local",password_hash=hash_password("DemoPass123!"),role=UserRole.candidate,is_email_verified=True); db.add(u); await db.flush(); db.add(CandidateProfile(user_id=u.id,display_name="Demo Candidate",city="Berlin",is_searchable=True))
  if not await db.scalar(select(User).where(User.email=="demo.employer@fsp.local")):
   u=User(email="demo.employer@fsp.local",password_hash=hash_password("DemoPass123!"),role=UserRole.employer,is_email_verified=True); db.add(u); await db.flush(); db.add(EmployerProfile(user_id=u.id,company_name="FSP Demo Tech",description="Demo employer",contact="hr@fsp.local"))
  await db.commit()
asyncio.run(main())

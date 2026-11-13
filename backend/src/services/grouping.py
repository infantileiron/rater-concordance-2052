from itertools import combinations
from src.services.cohort import UNGROUPED
from src.services.kendall import kendall_w
from src.services.kappa import weighted_kappa

def _kappa_pairs(matrix,raters):
 pairs=[]
 for i,j in combinations(range(len(raters)),2):
  pairs.append({"rater_a":raters[i],"rater_b":raters[j],**weighted_kappa([r[i] for r in matrix],[r[j] for r in matrix])})
 return pairs

def _mean_kappa(pairs):
 estimates=[p["kappa"] for p in pairs if p["kappa"] is not None]
 return (sum(estimates)/len(estimates) if estimates else None),len(estimates)

def _group_block(name,entries,isolated,raters):
 matrix=[t["positions"] for t in entries]
 pairs=_kappa_pairs(matrix,raters)
 w=kendall_w(matrix,raters)
 mean,n_estimable=_mean_kappa(pairs)
 return {"group":name,"tasks_total":len(entries)+len(isolated),"tasks_complete":len(entries),"tasks_isolated":len(isolated),
  "isolated":isolated,"kendall":w,"pairs":pairs,"estimable_pairs":n_estimable,"mean_pair_kappa":mean,
  "rank_profile":[{"task_id":t["task_id"],"ranks":w["ranks"][i]} for i,t in enumerate(entries)] if w["ranks"] else [],
  "note":"组内以该组共同完整任务重新排名，并列校正与五级二次权重口径与总体一致；不以分组系数均值替代总体。"
   +("" if len(entries)>=2 else " 该组完整任务少于2，W与kappa均不可估计。")}

def build_groups(complete,isolated,raters,overall_pairs,tasks_total,complete_total,isolated_total):
 order=[];buckets={};iso_buckets={}
 for t in complete:
  if t["group"] not in buckets:order.append(t["group"]);buckets[t["group"]]=[];iso_buckets[t["group"]]=[]
  buckets[t["group"]].append(t)
 for t in isolated:
  if t["group"] not in buckets:order.append(t["group"]);buckets[t["group"]]=[];iso_buckets[t["group"]]=[]
  iso_buckets[t["group"]].append(t)
 groups=[_group_block(name,buckets[name],iso_buckets[name],raters) for name in order]
 # 勾稽：各组完整数、隔离数与原始任务数合回总体
 sum_complete=sum(g["tasks_complete"] for g in groups);sum_isolated=sum(g["tasks_isolated"] for g in groups);sum_total=sum(g["tasks_total"] for g in groups)
 reconciliation={"group_count":len(groups),"ungrouped_present":UNGROUPED in order,
  "groups_complete_sum":sum_complete,"overall_complete":complete_total,"complete_matches":sum_complete==complete_total,
  "groups_isolated_sum":sum_isolated,"overall_isolated":isolated_total,"isolated_matches":sum_isolated==isolated_total,
  "groups_total_sum":sum_total,"overall_total":tasks_total,"total_matches":sum_total==tasks_total,
  "checks":[]}
 # 勾稽：每对评委的5x5混淆计数，跨组逐格相加等于总体
 pair_index={(p["rater_a"],p["rater_b"]):p for p in overall_pairs};confusion_matches=True;confusion_checked=0
 for key,op in pair_index.items():
  acc=[[0]*5 for _ in range(5)]
  for g in groups:
   gp=next((p for p in g["pairs"] if (p["rater_a"],p["rater_b"])==key),None)
   if gp:
    for i in range(5):
     for j in range(5):acc[i][j]+=gp["matrix"][i][j]
  ok=acc==op["matrix"];confusion_matches=confusion_matches and ok;confusion_checked+=1
  reconciliation["checks"].append({"rater_a":key[0],"rater_b":key[1],"matrix_matches":ok,"overall_n":op["n"],"groups_n_sum":sum(map(sum,acc))})
 reconciliation["confusion_pair_count"]=confusion_checked
 reconciliation["confusion_matches"]=confusion_matches
 reconciliation["all_match"]=reconciliation["complete_matches"] and reconciliation["isolated_matches"] and reconciliation["total_matches"] and confusion_matches
 return groups,reconciliation

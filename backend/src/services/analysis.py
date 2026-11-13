from itertools import combinations
import hashlib,json,math
from src.services.cohort import prepare
from src.services.grouping import build_groups
from src.services.kendall import kendall_w
from src.services.kappa import weighted_kappa
def analyze(tasks,raters,levels):
 complete,isolated=prepare(tasks,raters,levels);matrix=[t["positions"] for t in complete];pairs=[]
 for i,j in combinations(range(len(raters)),2):pairs.append({"rater_a":raters[i],"rater_b":raters[j],**weighted_kappa([r[i] for r in matrix],[r[j] for r in matrix])})
 disagreements=[]
 for task in complete:
  positions=task["positions"];distances=[(positions[i]-positions[j])**2/16 for i,j in combinations(range(len(raters)),2)]
  disagreements.append({"task_id":task["task_id"],"group":task["group"],"codes":dict(zip(raters,task["codes"])),"span":max(positions)-min(positions),"mean_pair_distance":math.fsum(distances)/len(distances)})
 disagreements.sort(key=lambda r:(-r["mean_pair_distance"],r["task_id"]))
 w=kendall_w(matrix,raters)
 estimates=[p["kappa"] for p in pairs if p["kappa"] is not None]
 groups,reconciliation=build_groups(complete,isolated,raters,pairs,len(tasks),len(complete),len(isolated))
 return {"raters":raters,"levels":levels,"tasks_total":len(tasks),"tasks_complete":len(complete),"tasks_isolated":len(isolated),"isolated":isolated,"kendall":w,"pairs":pairs,"estimable_pairs":len(estimates),"mean_pair_kappa":math.fsum(estimates)/len(estimates) if estimates else None,"disagreements":disagreements,"rank_profile":[{"task_id":t["task_id"],"ranks":w["ranks"][i]} for i,t in enumerate(complete)] if w["ranks"] else [],"groups":groups,"group_reconciliation":reconciliation,"checksum":hashlib.sha256(json.dumps({"tasks":tasks,"raters":raters,"levels":levels},sort_keys=True).encode()).hexdigest(),"assumptions":["标尺是有序1至5级，代码与文字仅作类别标签；二次权重用序号位置距离，不把标签数值当连续量。","选择评委缺任一评分的任务整行隔离；W与每一个kappa配对共用完整任务分母，隔离清单可核对。","W衡量任务排序协调，不等同于原始等级绝对一致；kappa通过边际分布校正偶然一致，可能为负。","全常量秩无变异时W为null；期望分歧为0时kappa为null，不记为完美一致。少于2个完整任务不估计。","均值kappa仅是可估计评委对的描述均值，不是推断检验或自动判定标准。模拟任务评测，不用于人员录用决策。","分组分析仅沿用所选评委的共同完整任务，在每个任务组内重新排名，并列校正和五级二次权重口径与总体一致；总体W与kappa不因分组而改变，也不用各组系数的均值替代。","各组完整数、隔离数与每对评委5×5混淆计数可逐格相加合回总体，勾稽结果见group_reconciliation；空组名统一归入未分组。组内完整任务少于2或全常量导致秩无变异、期望分歧为0时，相应指标返回null并在reason中注明不可估计原因。"]}

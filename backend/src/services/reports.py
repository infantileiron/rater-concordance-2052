import uuid,csv,io
from sqlalchemy import select
from fastapi import HTTPException
from src.models import Report,PanelReview
from src.services.runs import require_completed
from src.utils.time import now
from src.utils.serialization import serialize
from src.utils.csv import safe_cell
def create(db,payload,user):
 require_completed(db,payload.run_id)
 review=db.scalar(select(PanelReview).where(PanelReview.run_id==payload.run_id).order_by(PanelReview.created_at.desc()))
 if not review or review.decision!="accepted":raise HTTPException(409,"最新复核须为接受后才能归档")
 if db.scalar(select(Report).where(Report.run_id==payload.run_id)):raise HTTPException(409,"本次运行已归档")
 item=Report(id=str(uuid.uuid4()),published_by=user["email"],created_at=now(),**payload.model_dump());db.add(item);db.commit();return serialize(item)
def _writer(buf,cols):
 writer=csv.DictWriter(buf,cols);writer.writeheader();return writer
def export(db,id):
 report=db.get(Report,id)
 if not report:raise HTTPException(404,"报告不存在")
 result=require_completed(db,report.run_id).result;buf=io.StringIO()
 # 区块一：总体评委对（历史列与顺序保持不变，兼容既有下载口径）
 cols=["rater_a","rater_b","complete_tasks","isolated_tasks","kendall_w","kappa","observed_disagreement","expected_disagreement","exact_agreement","reason"]
 writer=_writer(buf,cols)
 for p in result["pairs"]:writer.writerow({"rater_a":safe_cell(p["rater_a"]),"rater_b":safe_cell(p["rater_b"]),"complete_tasks":result["tasks_complete"],"isolated_tasks":result["tasks_isolated"],"kendall_w":result["kendall"]["value"],**{k:p[k] for k in ("kappa","observed_disagreement","expected_disagreement","exact_agreement","reason")}})
 groups=result.get("groups")
 if not groups:
  buf.write("\n# 该运行在分组功能上线前计算，结果未回填分组，重新创建运行即可获得分组分析。\n")
  return "﻿"+buf.getvalue()
 # 区块二：分组汇总（组内重新排名，并列校正与五级权重口径同总体）
 buf.write("\n# 分组汇总：组内共同完整任务重新排名，不以分组系数均值替代总体\n")
 gcols=["group","tasks_total","tasks_complete","tasks_isolated","kendall_w","kendall_reason","tie_correction","denominator","estimable_pairs","mean_pair_kappa"]
 gw=_writer(buf,gcols)
 for g in groups:gw.writerow({"group":safe_cell(g["group"]),"tasks_total":g["tasks_total"],"tasks_complete":g["tasks_complete"],"tasks_isolated":g["tasks_isolated"],"kendall_w":g["kendall"]["value"],"kendall_reason":g["kendall"]["reason"],"tie_correction":g["kendall"]["tie_correction"],"denominator":g["kendall"]["denominator"],"estimable_pairs":g["estimable_pairs"],"mean_pair_kappa":g["mean_pair_kappa"]})
 # 区块三：分组评委对指标（五级二次加权kappa）
 buf.write("\n# 分组评委对：二次加权Cohen kappa，n为该组共同完整任务数\n")
 pcols=["group","rater_a","rater_b","n","kappa","observed_disagreement","expected_disagreement","exact_agreement","reason"]
 pw=_writer(buf,pcols)
 for g in groups:
  for p in g["pairs"]:pw.writerow({"group":safe_cell(g["group"]),**{k:p[k] for k in ("rater_a","rater_b","n","kappa","observed_disagreement","expected_disagreement","exact_agreement","reason")}})
 # 区块四：分组混淆计数（逐格相加应等于总体5×5矩阵）
 buf.write("\n# 分组混淆计数：行级序号i、列级序号j为五级位置(1-5)，各组逐格相加等于总体\n")
 ccols=["group","rater_a","rater_b","level_row","level_col","count"]
 cw=_writer(buf,ccols)
 for g in groups:
  for p in g["pairs"]:
   for i,row in enumerate(p["matrix"],start=1):
    for j,count in enumerate(row,start=1):cw.writerow({"group":safe_cell(g["group"]),"rater_a":p["rater_a"],"rater_b":p["rater_b"],"level_row":i,"level_col":j,"count":count})
 # 区块五：勾稽核对（各组依据能否合回总体）
 buf.write("\n# 勾稽核对：各组完整数/隔离数/总数与逐格混淆计数合回总体\n")
 rec=result["group_reconciliation"]
 rcols=["check_item","groups_sum","overall_value","matches"]
 rw=_writer(buf,rcols)
 rw.writerow({"check_item":"完整任务数","groups_sum":rec["groups_complete_sum"],"overall_value":rec["overall_complete"],"matches":rec["complete_matches"]})
 rw.writerow({"check_item":"隔离任务数","groups_sum":rec["groups_isolated_sum"],"overall_value":rec["overall_isolated"],"matches":rec["isolated_matches"]})
 rw.writerow({"check_item":"原始任务数","groups_sum":rec["groups_total_sum"],"overall_value":rec["overall_total"],"matches":rec["total_matches"]})
 for c in rec["checks"]:
  rw.writerow({"check_item":"混淆矩阵 "+c["rater_a"]+" × "+c["rater_b"],"groups_sum":c["groups_n_sum"],"overall_value":c["overall_n"],"matches":c["matrix_matches"]})
 return "﻿"+buf.getvalue()

import {useState} from 'react';
import type {GroupResult,Result} from '../types/domain';
import {Notice} from './common/Notice';
import {PairTable} from './PairTable';
import {ConfusionMatrix} from './ConfusionMatrix';
import {number} from '../utils/format';

function ReconciliationBanner({result}:{result:Result}){
 const rec=result.group_reconciliation!;
 const ok=rec.all_match;
 return <Notice error={!ok}>
   {ok?'勾稽通过：':`勾稽存在差异：`}
   {rec.group_count}个组的完整任务 {rec.groups_complete_sum}＝总体 {rec.overall_complete}
   ，隔离 {rec.groups_isolated_sum}＝总体 {rec.overall_isolated}
   ，原始任务 {rec.groups_total_sum}＝总体 {rec.overall_total}
   ；{rec.confusion_pair_count}对评委的5×5混淆计数跨组逐格相加{rec.confusion_matches?'全部等于总体矩阵。':'存在不相等项，请核查。'}
   {rec.ungrouped_present&&' 空组名已统一归入“未分组”。'}
 </Notice>;
}

function GroupDetail({group,result}:{group:GroupResult;result:Result}){
 const [pairIndex,setPairIndex]=useState(0);
 const pair=group.pairs[Math.min(pairIndex,Math.max(0,group.pairs.length-1))];
 const w=group.kendall;
 return <div className="group-detail">
   <div className="result-metrics group-metrics">
     <div><small>组内 Kendall W</small><b>{number(w.value)}</b><em>{w.reason}</em></div>
     <div><small>完整 / 原始任务</small><b>{group.tasks_complete}<i> / {group.tasks_total}</i></b></div>
     <div><small>整行隔离</small><b>{group.tasks_isolated}<i>项</i></b><em>并列修正和 {w.tie_correction}，分母 {w.denominator}</em></div>
     <div><small>组成对κ均值</small><b>{number(group.mean_pair_kappa)}</b><em>可估计{group.estimable_pairs}对 / 共{group.pairs.length}对</em></div>
   </div>
   <p className="caption">{group.note}</p>
   <PairTable pairs={group.pairs}/>
   {pair&&<div className="group-matrix">
     <div className="section-heading"><h3>组内五级评分混淆矩阵</h3>
       <select aria-label="选择组内评委对" value={Math.min(pairIndex,group.pairs.length-1)} onChange={e=>setPairIndex(+e.target.value)}>
         {group.pairs.map((p,i)=><option key={i} value={i}>{p.rater_a} × {p.rater_b}</option>)}
       </select>
     </div>
     <ConfusionMatrix pair={pair} levels={result.levels}/>
   </div>}
   {group.rank_profile.length
     ? <div className="table-scroll group-rank"><table><thead><tr><th>任务</th>{result.raters.map(r=><th key={r}>{r}</th>)}</tr></thead>
       <tbody>{group.rank_profile.slice(0,12).map(t=><tr key={t.task_id}><td><b>{t.task_id}</b></td>{t.ranks.map((r,i)=><td key={i}>{number(r,2)}</td>)}</tr>)}</tbody></table>
       <p className="caption">组内平均秩，并列项共用平均秩；预览前12项，完整任务共{group.tasks_complete}项。</p></div>
     : <Notice>组内完整任务不足，无法重新排名，请核查该组隔离清单。</Notice>}
   <h3>组内缺评分隔离清单</h3>
   {group.isolated.length
     ? <div className="table-scroll"><table><thead><tr><th>任务</th><th>缺评分评委</th><th>处理原因</th></tr></thead>
       <tbody>{group.isolated.map(t=><tr key={t.task_id}><td>{t.task_id}</td><td>{t.missing_raters.join('、')}</td><td>{t.reason}</td></tr>)}</tbody></table></div>
     : <p className="caption">该组所选评委的任务全部完整，无隔离。</p>}
 </div>;
}

export function GroupAnalysis({result}:{result:Result}){
 const groups=result.groups;
 const [active,setActive]=useState('');
 if(!groups||!groups.length)return <section className="paper">
   <h2>分组分析</h2>
   <Notice>该运行在分组功能上线前计算，历史结果不回填分组；重新创建一次运行即可获得组内重新排名与勾稽核对。</Notice>
 </section>;
 const current=groups.find(g=>g.group===active)||groups[0];
 return <section className="paper">
   <div className="section-heading"><h2>分组分析 · 组内重新排名</h2><span>{groups.length}个任务组 / 共用所选{result.raters.length}名评委</span></div>
   <ReconciliationBanner result={result}/>
   <p className="caption">总体W与kappa保持共同完整任务口径不变；分组只在组内重算，各组系数不做平均、不替代总体。组内完整任务少于2、全常量致秩无变异或期望分歧为0时，对应指标为“不可估计”并在表内注明原因。</p>
   <div className="run-selector group-selector"><label>选择任务组
     <select aria-label="选择任务组" value={current.group} onChange={e=>setActive(e.target.value)}>
       {groups.map(g=><option key={g.group} value={g.group}>{g.group}（完整{g.tasks_complete} / 隔离{g.tasks_isolated}）</option>)}
     </select></label></div>
   <GroupDetail key={current.group} group={current} result={result}/>
 </section>;
}

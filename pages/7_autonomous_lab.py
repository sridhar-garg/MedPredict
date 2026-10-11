"""CARE-BOT: non-clinical research & simulated robotics demonstration."""
from __future__ import annotations
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import apply_custom_css
from adaptive_assessment import run_experiment
from robot_simulator import run_dispatch, benchmark, SIZE

st.set_page_config(page_title='CARE-BOT | Autonomous Evidence & Robotics Lab',page_icon='🤖',layout='wide',initial_sidebar_state='expanded')


from sidebar_compat import show_sidebar
show_sidebar()
apply_custom_css()
if not st.session_state.get('is_logged_in',False):
    st.warning('Log in through the HealthAI Dashboard to open CARE-BOT.')
    if st.button('Go to Login'):st.switch_page('app.py')
    st.stop()

st.markdown('''<div style="border-radius:20px;padding:25px 28px;background:linear-gradient(120deg,#102c4a,#1a4974,#106e85);color:white">
  <div style="font-size:12px;letter-spacing:2px;opacity:.9">EXPERIMENTAL AUTONOMOUS ROBOTICS + MEDICAL AI</div>
  <div style="font-size:37px;font-weight:900;margin-top:8px">🤖 CARE-BOT Laboratory</div>
  <div style="font-size:16px;max-width:780px;opacity:.90;margin-top:8px">Cost-aware evidence collection, robot dispatch under uncertainty, and measured comparisons against transparent baselines.</div>
</div>''',unsafe_allow_html=True)
st.caption('Reproducible academic demonstrations. Not clinical decision support; no actual robots or patients are controlled.')
st.info('Two independent demonstrations: real public tabular cell measurements for active feature selection, and a synthetic mobile-robot response environment. **Do not** claim clinical or physical-robot validation.')

tab1,tab2,tab3=st.tabs(['🧠 Active Measurement AI','🗺️ Autonomous Robot Simulation','🏆 Evaluation & Judge Evidence'])

with tab1:
    st.subheader('Original research question: Can the next measurement be chosen intelligently?')
    st.write('An automated laboratory could choose which image-derived measurements to extract next instead of always acquiring a fixed set. This prototype measures the value of that decision policy using 569 public tabular cell-measurement records.')
    c1,c2,c3=st.columns(3)
    with c1:budget=st.slider('Measurement budget (out of 30)',min_value=2,max_value=12,value=6,key='care_budget')
    with c2:coverage=st.slider('Target validation acceptance',min_value=.60,max_value=.95,value=.80,step=.05,key='care_cover')
    with c3:seed=st.number_input('Reproducibility seed',min_value=1,max_value=10000,value=42,step=1,key='care_seed')
    st.caption('Three methods use the **same train/validation/test split** and measurement budget: fixed top-ranked features, random acquisition, and case-adaptive expected-entropy selection. No test labels are used to pick a measurement.')
    if st.button('Run actual train → validation → locked test comparison',type='primary',use_container_width=True,key='care_train'):
        with st.spinner('Training masked-feature classifier and evaluating the three policies…'):
            try:st.session_state['care_real_result']=run_experiment(int(seed),int(budget),float(coverage))
            except Exception as e:st.error(f'Experiment failed: {type(e).__name__}: {e}')
    result=st.session_state.get('care_real_result')
    if result:
        st.success('Measured experiment finished. All values below come from model predictions on held-out cases.')
        st.caption('DATASET: '+result['provenance']['dataset']+' · '+str(result['provenance']['n_test'])+' held-out cases · 30 cell-measurement features; NOT X-rays')
        rows=[]
        for k,record in result['results'].items():
            a=record['uncalibrated'];b=record['calibrated_and_abstention']
            rows.append({'Policy':k.title(),'AUROC':a['AUROC'],'Brier ↓':a['Brier'],
                         'Accuracy @0.5':a['accuracy_at_0_5'],
                         'Calibrated Brier ↓':b['calibrated_brier'],
                         'Accepted test':b['accepted_test'], 'Abstained test':b['abstained_test'],
                         'Error among accepted':b['accepted_test_error_rate']})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        fig=go.Figure()
        fig.add_trace(go.Bar(name='AUROC',x=[r['Policy'] for r in rows],y=[r['AUROC'] for r in rows]))
        fig.update_layout(title='Measured discrimination at equal measurement budget',yaxis_range=[0.5,1.02],height=360)
        st.plotly_chart(fig,use_container_width=True)
        st.warning('The adaptive method is not guaranteed to win on other budgets or seeds. Calibration can make Brier score worse. Zero accepted-case errors on a small split is not 100% clinical accuracy.')
        with st.expander('How the adaptive policy works'):
            st.markdown('**Input:** already measured numeric features. **Candidate pool:** ranked on training cases. **Policy:** for every candidate feature, estimate possible values from nearest training observations, then estimate expected prediction entropy if measured. **Action:** choose the highest-scoring remaining feature. **Evaluation:** reveal the chosen feature from the held-out record only after selecting it, then measure prediction quality. The test label stays hidden until final scoring.')
            st.write('Example features acquired for one held-out case:',result['results']['adaptive']['sample_measurement_sequence'])
        data=json.dumps(result,indent=2,default=float)
        st.download_button('Download exact experiment JSON',data=data,file_name='carebot_active_measured.json',mime='application/json')

with tab2:
    st.subheader('Real A* path planning + autonomous multi-robot task assignment')
    st.write('Multiple simulated robots travel on a gridded disaster-response map. Their goal is to collect basic measurements from simulated people. Robots use A* to avoid obstacles; a task planner chooses where to go next.')
    cc1,cc2,cc3,cc4=st.columns(4)
    with cc1:rseed=st.number_input('Scenario seed',0,100000,13,key='care_rseed')
    with cc2:rpol=st.selectbox('Dispatcher',['CARE-BOT priority-aware','Nearest-first baseline'],key='care_policy')
    with cc3:rn=st.selectbox('Robot count',[1,2],index=1,key='care_n_robots')
    with cc4:fail=st.checkbox('Simulate failure of robot 1',key='care_robot_fail')
    blocked_path=st.checkbox('Block an additional corridor; force A* replanning',key='care_block')
    extra=((5,4),) if blocked_path else ()
    try:
        scenario=run_dispatch(int(rseed),'carebot' if rpol.startswith('CARE') else 'nearest',int(rn),extra,fail)
        m=scenario['metrics']
        c1,c2,c3,c4=st.columns(4)
        c1.metric('Tasks visited',f"{m['seen']}/{m['total_tasks']}")
        c2.metric('Priority-weighted wait',f"{m['mean_priority_weighted_response_minutes']:.1f} min")
        c3.metric('Simulated urgent response',f"{m['mean_urgent_response_minutes']:.1f} min" if m['mean_urgent_response_minutes'] is not None else 'n/a')
        c4.metric('Travel steps',m['total_travel_steps'])
        upto=st.slider('Replay assignments',min_value=0,max_value=len(scenario['paths']),value=len(scenario['paths']),key='care_replay')
        fig=go.Figure()
        obs=scenario['obstacles']
        fig.add_trace(go.Scatter(x=[v[0] for v in obs],y=[v[1] for v in obs],mode='markers',name='Blocked cells',marker={'symbol':'square','size':21,'color':'#263952'}))
        colors=['#12a1ad','#ae5cf0']
        for i,pos in enumerate(scenario['robot_starts']):
            fig.add_trace(go.Scatter(x=[pos[0]],y=[pos[1]],mode='markers+text',text=[f'R{i+1} start'],textposition='top center',name=f'Robot {i+1}',marker={'size':18,'color':colors[i],'symbol':'diamond'}))
        tasks=scenario['patient_tasks']
        fig.add_trace(go.Scatter(x=[t.xy[0] for t in tasks],y=[t.xy[1] for t in tasks],mode='markers+text',text=[f'P{t.uid}' for t in tasks],textposition='top center',name='Synthetic patients',marker={'size':[13+12*t.visible_priority for t in tasks],'color':[t.visible_priority for t in tasks],'colorscale':'YlOrRd','showscale':True,'colorbar':{'title':'Proxy priority'}}))
        for route in scenario['paths'][:upto]:
            pts=route['path']; robot=route['robot']
            fig.add_trace(go.Scatter(x=[p[0] for p in pts],y=[p[1] for p in pts],mode='lines',name=f"R{robot+1} → P{route['patient']}",line={'color':colors[robot],'width':3},showlegend=False))
        fig.update_layout(xaxis={'range':[-.5,SIZE[0]-.5],'dtick':1,'title':'Grid x'},
                          yaxis={'range':[-.5,SIZE[1]-.5],'dtick':1,'scaleanchor':'x','title':'Grid y'},
                          height=510,margin={'l':25,'r':25,'t':25,'b':35})
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(pd.DataFrame(scenario['events']).drop(columns=['xy']),hide_index=True,use_container_width=True)
        st.caption('Synthetic urgency is hidden from the dispatch algorithm and used only for evaluation. The visible risk proxy is simulated noisy information, NOT derived from an actual patient. Task assignment is a high-level planner; collisions, motors and communications are not physically simulated.')
    except Exception as e:st.error('Simulator failed: '+str(e))

with tab3:
    st.subheader('Controlled autonomous-routing experiment')
    st.write('Run the **same scenarios** under nearest-first and CARE-BOT. The benchmark reports both improvements and sacrifices, not cherry-picked winning cases.')
    bx,by=st.columns(2)
    with bx:nscenarios=st.slider('Independent synthetic scenario seeds',10,100,40,10)
    with by:robot_failures=st.checkbox('Include robot-1 failures in both policies')
    if st.button('Run fair baseline comparison',type='primary',use_container_width=True,key='care_benchmark'):
        try:st.session_state['care_robot_benchmark']=benchmark(nscenarios,17,2,robot_failures)
        except Exception as exc:st.error(str(exc))
    results=st.session_state.get('care_robot_benchmark')
    if results:
        df=pd.DataFrame([{'Metric':name.replace('_',' ').title(),**scores} for name,scores in results['mean_metrics'].items()])
        st.dataframe(df,hide_index=True,use_container_width=True)
        st.caption('Lower is better for these four measures. A high-priority planner may travel more or take longer overall.')
        base=results['mean_metrics']['mean_urgent_response_minutes']['nearest_first']
        alt=results['mean_metrics']['mean_urgent_response_minutes']['risk_uncertainty_aware']
        if base and alt:
            delta=100*(base-alt)/base
            st.metric('Synthetic urgent response improvement over nearest-first',f'{delta:+.1f}% faster' if delta>=0 else f'{-delta:.1f}% slower')
        st.download_button('Download all scenario-level benchmark results (JSON)',json.dumps(results,indent=2),file_name='carebot_robot_synthetic_benchmark.json',mime='application/json')
        st.download_button('Download scenario data CSV',pd.DataFrame(results['cases']).to_csv(index=False),file_name='carebot_robot_scenarios.csv',mime='text/csv')
    st.divider()
    st.subheader('Defense checklist: what to tell the judges')
    st.markdown('''
- **Original contribution to demonstrate:** a cost/budget-aware policy for choosing additional laboratory measurements and a separate uncertainty-aware mobile-robot dispatch policy, each evaluated against simple baselines.
- **Actually tested:** the numerical-feature policies on a public tabular dataset with disjoint train, validation and test cases; mobile robot planning in fully synthetic scenarios with A* obstacle avoidance.
- **Not tested:** patient safety, clinical effectiveness, 50,000+ image training, actual robot navigation, external hospital generalization or hardware.
- **Meaningful limitations:** noisy cytology labels, small test set, no physical acquisition cost measurements, synthetic robot priority scores and simplified grid dynamics.
- **Planned physical prototype:** a low-cost camera-equipped mobile base or table-top gantry to demonstrate navigation/sensor acquisition; hardware has **not** been built in this ZIP.
- **Rubric connection:** measurable autonomous planning, technical execution, originality of the problem formulation, and disaster-healthcare relevance. Confirm with organisers that software-only robot simulation is eligible.
''')

st.divider()
if st.button('← Back to MedPredict Dashboard',key='care_home'):st.switch_page('app.py')

"""MedPredict X research workbench — never a clinical diagnostic workflow."""
from __future__ import annotations
import json
import os
from datetime import date
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

from utils import apply_custom_css
from research_quality import (quality_report, research_abstention, softmax_entropy,
                               model_saliency, blur_robustness, overlay_from_bytes)
from research_metrics import binary_report, bootstrap_auroc, ks_stat, psi
from lab_report_tools import candidates, to_fhir_observations, pdf_or_image_to_text
from research_sources import find_evidence
from research_benchmarks import demo_experiment, external_experiment, research_summary

st.set_page_config(page_title='MedPredict X | AI Research Hub', page_icon='🧪', layout='wide', initial_sidebar_state='expanded')


from sidebar_compat import show_sidebar
show_sidebar()
apply_custom_css()
if not st.session_state.get('is_logged_in', False):
    st.warning('Please log in to MedPredict on the Dashboard before opening the Research Hub.')
    if st.button('Go to Dashboard / Login'):st.switch_page('app.py')
    st.stop()

st.title('🧪 MedPredict X — AI Research Hub')
st.caption('Research-only tools · not a medical device · use public de-identified datasets, not real patient records')
st.warning('Model outputs, heatmaps, screening formulas and distribution-shift warnings cannot diagnose or exclude disease. No clinical recommendation should be based on this prototype.')

tabs=st.tabs(['🔍 Explainability','📊 Validation Lab','🧬 Multimodal Workspace',
              '🧾 Lab Reports','🧊 3D Image Viewer','📚 Evidence Finder',
              '📈 Drift Monitor','🏋️ Train 50k+ X-rays','🏆 Evidence Studio'])

with tabs[0]:
    st.subheader('Visual attribution, input quality, and robustness checks')
    st.write('Select a supported, task-specific pretrained classifier. Gradients highlight pixels influencing the prediction; they do not localise disease.')
    try:
        from imaging_models import MODELS
    except ImportError:
        st.error('imaging_models.py is missing. Run the previous complete research upgrade first.')
        MODELS={}
    if MODELS:
        choices={f'{m.label} · {m.key}':m for m in MODELS.values()}
        selected=st.selectbox('Classifier',list(choices),key='mpx_ex_model')
        spec=choices[selected]
        up=st.file_uploader('Research image (PNG/JPEG, 15 MB maximum)',type=['png','jpg','jpeg'],key='mpx_gradcam_upload')
        steps=st.slider('Gradient integration steps (higher is slower)',1,12,4)
        if up:
            try:
                im=overlay_from_bytes(up.getvalue())
                q=quality_report(im)
                st.image(im,caption='Input image (modality and anatomy NOT verified by software)',width=440)
                c1,c2,c3=st.columns(3)
                c1.metric('Resolution',f'{q.width} × {q.height}')
                c2.metric('Contrast std',f'{q.contrast_std:.1f}')
                c3.metric('Edge energy',f'{q.edge_energy:.1f}')
                if q.warnings:st.warning('Image-quality heuristics: '+' | '.join(q.warnings))
                st.caption(f'Supported research domain: {spec.trained_on}. {spec.limitation}')
                confirmed=st.checkbox('I verified this is the appropriate scan type/body part, and it contains no identifying information.',key='mpx_ex_check')
                if st.button('Compute explanation & test blur stability',disabled=not confirmed,key='mpx_grad_button'):
                    try:
                        with st.spinner('Loading model and calculating gradients (first run may download weights) …'):
                            overlay,scores=model_saliency(im,spec,steps=steps)
                            perturb=blur_robustness(im,spec)
                        a,b=st.columns(2)
                        with a:st.image(im,caption='Original',use_container_width=True)
                        with b:st.image(overlay,caption='Model attribution overlay — not a medical localisation map',use_container_width=True)


                        st.session_state['mpx_image_result']={
                            'task':spec.label,'model_id':spec.repo_id,
                            'label':scores[0][0],'raw_score':scores[0][1]}
                        st.dataframe(pd.DataFrame(scores,columns=['Model class','Raw softmax score']).head(10),hide_index=True)
                        ent=softmax_entropy([s for _,s in scores])
                        st.metric('Normalised class entropy',f'{ent:.3f}')
                        reasons=research_abstention(q,ent,scores[0][1])
                        if reasons:st.warning('Conservative demonstration abstention flags: '+' | '.join(reasons))
                        st.dataframe(pd.DataFrame(perturb,columns=['Class','Original raw score','Blurred raw score','Absolute change']).head(10),hide_index=True)
                        st.info('Model score changes under blur can indicate fragility, but do not quantify diagnostic reliability. Thresholds are illustrative until validated on a held-out dataset.')
                    except Exception as e:
                        st.error('Model attribution could not run. The selected model may be unavailable or incompatible with your installed Transformers version.')
                        st.code(f'{type(e).__name__}: {e}')
            except Exception as e:st.error(f'Unable to open image: {e}')

with tabs[1]:
    st.subheader('Held-out classification validation (your own labelled predictions)')
    st.write('Upload a CSV containing a ground-truth `label` (0/1), a `score` (0–1), optionally `patient_id` and `model`. The score must come from a held-out dataset, not training data.')
    uploaded=st.file_uploader('Predictions CSV',type=['csv'],key='mpx_evalcsv')
    if uploaded:
        try:
            df=pd.read_csv(uploaded)
            if len(df)>150_000:raise ValueError('Up to 150,000 rows supported')
            if not {'label','score'}.issubset(df):raise ValueError('Columns `label` and `score` required')
            if 'model' in df.columns:
                model_name=st.selectbox('Evaluate model',sorted(df['model'].dropna().astype(str).unique()))
                df=df[df['model'].astype(str)==model_name].copy()
            st.write('Rows:',len(df))
            threshold=st.slider('Classification threshold',.05,.95,.50,.05)
            if st.button('Calculate real validation metrics'):
                result=binary_report(df.label.to_numpy(),df.score.to_numpy(),threshold)
                bounds=bootstrap_auroc(df.label.to_numpy(),df.score.to_numpy(),
                     df['patient_id'].to_numpy() if 'patient_id' in df else None,repeats=150)
                result['AUROC_95pct_bootstrap_CI']=bounds
                st.json(result)
                st.caption('A reliable independent test requires patient-disjoint partitions and no test-set tuning. Bootstrap confidence intervals depend on the chosen sampling unit.')
                import matplotlib.pyplot as plt
                from sklearn.calibration import calibration_curve
                if result['positives'] not in [0,len(df)]:
                    actual,predicted=calibration_curve(df.label.astype(int),df.score.astype(float),n_bins=8,strategy='quantile')
                    chart=pd.DataFrame({'Mean prediction':predicted,'Observed positive fraction':actual})
                    st.scatter_chart(chart,x='Mean prediction',y='Observed positive fraction')
        except Exception as e:st.error(f'Invalid evaluation data: {e}')
    else:
        st.code('label,score,patient_id,model\n1,0.86,patient001,modelA\n0,0.12,patient002,modelA\n1,0.73,patient003,modelA',language='csv')

with tabs[2]:
    st.subheader('Multimodal evidence workspace')
    st.write('Combine supported evidence into a transparent table. No untrained fusion network is used, and no combined disease probability is invented.')
    auto=st.session_state.get('mpx_image_result')
    if auto:
        st.success(f"Automatically loaded the last imaging classifier result: {auto['task']} → {auto['label']} (raw score {auto['raw_score']:.3f}).")
    verified_labs=st.session_state.get('mpx_verified_labs',[])
    if verified_labs:
        st.info(f"Also found {len(verified_labs)} verified laboratory observation(s) from this session.")
    with st.form('mpx_evidence_form'):
        imaging_task=st.selectbox('Imaging source',['No imaging assessment','Chest X-ray research model','Bone X-ray research model','Brain MRI research model','Other supported image model'])
        image_label=st.text_input('Model-generated category (copy it from imaging results; optional)',max_chars=100)
        image_score=st.number_input('Raw classifier score (only if available)',0.,1.,value=0.,step=.01)
        report_measure=st.selectbox('Confirmed laboratory evidence',['None','Haemoglobin (g/dL)','Creatinine (mg/dL)','LDL (mg/dL)','Glucose (mg/dL)'])
        measure_value=st.number_input('Confirmed measurement value',min_value=0.,max_value=10000.,value=0.)
        symptom_context=st.text_area('Optional non-identifying context for the demonstration (no names or real patient details)',height=75)
        submitted=st.form_submit_button('Compile evidence table')
    if submitted:
        entries=[]
        if auto:
            entries.append({'modality':auto['task'],'finding':auto['label'],'value':auto['raw_score'],
                            'evidence_status':'Uncalibrated actual classifier score',
                            'provenance':auto['model_id']})
        for row in verified_labs:
            entries.append({'modality':'Verified lab OCR','finding':row['test'],
                            'value':row['candidate_value'],'evidence_status':'User-verified transcription',
                            'provenance':row.get('source_excerpt','Report')})
        if imaging_task!='No imaging assessment' and image_label:
            entries.append({'modality':imaging_task,'finding':image_label,'value':image_score,
                            'evidence_status':'Uncalibrated classifier output','provenance':'Manual transfer'})
        if report_measure!='None':
            entries.append({'modality':'Lab report','finding':report_measure,'value':measure_value,
                            'evidence_status':'User-confirmed measured value','provenance':'Manual entry'})
        if symptom_context.strip():
            entries.append({'modality':'Context','finding':'Supplied context (not verified)','value':'—',
                            'evidence_status':'Self-reported text','provenance':'Manual entry'})
        if entries:
            st.dataframe(pd.DataFrame(entries),hide_index=True,use_container_width=True)
            st.download_button('Export evidence JSON',json.dumps(entries,indent=2).encode(),'research_evidence.json','application/json')
        else:st.info('No evidence was provided.')
        st.warning('Integration ≠ model fusion. Real fusion requires paired, labelled multi-source cases and separate validation. A high image score must not override contradictory or missing clinical evidence.')

with tabs[3]:
    st.subheader('Document intelligence: lab values and FHIR-style export')
    st.write('OCR and regex extract candidate values; you must verify test name, units, result and date against the original report. Files are processed during this session, not saved by this add-on.')
    report=st.file_uploader('Upload de-identified PDF or scanned image',type=['pdf','png','jpg','jpeg'],key='mpx_report')
    pasted=st.text_area('Alternatively paste de-identified report text',height=100,key='mpx_report_text')
    if st.button('Extract measurement candidates',key='mpx_report_run'):
        try:
            t=pasted
            if report:t+='\n'+pdf_or_image_to_text(report.getvalue(),report.name)
            if not t.strip():raise ValueError('Upload a report or paste text')
            rows=candidates(t)
            st.session_state['mpx_rows']=rows
            st.success(f'Found {len(rows)} candidate measurement(s). This is not automatic medical interpretation.')
        except Exception as e:st.error(f'Text extraction failed: {e}. For image OCR, install Tesseract OCR on Windows.')
    if st.session_state.get('mpx_rows'):
        raw_rows=st.session_state['mpx_rows']
        df=pd.DataFrame([{**r,'human_verified':False} for r in raw_rows])
        edited=st.data_editor(df,hide_index=True,disabled=['line','test','source_excerpt','unit_read','expected_unit','unit_matches'],use_container_width=True)
        date_value=st.date_input('Report date (verify from original)',date.today())
        valid=edited.to_dict('records')
        if st.button('Build verified structured observations'):
            docs=to_fhir_observations(valid,date_value.isoformat())
            st.session_state['mpx_fhir']=docs
            st.session_state['mpx_verified_labs']=[r for r in valid if r.get('human_verified') and r.get('unit_matches')]
            st.info(f"Prepared {len(docs['entry'])} human-verified unit-matching observations. Verify against your data standards before exchange with any health system.")
        if st.session_state.get('mpx_fhir'):
            st.download_button('Download FHIR-style JSON Bundle',json.dumps(st.session_state['mpx_fhir'],indent=2).encode(),
                               file_name='observations_demo.json',mime='application/json')
    st.divider()
    st.markdown('#### Longitudinal lab trends (verified research CSV)')
    st.caption('Use a de-identified CSV with `date,test,value,unit` columns. Make sure units are consistent across dates.')
    trend_file=st.file_uploader('Upload verified lab trend CSV',type=['csv'],key='mpx_labtrend')
    if trend_file:
        try:
            trends=pd.read_csv(trend_file)
            if len(trends)>10000:raise ValueError('Maximum 10,000 trend rows')
            if not {'date','test','value','unit'}.issubset(trends.columns):
                raise ValueError('Need date,test,value,unit columns')
            trends['date']=pd.to_datetime(trends['date'],errors='raise')
            trends['value']=pd.to_numeric(trends['value'],errors='raise')
            option=st.selectbox('Test to plot',sorted(trends['test'].astype(str).unique()),key='mpx_lab_selected')
            filtered=trends[trends['test']==option].copy()
            if filtered['unit'].astype(str).nunique()>1:
                st.error('Mixed units detected. Harmonise them outside the app before comparing values.')
            else:
                st.line_chart(filtered.sort_values('date').set_index('date')['value'])
                st.caption(f"Unit: {filtered['unit'].iloc[0]}. Trends are descriptive and should not be interpreted without context.")
        except Exception as e:st.error(f'Could not plot verified lab trends: {e}')

with tabs[4]:
    st.subheader('DICOM / NIfTI volume exploration and intensity-mask demo')
    st.warning('The 3D intensity threshold is NOT a learned organ segmentation model. Correct clinical segmentation needs separately validated anatomy-specific weights.')
    choice=st.radio('Study format',['NIfTI (.nii.gz)','DICOM series (multiple .dcm images)'],horizontal=True)
    if choice.startswith('NIfTI'):
        nifti=st.file_uploader('3D NIfTI image',type=['gz'],key='mpx_nii')
        dcm_files=[]
    else:
        dcm_files=st.file_uploader('A single de-identified DICOM series only',type=['dcm'],accept_multiple_files=True,key='mpx_dcms')
        nifti=None
    if st.button('Load local study into viewer',key='mpx_load_volume'):
        try:
            from volume_viewer import load_nifti,load_dicom_series
            if nifti:volume=load_nifti(nifti.getvalue())
            elif dcm_files:volume=load_dicom_series([f.getvalue() for f in dcm_files])
            else:raise ValueError('Select a study first')

            st.session_state['mpx_volume']=volume
            st.success(f'Volume loaded: {volume.shape} · voxel coordinates only; orientation not clinically calibrated.')
        except Exception as e:st.error(f'Cannot load volume: {e}')
    volume=st.session_state.get('mpx_volume')
    if isinstance(volume,np.ndarray):
        from volume_viewer import preview_slice,threshold_voxels
        axis=st.selectbox('Slice orientation (array axis, not guaranteed patient anatomical orientation)',[0,1,2])
        index=st.slider('Slice',0,int(volume.shape[axis]-1),int(volume.shape[axis]//2))
        st.image(preview_slice(volume,axis,index),caption='Voxel slice preview',clamp=True,width=520)
        lo=float(np.nanpercentile(volume,5));hi=float(np.nanpercentile(volume,95))
        if lo>=hi:st.info('Constant intensity volume; no threshold mask available.')
        else:
            vmin,vmax=st.slider('Educational threshold range',min_value=lo,max_value=hi,value=(lo,hi),step=max((hi-lo)/100,0.001))
            if st.button('Compute threshold mask preview'):
                mask=threshold_voxels(volume,vmin,vmax)
                st.metric('Fraction of voxels in selected range',f'{100*mask.mean():.2f}%')
                st.caption('This threshold mask is not anatomical segmentation. It should not be used to calculate organ size or pathology.')

                try:
                    import plotly.graph_objects as go
                    strides=tuple(max(1,int(np.ceil(sz/32))) for sz in volume.shape)
                    sub=volume[::strides[0],::strides[1],::strides[2]]
                    x,y,z=np.mgrid[0:sub.shape[0],0:sub.shape[1],0:sub.shape[2]]
                    value_min,value_max=np.percentile(sub,[5,95])
                    if value_max>value_min:
                        fig=go.Figure(data=go.Isosurface(x=x.ravel(),y=y.ravel(),z=z.ravel(),value=sub.ravel(),
                            isomin=vmin,isomax=vmax,surface_count=2,caps=dict(x_show=False,y_show=False,z_show=False)))
                        fig.update_layout(title='Intensity isosurfaces — not segmented organs',height=390,
                                          margin=dict(l=10,r=10,b=10,t=50))
                        st.plotly_chart(fig,use_container_width=True)
                except Exception as e:st.caption(f'3D display unavailable: {e}')
    st.markdown('For **task-specific pretrained organ segmentation**, see the [MONAI model zoo](https://github.com/Project-MONAI/model-zoo). Its spleen CT bundle is suitable only with matching imaging and preprocessing; not connected as a universal segmenter.')

with tabs[5]:
    st.subheader('Evidence-grounded research finder')
    st.write('Retrieval from a small, attributable bibliography. This feature does not generate new medical advice or claim to verify live guidelines.')
    q=st.text_input('Research question, e.g. How do I validate chest X-ray AI?')
    if q:
        matches=find_evidence(q)
        if matches:
            for source,score in matches:
                with st.expander(f"{source['title']} · similarity {score:.2f}",expanded=score==matches[0][1]):
                    st.write(source['summary'])
                    st.markdown(f"[Read the original source]({source['url']})")
            st.info('Scores are document relevance scores, NOT levels of medical evidence or truth. Follow each source to check its full context.')
        else:st.info('No matching curated reference. This system abstains rather than fabricating a citation.')

with tabs[6]:
    st.subheader('Data shift and monitoring')
    st.write('Upload two CSV files with the same numeric feature(s): a reference dataset and a new batch. No data is collected automatically.')
    c1,c2=st.columns(2)
    with c1:reference=st.file_uploader('Reference numeric CSV',type=['csv'],key='mpx_ref')
    with c2:incoming=st.file_uploader('Current batch numeric CSV',type=['csv'],key='mpx_batch')
    if reference and incoming:
        try:
            a=pd.read_csv(reference);b=pd.read_csv(incoming)
            if max(len(a),len(b))>150000:raise ValueError('Maximum 150k rows per CSV')
            common=[c for c in a.columns if c in b.columns and pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c])]
            if not common:raise ValueError('No shared numeric columns')
            feature=st.selectbox('Metric to compare',common)
            if st.button('Check distribution shift'):
                pi=psi(a[feature],b[feature]);ks,p=ks_stat(a[feature],b[feature])
                st.metric('PSI (heuristic)',f'{pi:.3f}' if np.isfinite(pi) else 'Undefined')
                st.metric('KS statistic',f'{ks:.3f}')
                st.write('KS test p-value:',p)
                st.dataframe(pd.DataFrame({'dataset':['reference','current'],'n':[len(a),len(b)],
                    'mean':[a[feature].mean(),b[feature].mean()], 'std':[a[feature].std(),b[feature].std()]}),hide_index=True)
                st.warning('Detected data shift does not prove performance degradation, and absence of shift does not guarantee model safety. Labels are needed to measure changing errors.')
        except Exception as e:st.error(f'Drift analysis failed: {e}')
    else:
        st.caption('Suggested columns: model_score, inference_ms, image_contrast, image_width. Use synthetic/non-identifying telemetry in demos.')

with tabs[7]:
    st.subheader('Build your own chest X-ray model on 50,000+ images')
    st.write('The ZIP provides a real patient-disjoint training and evaluation pipeline. It does NOT contain a newly trained model.')
    st.markdown('**Official source:** [NIH Clinical Center ChestXray14](https://nihcc.app.box.com/v/ChestXray-NIHCC) — 112,120 images, 30,805 patients, report-derived labels.')
    st.code('''# Download the NIH ChestXray14 images and metadata via the official NIH link.
# Place Data_Entry_2017_v2020.csv, train_val_list.txt, test_list.txt,
# and extracted PNG files inside D:\\NIH_ChestXray14.
.\\.venv\\Scripts\\python.exe train_nih_chestxray14.py --data-root "D:\\NIH_ChestXray14" --epochs 10 --batch-size 16 --output "trained_nih14"
''',language='powershell')
    st.caption('Patient-disjoint train/validation/test partitions, early stopping by validation AUROC and one held-out test run; training 50k+ cases needs significant storage and preferably a GPU.')
    ckpt_path=os.getenv('MEDPREDICT_NIH_MODEL_PATH','')
    if ckpt_path and Path(ckpt_path).is_file():
        st.success('Local research checkpoint detected via MEDPREDICT_NIH_MODEL_PATH.')
        sample=st.file_uploader('Test a frontal chest X-ray (research only)',type=['png','jpg','jpeg'],key='mpx_nih_sample')
        if sample and st.button('Infer with my trained model'):
            try:
                from medpredict_x_nih import infer_nih
                im=overlay_from_bytes(sample.getvalue())
                scores,meta=infer_nih(im,ckpt_path)
                st.dataframe(pd.DataFrame(scores),hide_index=True)
                st.caption(f"Train images recorded: {meta['train_images']}. The values above are raw multi-label sigmoid outputs; not calibrated disease probabilities.")
            except Exception as e:st.error(f'Own-model inference failed: {e}')
    else:st.info('No custom checkpoint has been trained/configured. The pre-existing six pretrained models are unchanged.')
    st.markdown('A **high accuracy claim** requires independent validation; weak NIH report-derived labels and differences between hospitals can substantially affect generalisation.')



with tabs[8]:
    st.subheader('🏆 Evidence Studio — test a real hypothesis, not a fake score')
    st.info('The built-in one-click experiment trains on 569 diagnostic *tabular* cases. It does NOT train a chest X-ray model on NIH images. You may separately evaluate real NIH model predictions below.')
    st.markdown('**Research hypothesis:** Properly calibrated predictions plus a validation-selected abstention threshold can reduce error on accepted test cases. This is a hypothesis, NOT a promised improvement.')
    target_coverage=st.slider('Target validation coverage',0.50,1.00,0.80,0.05,key='mpx_ev_coverage')
    evidence_mode=st.radio('Experiment source',
        ['One-click genuine public-data experiment','Evaluate MY held-out image-model scores'],
        horizontal=True,key='mpx_ev_mode')
    res=None
    preds=None
    if evidence_mode=='One-click genuine public-data experiment':
        st.caption('Dataset: scikit-learn Wisconsin Diagnostic Breast Cancer, 569 cases; image features are NOT used. Positive label = malignant. Real Random Forest training, independent validation calibration, untouched test data.')
        if st.button('Train and evaluate on a locked test set',type='primary',key='mpx_ev_demo'):
            with st.spinner('Training, calibrating and evaluating …'):
                try:
                    res,preds=demo_experiment(seed=42,target_coverage=target_coverage)
                    st.session_state['mpx_ev_result']=res
                    st.session_state['mpx_ev_predictions']=preds
                    st.session_state['mpx_ev_applied_coverage']=target_coverage
                except Exception as exc:st.error(f'Experiment failed: {type(exc).__name__}: {exc}')
        else:
            if st.session_state.get('mpx_ev_applied_coverage')==target_coverage:
                res=st.session_state.get('mpx_ev_result')
                preds=st.session_state.get('mpx_ev_predictions')
    else:
        st.warning('Upload prediction scores generated by the SAME fitted image model on independent validation and held-out test sets. The app checks patient overlap, but cannot authenticate labels, data source, or model provenance.')
        st.code('label,score,patient_id\n1,0.84,deidentified_001\n0,0.10,deidentified_002',language='csv')
        c1,c2=st.columns(2)
        with c1:val_file=st.file_uploader('Validation scores (CSV)',type=['csv'],key='mpx_ev_val')
        with c2:test_file=st.file_uploader('Locked test scores (CSV)',type=['csv'],key='mpx_ev_test')
        if val_file and test_file and st.button('Evaluate independent test scores',type='primary',key='mpx_ev_external'):
            try:
                val=pd.read_csv(val_file)
                test=pd.read_csv(test_file)
                res,preds=external_experiment(val,test,target_coverage)
                st.session_state['mpx_ev_result']=res
                st.session_state['mpx_ev_predictions']=preds
            except Exception as exc:st.error(f'Could not evaluate: {type(exc).__name__}: {exc}')
    if res is not None:
        st.success('Experiment completed and measured. No outcome was fabricated.')
        st.caption('Source: '+res['provenance']['dataset'])
        a=res['raw_test'];b=res['calibrated_test'];sel=res['abstention_test']
        summary=pd.DataFrame([
            {'Method':'Uncalibrated baseline','AUROC':a['AUROC'],'Brier (lower=better)':a['Brier_score'],'ECE (lower=better)':a['ECE_10_bins'],'Accuracy':a['accuracy']},
            {'Method':'Calibrated (val-only)','AUROC':b['AUROC'],'Brier (lower=better)':b['Brier_score'],'ECE (lower=better)':b['ECE_10_bins'],'Accuracy':b['accuracy']},
        ])
        st.dataframe(summary,hide_index=True,use_container_width=True)
        m1,m2,m3=st.columns(3)
        m1.metric('Test acceptance rate',f"{100*sel['coverage']:.1f}%")
        m2.metric('Test error (all cases)',f"{100*sel['error_rate_without_abstention']:.1f}%")
        m3.metric('Test error (accepted only)',f"{100*sel['error_rate_on_accepted']:.1f}%" if sel['error_rate_on_accepted'] is not None else 'n/a')
        st.caption('Acceptance threshold was selected using validation scores; test-set coverage can differ from target. Abstentions are NOT medically validated safe decisions.')
        ci=res['calibrated_auroc_95pct_bootstrap_CI']
        st.write(f'Calibrated AUROC bootstrap 95% interval: **{ci[0]}–{ci[1]}** (approximate; use independent patient grouping when available).')
        with st.expander('Calibration reliability points'):
            st.dataframe(pd.DataFrame(res['reliability_points']),hide_index=True)
        if 'tabular_noise_stress_test' in res:
            noisy=res['tabular_noise_stress_test']
            st.markdown('**Controlled stress experiment (tabular feature noise, not radiography)**')
            st.write('Baseline test AUROC:',noisy['baseline']['AUROC'],'· Perturbed test AUROC:',noisy['perturbed']['AUROC'])
        st.download_button('Download measured experiment JSON',
            data=json.dumps(res,indent=2),file_name='medpredict_x_measured_evidence.json',mime='application/json',key='mpx_ev_dl_json')
        st.download_button('Download defensible research write-up (Markdown)',
            data=research_summary(res),file_name='medpredict_x_research_summary.md',mime='text/markdown',key='mpx_ev_dl_md')
        if preds is not None:
            st.download_button('Download held-out prediction scores (CSV; no patient IDs)',
                data=preds.to_csv(index=False),file_name='medpredict_x_holdout_predictions.csv',mime='text/csv',key='mpx_ev_dl_csv')
        st.warning('The one-click dataset is 569 tabular cases, not 50,000+ chest images. Do not describe the resulting metrics as NIH X-ray, clinical, or external-hospital performance.')

st.divider()
if st.button('← Return to Dashboard'):st.switch_page('app.py')

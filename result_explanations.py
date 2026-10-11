"""Transparent, inline, non-generative explanations for the existing MedPredict pages."""
from __future__ import annotations
import streamlit as st


def explain_prediction(result:dict, disease:str):
    """Returns descriptive explanation of model-derived output (not causal attribution)."""
    with st.expander('🔎 Explain my AI result', expanded=False):
        category=result.get('risk_category', 'Not available')
        st.markdown(f'**Reported category:** {category}')
        probability=result.get('probability')
        if isinstance(probability,(int,float)):
            st.write(f'MedPredict combined its model scores into an estimate of **{probability*100:.1f}%**. '
                     'This is a model output, not your actual probability of having the disease unless independently calibrated and validated.')
        st.write(f'The **{disease}** estimate is based on the information entered into the assessment. '
                 'It does not confirm or exclude a medical diagnosis.')
        st.write('**How to verify it:** check the values you entered, understand the training population and limitations, '
                 'and discuss concerning symptoms or medical results with a qualified clinician.')
        st.caption('The score alone does not identify which specific input caused the prediction. '
                   'When the underlying model exposes verified SHAP explanations, use those plots for model-feature attribution.')


def explain_screening(result:dict,metric=None,source_url:str|None=None):
    with st.expander('🔎 Explain my screening result',expanded=False):
        st.write(f"This category was calculated from a published screening formula or reference range: **{result.get('label','—')}**.")
        if metric:st.write(f'Input/derived metric: **{metric[0]} — {metric[1]}**.')
        st.write('This is **rule-based screening**, not an AI diagnosis, and it cannot establish treatment needs by itself.')
        if source_url:st.link_button('Review clinical reference',source_url)


def explain_report(values:dict,verified:bool=False):
    with st.expander('🔎 Explain my medical report',expanded=False):
        st.write('MedPredict extracts text from the PDF or image, matches supported laboratory test names, '
                 'and then applies a small number of transparent screening formulas/reference ranges.')
        if values:
            st.write(f'**{len(values)} candidate measurement(s)** were extracted. They may be wrong if OCR misread characters or units.')
            st.dataframe([{'Test':k,'Candidate value':v} for k,v in values.items()],hide_index=True,use_container_width=True)
        st.write('Clinical interpretation depends on the correct units, age, personal circumstances, laboratory reference ranges, and symptoms.')
        if verified:st.success('You confirmed the extracted numbers against the report. This does not independently validate the measurements.')
        else:st.warning('Verify all extracted measurements and units before using a screening calculation.')


def explain_imaging(ranked:list[tuple[str,float]],spec,image=None):
    with st.expander('🔎 Explain my AI imaging result',expanded=False):
        if ranked:
            st.write(f'The top reported class was **{ranked[0][0]}**, with raw model score **{ranked[0][1]*100:.1f}%**. '
                     'This score is not a calibrated probability of disease.')
        st.write(f"**Model:** {getattr(spec,'label','Research image model')}")
        st.write(f"**Training domain:** {getattr(spec,'trained_on','Not provided')}")
        st.warning(f"**Limits:** {getattr(spec,'limitation','May not generalise outside training data.')}")
        st.write('The model compares patterns in the uploaded image with patterns learned during training; '
                 'it cannot verify that the selected body part/modality is correct.')
        if image is not None and st.button('Show experimental image attribution',key='medpredict_inline_attribution'):
            try:
                from research_quality import model_saliency
                with st.spinner('Computing model attribution…'):
                    heatmap,_=model_saliency(image,spec)
                st.image(heatmap,caption='Attribution highlights influential pixels, not medically confirmed pathology.',use_container_width=True)
            except Exception as e:
                st.info('Attribution is not available for this model/runtime. No explanation image will be invented.')
        st.caption('Research output only. Consider image quality, data distribution and independent validation.')

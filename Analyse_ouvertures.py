"""Analyses reproductibles: descriptif, chi2, régressions imbriquées, robustesse et export."""
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency, chi2, spearmanr
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
import config_projet as cfg


def chi_test(frame, a, b, label, min_expected=5):
    tab=pd.crosstab(frame[a],frame[b]); n=int(tab.to_numpy().sum())
    if min(tab.shape)<2 or n<10: return {'test':label,'n':n,'chi2':np.nan,'ddl':np.nan,'p':np.nan,'cramer_v':np.nan,'expected_lt5':np.nan,'valid':False}
    try: stat,p,ddl,exp=chi2_contingency(tab)
    except ValueError: return {'test':label,'n':n,'chi2':np.nan,'ddl':np.nan,'p':np.nan,'cramer_v':np.nan,'expected_lt5':np.nan,'valid':False}
    v=np.sqrt(stat/(n*min(tab.shape[0]-1,tab.shape[1]-1)))
    return {'test':label,'n':n,'chi2':stat,'ddl':ddl,'p':p,'cramer_v':v,'expected_lt5':int((exp<min_expected).sum()),'valid':bool((exp>=min_expected).all())}

def run_models(data, formulae, file_prefix, max_n=150000):
    outcomes=[]; details=[]
    # Même échantillon pour les modèles imbriqués, sinon LR/AIC non comparables
    frame=data.copy()
    predictors=set()
    for f in formulae.values():
        for c in ['win','elo_diff','rating','is_white','format_partie','opening_group','experience_log','repeat_same_color','prev_result_same_color','user_id','game_index','elo_band']:
            if c in f: predictors.add(c)
    predictors={c for c in predictors if c in frame}
    frame=frame.dropna(subset=list(predictors))
    if len(frame)>max_n: frame=frame.sample(max_n,random_state=42)
    old=None
    for label,formula in formulae.items():
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                fit=smf.logit(formula,data=frame).fit(disp=False,maxiter=130,cov_type='cluster',cov_kwds={'groups':frame['user_id']})
            lr=2*(fit.llf-old.llf) if old is not None else np.nan
            df_lr=fit.df_model-old.df_model if old is not None else np.nan
            # Tests LR seulement pour modèles imbriqués avec MLE non robustes; ici log-vraisemblance inchangée
            outcomes.append({'model':label,'n':int(fit.nobs),'aic':fit.aic,'bic':fit.bic,'pseudo_r2':fit.prsquared,'LR_vs_previous':lr if df_lr>0 else np.nan,'LR_p':chi2.sf(lr,df_lr) if df_lr>0 else np.nan})
            ci=fit.conf_int(); details.extend([{'model':label,'parameter':k,'beta':v,'OR':np.exp(np.clip(v,-50,50)),'p':fit.pvalues[k],'OR_low':np.exp(np.clip(ci.loc[k,0],-50,50)),'OR_high':np.exp(np.clip(ci.loc[k,1],-50,50))} for k,v in fit.params.items()])
            old=fit
        except Exception as e:
            outcomes.append({'model':label,'n':len(frame),'error':str(e)[:220]}); old=None
    pd.DataFrame(outcomes).to_csv(cfg.RESULTS_DIR/(file_prefix+'_comparaison.csv'),index=False)
    pd.DataFrame(details).to_csv(cfg.RESULTS_DIR/(file_prefix+'_coefficients.csv'),index=False)
    return pd.DataFrame(outcomes)

def analyze(df, run_regressions=False):
    print('Observations',len(df),'joueurs',df.user_id.nunique(),'parties distinctes',df.game_id.nunique())
    diagnostics=pd.DataFrame({'variable':df.columns,'missing_pct':df.isna().mean().values*100})
    diagnostics.to_csv(cfg.RESULTS_DIR/'qualite_donnees.csv',index=False)
    d=df[df['opening_family'].ne('Inconnue')].copy()
    # Limiter aux groupes assez fréquents; Autres reste explicitement visible
    top=d.opening_family.value_counts(); retained=top[top>=max(30,int(len(d)*.005))].index[:12]
    d['opening_group']=np.where(d.opening_family.isin(retained),d.opening_family,'Autres')
    if d.empty: raise ValueError('Aucune ouverture identifiée')
    dims=['opening_group','eco_group','color','format_partie','elo_band','seed_origin']
    tests=[]
    for dim in dims:
        if dim in d:
            group=d.groupby(dim,observed=True).agg(n=('game_id','size'),win_rate=('win','mean'),score_mean=('score','mean'),draw_rate=('is_draw','mean')).reset_index()
            group.to_csv(cfg.RESULTS_DIR/('description_'+dim+'.csv'),index=False)
            tests.append(chi_test(d,dim,'result','result_vs_'+dim))
    for fmt,part in d.groupby('format_partie'):
        tests.append(chi_test(part,'opening_group','result','ouverture_result_'+fmt))
    for color,part in d.groupby('color'):
        tests.append(chi_test(part,'opening_group','result','ouverture_result_'+color))
    for band,part in d.groupby('elo_band',observed=True):
        tests.append(chi_test(part,'opening_group','result','ouverture_result_elo_'+str(band)))
    # Répétition selon résultat précédent, en comparant les parties jouées avec la même couleur
    rep=d.dropna(subset=['prev_result_same_color','repeat_same_color'])
    tests.append(chi_test(rep,'prev_result_same_color','repeat_same_color','result_precedent_vs_repetition'))
    for fmt,sub in rep.groupby('format_partie'):
        tests.append(chi_test(sub,'prev_result_same_color','repeat_same_color','repetition_'+fmt))
    tests.append(chi_test(rep,'repeat_same_color','result','repetition_vs_result_courant'))
    t=pd.DataFrame(tests)
    p=t['p'].notna()
    if p.any(): t.loc[p,'p_fdr_bh']=multipletests(t.loc[p,'p'],method='fdr_bh')[1]
    t.to_csv(cfg.RESULTS_DIR/'tests_chi2.csv',index=False)
    # Hypothèses: M0 couleur; M1 Elo; M2 cadence; M3 famille; M4 expérience; M5 interactions
    # Échantillon commun et erreurs-types robustes par joueur.
    if run_regressions:
        formulas={
          'M0_couleur':'win ~ is_white',
          'M1_plus_Elo':'win ~ is_white + elo_diff',
          'M2_plus_cadence':'win ~ is_white + elo_diff + C(format_partie)',
          'M3_plus_ouverture':'win ~ is_white + elo_diff + C(format_partie) + C(opening_group)',
          'M4_plus_experience':'win ~ is_white + elo_diff + C(format_partie) + C(opening_group) + experience_log',
          'M5_interaction_couleur':'win ~ is_white + elo_diff + C(format_partie) + C(opening_group) + experience_log + is_white:experience_log',
        }
        print(run_models(d,formulas,'modeles_victoire').to_string(index=False))
        rep=rep.copy(); rep['previous_win']=(rep['prev_result_same_color']=='Win').astype(int)
        rep['previous_draw']=(rep['prev_result_same_color']=='Draw').astype(int)
        rep['repeat_same_color']=rep['repeat_same_color'].astype(int)
        rep_models={
          'R0_ancienne_victoire':'repeat_same_color ~ previous_win + previous_draw',
          'R1_plus_Elo':'repeat_same_color ~ previous_win + previous_draw + elo_diff',
          'R2_plus_couleur_cadence':'repeat_same_color ~ previous_win + previous_draw + elo_diff + is_white + C(format_partie)',
          'R3_plus_experience':'repeat_same_color ~ previous_win + previous_draw + elo_diff + is_white + C(format_partie) + experience_log',
        }
        print(run_models(rep,rep_models,'modeles_repetition').to_string(index=False))
        # Contrôle direct du lien répétition / résultat, net d'Elo/cadence/ouverture
        performance={
          'P0_repetition':'win ~ repeat_same_color',
          'P1_plus_couleur':'win ~ repeat_same_color + is_white',
          'P2_plus_Elo':'win ~ repeat_same_color + is_white + elo_diff',
          'P3_plus_cadence':'win ~ repeat_same_color + is_white + elo_diff + C(format_partie)',
          'P4_plus_ouverture_experience':'win ~ repeat_same_color + is_white + elo_diff + C(format_partie) + C(opening_group) + experience_log',
        }
        run_models(rep,performance,'modeles_performance_repetition')
        # Robustesse : nul=demi point, par Elo, et uniquement parties non nulles
        non_draw=d[d.result!='Draw']
        run_models(non_draw,{'sans_nulles':'win ~ is_white + elo_diff + C(format_partie) + C(opening_group) + experience_log'},'robustesse_sans_nulles')
    # Descriptif temporel: courbe expérience ex ante
    d['experience_bin']=pd.cut(d.experience_opening_prior,bins=[-1,0,1,2,4,9,19,49,999999],labels=['1','2','3','4-5','6-10','11-20','21-50','51+'])
    exp=d.groupby('experience_bin',observed=True).agg(n=('win','size'),score_mean=('score','mean'),win_rate=('win','mean')).reset_index()
    exp.to_csv(cfg.RESULTS_DIR/'experience_progression.csv',index=False)
    fig,ax=plt.subplots(figsize=(8,4)); ax.plot(exp.experience_bin.astype(str),exp.score_mean,marker='o'); ax.set(xlabel='Rang de pratique de la famille (même couleur)',ylabel='Score moyen',title='Expérience et résultat brut (non causal)'); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(cfg.RESULTS_DIR/'experience_score.png',dpi=180); plt.close(fig)
    # Écart au score attendu Elo selon famille, descriptif complémentaire
    e=d.dropna(subset=['expected_score']).copy(); e['score_surprise']=e.score-e.expected_score
    e.groupby('opening_group').agg(n=('score','size'),mean_surprise=('score_surprise','mean')).reset_index().to_csv(cfg.RESULTS_DIR/'surperformance_elo.csv',index=False)
    # Résumé non fabriqué: toute conclusion doit venir des sorties effectives
    (cfg.RESULTS_DIR/'LECTURE_RESULTATS.md').write_text('''# Comment interpréter les sorties\n\nLes régressions sont optionnelles : leurs fichiers existent uniquement si analyze(df, run_regressions=True) est appelé.\n\n- `tests_chi2.csv` : **p_fdr_bh** corrige la multiplicité des tests. Le test chi² est fragile si `valid=False` (effectifs théoriques < 5). Le V de Cramér mesure la taille de l’association.\n- `modeles_victoire_comparaison.csv` : comparer M0 à M5 sur un **échantillon identique** ; baisse d’AIC et LR positif documentent le gain d’ajustement, pas la causalité.\n- `modeles_victoire_coefficients.csv` : OR >1 indique une augmentation des odds conditionnelles. Les interactions se lisent conditionnellement.\n- `modeles_repetition_coefficients.csv` : coefficient de `previous_win` pour rejouer une ouverture après un succès antérieur, comparativement à une défaite.\n- `modeles_performance_repetition_coefficients.csv` : coefficient de `repeat_same_color` pour la performance après répétition.\n- `experience_progression.csv` : comparaison brute par ancienneté ; attention sélection et survie des ouvertures.\n- `surperformance_elo.csv` : score moins score attendu Elo ; estimation descriptive, pas causale.\n- Vérifier la stabilité sur plusieurs périodes, graines et répartitions Elo. Les observations appartenant au même joueur ne sont pas indépendantes ; écarts-types cluster par joueur.\n- Les modèles logistiques traitent une partie nulle comme non-victoire ; contrôler la fréquence des nulles en parallèle, puis refaire sur les parties décisives.\n''',encoding='utf-8')
    return t
if __name__=='__main__':
    d=pd.read_parquet(cfg.DATA_DIR/'games_clean.parquet'); analyze(d)

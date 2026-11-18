clear all
set more off
set type double
capture log close
log using "replicar_indices_comparables_stata.log", text replace
use "indices_comparables_micro.dta", clear
postfile audit str20 familia str20 modelo str20 resultado str30 parametro double coef se p nobs clusters using "replica_indices_aioe_stata.dta", replace
foreach y in desempleo no_cotiza salario {
 gen expo = aioe_pct
 gen expo_post = expo*post
 quietly regress `y' expo expo_post edad edad2 mujer rural jefe i.dpto i.anio i.oficio_2d i.edu_cat [pw=FEX_C], vce(cluster ciuo08)
 post audit ("did") ("estatico") ("`y'") ("exposicion_post") (_b[expo_post]) (_se[expo_post]) (2*ttail(e(df_r),abs(_b[expo_post]/_se[expo_post]))) (e(N)) (e(N_clust))
 gen expo_2021=expo*(anio==2021)
 forvalues yr=2023/2025 {
 gen expo_`yr'=expo*(anio==`yr')
 }
 quietly regress `y' expo expo_2021 expo_2023 expo_2024 expo_2025 edad edad2 mujer rural jefe i.dpto i.anio i.oficio_2d i.edu_cat [pw=FEX_C], vce(cluster ciuo08)
 post audit ("did") ("dinamico") ("`y'") ("exposicion_2021") (_b[expo_2021]) (_se[expo_2021]) (2*ttail(e(df_r),abs(_b[expo_2021]/_se[expo_2021]))) (e(N)) (e(N_clust))
 forvalues yr=2023/2025 {
 post audit ("did") ("dinamico") ("`y'") ("exposicion_`yr'") (_b[expo_`yr']) (_se[expo_`yr']) (2*ttail(e(df_r),abs(_b[expo_`yr']/_se[expo_`yr']))) (e(N)) (e(N_clust))
 }
 foreach h in H_tic H_edu {
 gen expo_h=expo*`h'
 gen post_h=post*`h'
 gen triple=expo*post*`h'
 local edu "i.edu_cat"
 if "`h'"=="H_tic" local edu "i.edu_cat"
 quietly regress `y' expo expo_post expo_h post_h triple `h' edad edad2 mujer rural jefe i.dpto i.anio i.oficio_2d `edu' [pw=FEX_C], vce(cluster ciuo08)
 post audit ("ddd") ("`h'") ("`y'") ("exposicion_post") (_b[expo_post]) (_se[expo_post]) (2*ttail(e(df_r),abs(_b[expo_post]/_se[expo_post]))) (e(N)) (e(N_clust))
 post audit ("ddd") ("`h'") ("`y'") ("triple") (_b[triple]) (_se[triple]) (2*ttail(e(df_r),abs(_b[triple]/_se[triple]))) (e(N)) (e(N_clust))
 quietly lincom expo_post+triple
 post audit ("ddd") ("`h'") ("`y'") ("exposicion_post_H1") (r(estimate)) (r(se)) (r(p)) (e(N)) (e(N_clust))
 drop expo_h post_h triple
 }
 drop expo expo_post expo_2021 expo_2023 expo_2024 expo_2025
}
use "indices_comparables_panel.dta",clear
encode id_cohorte,gen(coh)
foreach y in desempleo no_cotiza salario {
 foreach source in d c {
 gen expo_post=aioe_pct_`source'*post
 quietly regress `y' expo_post edad_media prop_rural prop_edu_universitaria i.coh i.anio [pw=n_obs_pet],vce(cluster departamento)
 local family="shiftshare"
 local model="estatico"
 if "`source'"=="c" local family="panel"
 if "`source'"=="c" local model="within"
 post audit ("`family'") ("`model'") ("`y'") ("exposicion_post") (_b[expo_post]) (_se[expo_post]) (2*ttail(e(df_r),abs(_b[expo_post]/_se[expo_post]))) (e(N)) (e(N_clust))
 drop expo_post
 }
 gen expo_2021=aioe_pct_d*(anio==2021)
 forvalues yr=2023/2025 {
 gen expo_`yr'=aioe_pct_d*(anio==`yr')
 }
 quietly regress `y' expo_2021 expo_2023 expo_2024 expo_2025 edad_media prop_rural prop_edu_universitaria i.coh i.anio [pw=n_obs_pet],vce(cluster departamento)
 post audit ("shiftshare") ("dinamico") ("`y'") ("exposicion_2021") (_b[expo_2021]) (_se[expo_2021]) (2*ttail(e(df_r),abs(_b[expo_2021]/_se[expo_2021]))) (e(N)) (e(N_clust))
 forvalues yr=2023/2025 {
 post audit ("shiftshare") ("dinamico") ("`y'") ("exposicion_`yr'") (_b[expo_`yr']) (_se[expo_`yr']) (2*ttail(e(df_r),abs(_b[expo_`yr']/_se[expo_`yr']))) (e(N)) (e(N_clust))
 }
 drop expo_2021 expo_2023 expo_2024 expo_2025
 preserve
 keep if inlist(anio,2022,2025)
 sort coh anio
 foreach v in `y' edad_media prop_rural prop_edu_universitaria {
 by coh: gen d_`v'=`v'-`v'[1]
 }
 by coh:gen peso=(n_obs_pet+n_obs_pet[1])/2
 keep if anio==2025
 quietly regress d_`y' aioe_pct_c d_edad_media d_prop_rural d_prop_edu_universitaria [pw=peso],vce(cluster departamento)
 post audit ("panel") ("fd") ("`y'") ("exposicion_post") (_b[aioe_pct_c]) (_se[aioe_pct_c]) (2*ttail(e(df_r),abs(_b[aioe_pct_c]/_se[aioe_pct_c]))) (e(N)) (e(N_clust))
 restore
}
postclose audit
use replica_indices_aioe_stata.dta,clear
export delimited using "replica_indices_aioe_stata.csv",replace
log close

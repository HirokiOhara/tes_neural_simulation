/* Created by Language version: 7.7.0 */
/* VECTORIZED */
#define NRN_VECTORIZED 1
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "mech_api.h"
#undef PI
#define nil 0
#include "md1redef.h"
#include "section.h"
#include "nrniv_mf.h"
#include "md2redef.h"
 
#if METHOD3
extern int _method3;
#endif

#if !NRNGPU
#undef exp
#define exp hoc_Exp
extern double hoc_Exp(double);
#endif
 
#define nrn_init _nrn_init__hcn
#define _nrn_initial _nrn_initial__hcn
#define nrn_cur _nrn_cur__hcn
#define _nrn_current _nrn_current__hcn
#define nrn_jacob _nrn_jacob__hcn
#define nrn_state _nrn_state__hcn
#define _net_receive _net_receive__hcn 
#define _f_rates _f_rates__hcn 
#define rates rates__hcn 
#define states states__hcn 
 
#define _threadargscomma_ _p, _ppvar, _thread, _nt,
#define _threadargsprotocomma_ double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt,
#define _threadargs_ _p, _ppvar, _thread, _nt
#define _threadargsproto_ double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt
 	/*SUPPRESS 761*/
	/*SUPPRESS 762*/
	/*SUPPRESS 763*/
	/*SUPPRESS 765*/
	 extern double *getarg();
 /* Thread safe. No static _p or _ppvar. */
 
#define t _nt->_t
#define dt _nt->_dt
#define gbar _p[0]
#define gbar_columnindex 0
#define ekna _p[1]
#define ekna_columnindex 1
#define g_s _p[2]
#define g_s_columnindex 2
#define g_f _p[3]
#define g_f_columnindex 3
#define q10 _p[4]
#define q10_columnindex 4
#define ik _p[5]
#define ik_columnindex 5
#define ina _p[6]
#define ina_columnindex 6
#define ih _p[7]
#define ih_columnindex 7
#define g _p[8]
#define g_columnindex 8
#define gp _p[9]
#define gp_columnindex 9
#define tau_m _p[10]
#define tau_m_columnindex 10
#define tau_n _p[11]
#define tau_n_columnindex 11
#define ninf _p[12]
#define ninf_columnindex 12
#define minf _p[13]
#define minf_columnindex 13
#define m _p[14]
#define m_columnindex 14
#define n _p[15]
#define n_columnindex 15
#define ek _p[16]
#define ek_columnindex 16
#define ena _p[17]
#define ena_columnindex 17
#define ki _p[18]
#define ki_columnindex 18
#define ko _p[19]
#define ko_columnindex 19
#define nai _p[20]
#define nai_columnindex 20
#define nao _p[21]
#define nao_columnindex 21
#define Dm _p[22]
#define Dm_columnindex 22
#define Dn _p[23]
#define Dn_columnindex 23
#define v _p[24]
#define v_columnindex 24
#define _g _p[25]
#define _g_columnindex 25
#define _ion_ek	*_ppvar[0]._pval
#define _ion_ko	*_ppvar[1]._pval
#define _ion_ki	*_ppvar[2]._pval
#define _ion_ik	*_ppvar[3]._pval
#define _ion_dikdv	*_ppvar[4]._pval
#define _ion_ena	*_ppvar[5]._pval
#define _ion_nao	*_ppvar[6]._pval
#define _ion_nai	*_ppvar[7]._pval
#define _ion_ina	*_ppvar[8]._pval
#define _ion_dinadv	*_ppvar[9]._pval
 
#if MAC
#if !defined(v)
#define v _mlhv
#endif
#if !defined(h)
#define h _mlhh
#endif
#endif
 
#if defined(__cplusplus)
extern "C" {
#endif
 static int hoc_nrnpointerindex =  -1;
 static Datum* _extcall_thread;
 static Prop* _extcall_prop;
 /* external NEURON variables */
 extern double celsius;
 /* declaration of user functions */
 static void _hoc_rates(void);
 static int _mechtype;
extern void _nrn_cacheloop_reg(int, int);
extern void hoc_register_prop_size(int, int, int);
extern void hoc_register_limits(int, HocParmLimits*);
extern void hoc_register_units(int, HocParmUnits*);
extern void nrn_promote(Prop*, int, int);
extern Memb_func* memb_func;
 
#define NMODL_TEXT 1
#if NMODL_TEXT
static const char* nmodl_file_text;
static const char* nmodl_filename;
extern void hoc_reg_nmodl_text(int, const char*);
extern void hoc_reg_nmodl_filename(int, const char*);
#endif

 extern void _nrn_setdata_reg(int, void(*)(Prop*));
 static void _setdata(Prop* _prop) {
 _extcall_prop = _prop;
 }
 static void _hoc_setdata() {
 Prop *_prop, *hoc_getdata_range(int);
 _prop = hoc_getdata_range(_mechtype);
   _setdata(_prop);
 hoc_retpushx(1.);
}
 /* connect user functions to hoc names */
 static VoidFunc hoc_intfunc[] = {
 "setdata_hcn", _hoc_setdata,
 "rates_hcn", _hoc_rates,
 0, 0
};
 
static void _check_rates(double*, Datum*, Datum*, NrnThread*); 
static void _check_table_thread(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, int _type) {
   _check_rates(_p, _ppvar, _thread, _nt);
 }
 /* declare global and static user variables */
#define usetable usetable_hcn
 double usetable = 1;
 /* some parameters have upper and lower limits */
 static HocParmLimits _hoc_parm_limits[] = {
 "usetable_hcn", 0, 1,
 0,0,0
};
 static HocParmUnits _hoc_parm_units[] = {
 "gbar_hcn", "S/cm2",
 "ekna_hcn", "mV",
 "ik_hcn", "mA/cm2",
 "ina_hcn", "mA/cm2",
 "ih_hcn", "mA/cm2",
 "g_hcn", "S/cm2",
 "tau_m_hcn", "ms",
 "tau_n_hcn", "ms",
 0,0
};
 static double delta_t = 0.01;
 static double m0 = 0;
 static double n0 = 0;
 /* connect global user variables to hoc */
 static DoubScal hoc_scdoub[] = {
 "usetable_hcn", &usetable_hcn,
 0,0
};
 static DoubVec hoc_vdoub[] = {
 0,0,0
};
 static double _sav_indep;
 static void nrn_alloc(Prop*);
static void  nrn_init(NrnThread*, _Memb_list*, int);
static void nrn_state(NrnThread*, _Memb_list*, int);
 static void nrn_cur(NrnThread*, _Memb_list*, int);
static void  nrn_jacob(NrnThread*, _Memb_list*, int);
 
static int _ode_count(int);
static void _ode_map(int, double**, double**, double*, Datum*, double*, int);
static void _ode_spec(NrnThread*, _Memb_list*, int);
static void _ode_matsol(NrnThread*, _Memb_list*, int);
 
#define _cvode_ieq _ppvar[10]._i
 static void _ode_matsol_instance1(_threadargsproto_);
 /* connect range variables in _p that hoc is supposed to know about */
 static const char *_mechanism[] = {
 "7.7.0",
"hcn",
 "gbar_hcn",
 "ekna_hcn",
 "g_s_hcn",
 "g_f_hcn",
 "q10_hcn",
 0,
 "ik_hcn",
 "ina_hcn",
 "ih_hcn",
 "g_hcn",
 "gp_hcn",
 "tau_m_hcn",
 "tau_n_hcn",
 "ninf_hcn",
 "minf_hcn",
 0,
 "m_hcn",
 "n_hcn",
 0,
 0};
 static Symbol* _k_sym;
 static Symbol* _na_sym;
 
extern Prop* need_memb(Symbol*);

static void nrn_alloc(Prop* _prop) {
	Prop *prop_ion;
	double *_p; Datum *_ppvar;
 	_p = nrn_prop_data_alloc(_mechtype, 26, _prop);
 	/*initialize range parameters*/
 	gbar = 0;
 	ekna = -30;
 	g_s = 0.25;
 	g_f = 0.75;
 	q10 = 3;
 	_prop->param = _p;
 	_prop->param_size = 26;
 	_ppvar = nrn_prop_datum_alloc(_mechtype, 11, _prop);
 	_prop->dparam = _ppvar;
 	/*connect ionic variables to this model*/
 prop_ion = need_memb(_k_sym);
 nrn_promote(prop_ion, 1, 1);
 	_ppvar[0]._pval = &prop_ion->param[0]; /* ek */
 	_ppvar[1]._pval = &prop_ion->param[2]; /* ko */
 	_ppvar[2]._pval = &prop_ion->param[1]; /* ki */
 	_ppvar[3]._pval = &prop_ion->param[3]; /* ik */
 	_ppvar[4]._pval = &prop_ion->param[4]; /* _ion_dikdv */
 prop_ion = need_memb(_na_sym);
 nrn_promote(prop_ion, 1, 1);
 	_ppvar[5]._pval = &prop_ion->param[0]; /* ena */
 	_ppvar[6]._pval = &prop_ion->param[2]; /* nao */
 	_ppvar[7]._pval = &prop_ion->param[1]; /* nai */
 	_ppvar[8]._pval = &prop_ion->param[3]; /* ina */
 	_ppvar[9]._pval = &prop_ion->param[4]; /* _ion_dinadv */
 
}
 static void _initlists();
  /* some states have an absolute tolerance */
 static Symbol** _atollist;
 static HocStateTolerance _hoc_state_tol[] = {
 0,0
};
 static void _update_ion_pointer(Datum*);
 extern Symbol* hoc_lookup(const char*);
extern void _nrn_thread_reg(int, int, void(*)(Datum*));
extern void _nrn_thread_table_reg(int, void(*)(double*, Datum*, Datum*, NrnThread*, int));
extern void hoc_register_tolerance(int, HocStateTolerance*, Symbol***);
extern void _cvode_abstol( Symbol**, double*, int);

 void _HCN_reg() {
	int _vectorized = 1;
  _initlists();
 	ion_reg("k", -10000.);
 	ion_reg("na", -10000.);
 	_k_sym = hoc_lookup("k_ion");
 	_na_sym = hoc_lookup("na_ion");
 	register_mech(_mechanism, nrn_alloc,nrn_cur, nrn_jacob, nrn_state, nrn_init, hoc_nrnpointerindex, 1);
 _mechtype = nrn_get_mechtype(_mechanism[1]);
     _nrn_setdata_reg(_mechtype, _setdata);
     _nrn_thread_reg(_mechtype, 2, _update_ion_pointer);
     _nrn_thread_table_reg(_mechtype, _check_table_thread);
 #if NMODL_TEXT
  hoc_reg_nmodl_text(_mechtype, nmodl_file_text);
  hoc_reg_nmodl_filename(_mechtype, nmodl_filename);
#endif
  hoc_register_prop_size(_mechtype, 26, 11);
  hoc_register_dparam_semantics(_mechtype, 0, "k_ion");
  hoc_register_dparam_semantics(_mechtype, 1, "k_ion");
  hoc_register_dparam_semantics(_mechtype, 2, "k_ion");
  hoc_register_dparam_semantics(_mechtype, 3, "k_ion");
  hoc_register_dparam_semantics(_mechtype, 4, "k_ion");
  hoc_register_dparam_semantics(_mechtype, 5, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 6, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 7, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 8, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 9, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 10, "cvodeieq");
 	hoc_register_cvode(_mechtype, _ode_count, _ode_map, _ode_spec, _ode_matsol);
 	hoc_register_tolerance(_mechtype, _hoc_state_tol, &_atollist);
 	hoc_register_var(hoc_scdoub, hoc_vdoub, hoc_intfunc);
 	ivoc_help("help ?1 hcn HCN.mod\n");
 hoc_register_limits(_mechtype, _hoc_parm_limits);
 hoc_register_units(_mechtype, _hoc_parm_units);
 }
 static double *_t_minf;
 static double *_t_ninf;
 static double *_t_tau_m;
 static double *_t_tau_n;
static int _reset;
static char *modelname = "";

static int error;
static int _ninits = 0;
static int _match_recurse=1;
static void _modl_cleanup(){ _match_recurse=1;}
static int _f_rates(_threadargsprotocomma_ double);
static int rates(_threadargsprotocomma_ double);
 
static int _ode_spec1(_threadargsproto_);
/*static int _ode_matsol1(_threadargsproto_);*/
 static void _n_rates(_threadargsprotocomma_ double _lv);
 static int _slist1[2], _dlist1[2];
 static int states(_threadargsproto_);
 
/*CVODE*/
 static int _ode_spec1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {int _reset = 0; {
   rates ( _threadargscomma_ v ) ;
   Dm = ( minf - m ) / ( tau_m ) ;
   Dn = ( ninf - n ) / ( tau_n ) ;
   }
 return _reset;
}
 static int _ode_matsol1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
 rates ( _threadargscomma_ v ) ;
 Dm = Dm  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( tau_m ) )) ;
 Dn = Dn  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( tau_n ) )) ;
  return 0;
}
 /*END CVODE*/
 static int states (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) { {
   rates ( _threadargscomma_ v ) ;
    m = m + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( tau_m ))))*(- ( ( ( minf ) ) / ( tau_m ) ) / ( ( ( ( - 1.0 ) ) ) / ( tau_m ) ) - m) ;
    n = n + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( tau_n ))))*(- ( ( ( ninf ) ) / ( tau_n ) ) / ( ( ( ( - 1.0 ) ) ) / ( tau_n ) ) - n) ;
   }
  return 0;
}
 static double _mfac_rates, _tmin_rates;
  static void _check_rates(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
  static int _maktable=1; int _i, _j, _ix = 0;
  double _xi, _tmax;
  static double _sav_celsius;
  if (!usetable) {return;}
  if (_sav_celsius != celsius) { _maktable = 1;}
  if (_maktable) { double _x, _dx; _maktable=0;
   _tmin_rates =  - 120.0 ;
   _tmax =  100.0 ;
   _dx = (_tmax - _tmin_rates)/440.; _mfac_rates = 1./_dx;
   for (_i=0, _x=_tmin_rates; _i < 441; _x += _dx, _i++) {
    _f_rates(_p, _ppvar, _thread, _nt, _x);
    _t_minf[_i] = minf;
    _t_ninf[_i] = ninf;
    _t_tau_m[_i] = tau_m;
    _t_tau_n[_i] = tau_n;
   }
   _sav_celsius = celsius;
  }
 }

 static int rates(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, double _lVm) { 
#if 0
_check_rates(_p, _ppvar, _thread, _nt);
#endif
 _n_rates(_p, _ppvar, _thread, _nt, _lVm);
 return 0;
 }

 static void _n_rates(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, double _lVm){ int _i, _j;
 double _xi, _theta;
 if (!usetable) {
 _f_rates(_p, _ppvar, _thread, _nt, _lVm); return; 
}
 _xi = _mfac_rates * (_lVm - _tmin_rates);
 if (isnan(_xi)) {
  minf = _xi;
  ninf = _xi;
  tau_m = _xi;
  tau_n = _xi;
  return;
 }
 if (_xi <= 0.) {
 minf = _t_minf[0];
 ninf = _t_ninf[0];
 tau_m = _t_tau_m[0];
 tau_n = _t_tau_n[0];
 return; }
 if (_xi >= 440.) {
 minf = _t_minf[440];
 ninf = _t_ninf[440];
 tau_m = _t_tau_m[440];
 tau_n = _t_tau_n[440];
 return; }
 _i = (int) _xi;
 _theta = _xi - (double)_i;
 minf = _t_minf[_i] + _theta*(_t_minf[_i+1] - _t_minf[_i]);
 ninf = _t_ninf[_i] + _theta*(_t_ninf[_i+1] - _t_ninf[_i]);
 tau_m = _t_tau_m[_i] + _theta*(_t_tau_m[_i+1] - _t_tau_m[_i]);
 tau_n = _t_tau_n[_i] + _theta*(_t_tau_n[_i+1] - _t_tau_n[_i]);
 }

 
static int  _f_rates ( _threadargsprotocomma_ double _lVm ) {
   double _lQ10 ;
  _lQ10 = pow( q10 , ( ( celsius - 22.0 ) / 10.0 ) ) ;
   minf = pow( ( 1.0 / ( 1.0 + exp ( ( _lVm + 97.0 ) / 7.35 ) ) ) , ( 1.0 / 3.0 ) ) ;
   ninf = pow( ( 1.0 / ( 1.0 + exp ( ( _lVm + 94.0 ) / 8.9 ) ) ) , ( 1.0 / 3.0 ) ) ;
   tau_m = 0.5 / ( exp ( ( _lVm - 42.0 ) / 11.8 ) + exp ( - 1.0 * ( _lVm + 498.0 ) / 66.6 ) ) ;
   tau_n = 0.5 / ( exp ( ( _lVm + 25.0 ) / 4.1 ) + exp ( - 1.0 * ( _lVm + 356.0 ) / 32.0 ) ) ;
   tau_m = tau_m / _lQ10 ;
   tau_n = tau_n / _lQ10 ;
     return 0; }
 
static void _hoc_rates(void) {
  double _r;
   double* _p; Datum* _ppvar; Datum* _thread; NrnThread* _nt;
   if (_extcall_prop) {_p = _extcall_prop->param; _ppvar = _extcall_prop->dparam;}else{ _p = (double*)0; _ppvar = (Datum*)0; }
  _thread = _extcall_thread;
  _nt = nrn_threads;
 
#if 1
 _check_rates(_p, _ppvar, _thread, _nt);
#endif
 _r = 1.;
 rates ( _p, _ppvar, _thread, _nt, *getarg(1) );
 hoc_retpushx(_r);
}
 
static int _ode_count(int _type){ return 2;}
 
static void _ode_spec(NrnThread* _nt, _Memb_list* _ml, int _type) {
   double* _p; Datum* _ppvar; Datum* _thread;
   Node* _nd; double _v; int _iml, _cntml;
  _cntml = _ml->_nodecount;
  _thread = _ml->_thread;
  for (_iml = 0; _iml < _cntml; ++_iml) {
    _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
    _nd = _ml->_nodelist[_iml];
    v = NODEV(_nd);
  ek = _ion_ek;
  ko = _ion_ko;
  ki = _ion_ki;
  ena = _ion_ena;
  nao = _ion_nao;
  nai = _ion_nai;
     _ode_spec1 (_p, _ppvar, _thread, _nt);
   }}
 
static void _ode_map(int _ieq, double** _pv, double** _pvdot, double* _pp, Datum* _ppd, double* _atol, int _type) { 
	double* _p; Datum* _ppvar;
 	int _i; _p = _pp; _ppvar = _ppd;
	_cvode_ieq = _ieq;
	for (_i=0; _i < 2; ++_i) {
		_pv[_i] = _pp + _slist1[_i];  _pvdot[_i] = _pp + _dlist1[_i];
		_cvode_abstol(_atollist, _atol, _i);
	}
 }
 
static void _ode_matsol_instance1(_threadargsproto_) {
 _ode_matsol1 (_p, _ppvar, _thread, _nt);
 }
 
static void _ode_matsol(NrnThread* _nt, _Memb_list* _ml, int _type) {
   double* _p; Datum* _ppvar; Datum* _thread;
   Node* _nd; double _v; int _iml, _cntml;
  _cntml = _ml->_nodecount;
  _thread = _ml->_thread;
  for (_iml = 0; _iml < _cntml; ++_iml) {
    _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
    _nd = _ml->_nodelist[_iml];
    v = NODEV(_nd);
  ek = _ion_ek;
  ko = _ion_ko;
  ki = _ion_ki;
  ena = _ion_ena;
  nao = _ion_nao;
  nai = _ion_nai;
 _ode_matsol_instance1(_threadargs_);
 }}
 extern void nrn_update_ion_pointer(Symbol*, Datum*, int, int);
 static void _update_ion_pointer(Datum* _ppvar) {
   nrn_update_ion_pointer(_k_sym, _ppvar, 0, 0);
   nrn_update_ion_pointer(_k_sym, _ppvar, 1, 2);
   nrn_update_ion_pointer(_k_sym, _ppvar, 2, 1);
   nrn_update_ion_pointer(_k_sym, _ppvar, 3, 3);
   nrn_update_ion_pointer(_k_sym, _ppvar, 4, 4);
   nrn_update_ion_pointer(_na_sym, _ppvar, 5, 0);
   nrn_update_ion_pointer(_na_sym, _ppvar, 6, 2);
   nrn_update_ion_pointer(_na_sym, _ppvar, 7, 1);
   nrn_update_ion_pointer(_na_sym, _ppvar, 8, 3);
   nrn_update_ion_pointer(_na_sym, _ppvar, 9, 4);
 }

static void initmodel(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
  int _i; double _save;{
  m = m0;
  n = n0;
 {
   rates ( _threadargscomma_ v ) ;
   m = minf ;
   n = ninf ;
   }
 
}
}

static void nrn_init(NrnThread* _nt, _Memb_list* _ml, int _type){
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; double _v; int* _ni; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];

#if 0
 _check_rates(_p, _ppvar, _thread, _nt);
#endif
#if CACHEVEC
  if (use_cachevec) {
    _v = VEC_V(_ni[_iml]);
  }else
#endif
  {
    _nd = _ml->_nodelist[_iml];
    _v = NODEV(_nd);
  }
 v = _v;
  ek = _ion_ek;
  ko = _ion_ko;
  ki = _ion_ki;
  ena = _ion_ena;
  nao = _ion_nao;
  nai = _ion_nai;
 initmodel(_p, _ppvar, _thread, _nt);
  }
}

static double _nrn_current(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, double _v){double _current=0.;v=_v;{ {
   gp = ( g_s * n * n * n + g_f * m * m * m ) ;
   g = gbar * gp ;
   ina = ( ekna - ek ) * g * ( v - ena ) / ( ena - ek ) ;
   ik = ( ekna - ena ) * g * ( v - ek ) / ( ek - ena ) ;
   ih = ina + ik ;
   }
 _current += ik;
 _current += ina;

} return _current;
}

static void nrn_cur(NrnThread* _nt, _Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; int* _ni; double _rhs, _v; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
#if CACHEVEC
  if (use_cachevec) {
    _v = VEC_V(_ni[_iml]);
  }else
#endif
  {
    _nd = _ml->_nodelist[_iml];
    _v = NODEV(_nd);
  }
  ek = _ion_ek;
  ko = _ion_ko;
  ki = _ion_ki;
  ena = _ion_ena;
  nao = _ion_nao;
  nai = _ion_nai;
 _g = _nrn_current(_p, _ppvar, _thread, _nt, _v + .001);
 	{ double _dina;
 double _dik;
  _dik = ik;
  _dina = ina;
 _rhs = _nrn_current(_p, _ppvar, _thread, _nt, _v);
  _ion_dikdv += (_dik - ik)/.001 ;
  _ion_dinadv += (_dina - ina)/.001 ;
 	}
 _g = (_g - _rhs)/.001;
  _ion_ik += ik ;
  _ion_ina += ina ;
#if CACHEVEC
  if (use_cachevec) {
	VEC_RHS(_ni[_iml]) -= _rhs;
  }else
#endif
  {
	NODERHS(_nd) -= _rhs;
  }
 
}
 
}

static void nrn_jacob(NrnThread* _nt, _Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; int* _ni; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml];
#if CACHEVEC
  if (use_cachevec) {
	VEC_D(_ni[_iml]) += _g;
  }else
#endif
  {
     _nd = _ml->_nodelist[_iml];
	NODED(_nd) += _g;
  }
 
}
 
}

static void nrn_state(NrnThread* _nt, _Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; double _v = 0.0; int* _ni; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
 _nd = _ml->_nodelist[_iml];
#if CACHEVEC
  if (use_cachevec) {
    _v = VEC_V(_ni[_iml]);
  }else
#endif
  {
    _nd = _ml->_nodelist[_iml];
    _v = NODEV(_nd);
  }
 v=_v;
{
  ek = _ion_ek;
  ko = _ion_ko;
  ki = _ion_ki;
  ena = _ion_ena;
  nao = _ion_nao;
  nai = _ion_nai;
 {   states(_p, _ppvar, _thread, _nt);
  }  }}

}

static void terminal(){}

static void _initlists(){
 double _x; double* _p = &_x;
 int _i; static int _first = 1;
  if (!_first) return;
 _slist1[0] = m_columnindex;  _dlist1[0] = Dm_columnindex;
 _slist1[1] = n_columnindex;  _dlist1[1] = Dn_columnindex;
   _t_minf = makevector(441*sizeof(double));
   _t_ninf = makevector(441*sizeof(double));
   _t_tau_m = makevector(441*sizeof(double));
   _t_tau_n = makevector(441*sizeof(double));
_first = 0;
}

#if defined(__cplusplus)
} /* extern "C" */
#endif

#if NMODL_TEXT
static const char* nmodl_filename = "HCN.mod";
static const char* nmodl_file_text = 
  ": h.mod is the h channel \n"
  ": from Tom Andersson Sensitivity studies of voltage-dpendent conductance in neurons\n"
  ": Tom has build his model on Kouranova 2008 Hyoerpolarization -activated cyclic nuleotide-gated channel mRNA and protein expression in large versus mall diameter dorsal root ganglion neurons: correlation with hyperpolarization-activated current\n"
  ": Adopted and altered by Nathan Titus (small changes in relative ik/ina and reversal potentials\n"
  "\n"
  "NEURON {\n"
  "	SUFFIX hcn\n"
  "	USEION k READ ek, ko, ki WRITE ik\n"
  "        USEION na READ ena, nao, nai WRITE ina\n"
  "	RANGE gbar, ena, ik, ina, ek, ekna, g_s, g_f, ih\n"
  "	RANGE minf, ninf, m, n, gp, g, q10, tau_n, tau_m\n"
  "}\n"
  "\n"
  "UNITS {\n"
  "	(molar) = (1/liter)			: moles do not appear in units\n"
  "	(mM)	= (millimolar)\n"
  "	(S) = (siemens)\n"
  "	(mV) = (millivolts)\n"
  "	(mA) = (milliamp)\n"
  "}\n"
  "\n"
  "PARAMETER {\n"
  "	gbar	(S/cm2): = 30e-6\n"
  "	ekna = -30   (mV): the combined rev pot from Na and k\n"
  "	:g_s	= 0.67\n"
  "	:g_f	= 0.33\n"
  "	g_s = .25\n"
  "	g_f = .75\n"
  "	q10 = 3\n"
  "	\n"
  "}\n"
  "\n"
  "ASSIGNED {\n"
  "	v	(mV) : NEURON provides this\n"
  "	ik	(mA/cm2)\n"
  "    ina     (mA/cm2)\n"
  "	ih  (mA/cm2)\n"
  "	g	(S/cm2)\n"
  "	gp\n"
  "	\n"
  "	tau_m	(ms)\n"
  "    tau_n (ms)\n"
  "	ninf\n"
  "    minf\n"
  "    :    kh\n"
  "	ek	(mV)\n"
  "	ena	(mV)\n"
  "	ki	(mM)\n"
  "	ko	(mM)\n"
  "	nai	(mM)\n"
  "	nao	(mM)\n"
  "	celsius (degC)\n"
  "}\n"
  "\n"
  "STATE { m n }\n"
  "\n"
  "BREAKPOINT {\n"
  "	SOLVE states METHOD cnexp\n"
  "	gp = (g_s*n*n*n+g_f*m*m*m)\n"
  "	g = gbar * gp\n"
  "    ina=(ekna-ek)*g*(v-ena)/(ena-ek)\n"
  "    ik=(ekna-ena)*g*(v-ek)/(ek-ena)\n"
  "	ih = ina+ik\n"
  "    : This math looks complicated but it is just parallel \n"
  "	: conductance model math to set the reversal potential \n"
  "	: of the channel to ekna based on the relative proportion\n"
  "	: of ik and ina\n"
  "}\n"
  "\n"
  "INITIAL {\n"
  "	: assume that equilibrium has been reached\n"
  "	rates(v)\n"
  "	m = minf\n"
  "    n = ninf\n"
  "\n"
  "}\n"
  " \n"
  "DERIVATIVE states {\n"
  "	rates(v)\n"
  "	m' = (minf - m)/(tau_m)\n"
  "    n' = (ninf - n)/(tau_n)\n"
  "\n"
  "}\n"
  "\n"
  "? rates\n"
  "PROCEDURE rates(Vm (mV)) (/ms) {\n"
  "	LOCAL Q10\n"
  "	TABLE minf,ninf,tau_m,tau_n DEPEND celsius FROM -120 TO 100 WITH 440\n"
  "UNITSOFF	\n"
  "	Q10 = q10^((celsius-22)/10)\n"
  "\n"
  "	minf = (1/(1+exp((Vm+97)/7.35)))^(1/3)\n"
  "    ninf = (1/(1+exp((Vm+94)/8.9)))^(1/3)\n"
  "\n"
  "    tau_m = 0.5/(exp((Vm-42)/11.8)+exp(-1*(Vm+498)/66.6))\n"
  "    \n"
  "    tau_n= 0.5/(exp((Vm+25)/4.1)+exp(-1*(Vm+356)/32))\n"
  "   \n"
  "	tau_m=tau_m/Q10\n"
  "    tau_n=tau_n/Q10\n"
  "UNITSON\n"
  "\n"
  "  \n"
  "}\n"
  ;
#endif

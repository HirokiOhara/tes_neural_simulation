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
 
#define nrn_init _nrn_init__newnav8
#define _nrn_initial _nrn_initial__newnav8
#define nrn_cur _nrn_cur__newnav8
#define _nrn_current _nrn_current__newnav8
#define nrn_jacob _nrn_jacob__newnav8
#define nrn_state _nrn_state__newnav8
#define _net_receive _net_receive__newnav8 
#define _f_rates _f_rates__newnav8 
#define rates rates__newnav8 
#define states states__newnav8 
 
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
#define minfshift _p[1]
#define minfshift_columnindex 1
#define hinfshift _p[2]
#define hinfshift_columnindex 2
#define sinfshift _p[3]
#define sinfshift_columnindex 3
#define mtaushift _p[4]
#define mtaushift_columnindex 4
#define htaushift _p[5]
#define htaushift_columnindex 5
#define staushift _p[6]
#define staushift_columnindex 6
#define ina _p[7]
#define ina_columnindex 7
#define g _p[8]
#define g_columnindex 8
#define tau_m _p[9]
#define tau_m_columnindex 9
#define tau_h _p[10]
#define tau_h_columnindex 10
#define tau_s _p[11]
#define tau_s_columnindex 11
#define minf _p[12]
#define minf_columnindex 12
#define hinf _p[13]
#define hinf_columnindex 13
#define sinf _p[14]
#define sinf_columnindex 14
#define gp _p[15]
#define gp_columnindex 15
#define h _p[16]
#define h_columnindex 16
#define m _p[17]
#define m_columnindex 17
#define s _p[18]
#define s_columnindex 18
#define ena _p[19]
#define ena_columnindex 19
#define Dh _p[20]
#define Dh_columnindex 20
#define Dm _p[21]
#define Dm_columnindex 21
#define Ds _p[22]
#define Ds_columnindex 22
#define v _p[23]
#define v_columnindex 23
#define _g _p[24]
#define _g_columnindex 24
#define _ion_ena	*_ppvar[0]._pval
#define _ion_ina	*_ppvar[1]._pval
#define _ion_dinadv	*_ppvar[2]._pval
 
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
 "setdata_newnav8", _hoc_setdata,
 "rates_newnav8", _hoc_rates,
 0, 0
};
 
static void _check_rates(double*, Datum*, Datum*, NrnThread*); 
static void _check_table_thread(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, int _type) {
   _check_rates(_p, _ppvar, _thread, _nt);
 }
 /* declare global and static user variables */
#define q10 q10_newnav8
 double q10 = 3;
#define usetable usetable_newnav8
 double usetable = 1;
 /* some parameters have upper and lower limits */
 static HocParmLimits _hoc_parm_limits[] = {
 "usetable_newnav8", 0, 1,
 0,0,0
};
 static HocParmUnits _hoc_parm_units[] = {
 "gbar_newnav8", "S/cm2",
 "minfshift_newnav8", "mV",
 "hinfshift_newnav8", "mV",
 "sinfshift_newnav8", "mV",
 "mtaushift_newnav8", "ms",
 "htaushift_newnav8", "ms",
 "staushift_newnav8", "ms",
 "ina_newnav8", "mA/cm2",
 "g_newnav8", "S/cm2",
 "tau_m_newnav8", "ms",
 "tau_h_newnav8", "ms",
 0,0
};
 static double delta_t = 0.01;
 static double h0 = 0;
 static double m0 = 0;
 static double s0 = 0;
 /* connect global user variables to hoc */
 static DoubScal hoc_scdoub[] = {
 "q10_newnav8", &q10_newnav8,
 "usetable_newnav8", &usetable_newnav8,
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
 
#define _cvode_ieq _ppvar[3]._i
 static void _ode_matsol_instance1(_threadargsproto_);
 /* connect range variables in _p that hoc is supposed to know about */
 static const char *_mechanism[] = {
 "7.7.0",
"newnav8",
 "gbar_newnav8",
 "minfshift_newnav8",
 "hinfshift_newnav8",
 "sinfshift_newnav8",
 "mtaushift_newnav8",
 "htaushift_newnav8",
 "staushift_newnav8",
 0,
 "ina_newnav8",
 "g_newnav8",
 "tau_m_newnav8",
 "tau_h_newnav8",
 "tau_s_newnav8",
 "minf_newnav8",
 "hinf_newnav8",
 "sinf_newnav8",
 "gp_newnav8",
 0,
 "h_newnav8",
 "m_newnav8",
 "s_newnav8",
 0,
 0};
 static Symbol* _na_sym;
 
extern Prop* need_memb(Symbol*);

static void nrn_alloc(Prop* _prop) {
	Prop *prop_ion;
	double *_p; Datum *_ppvar;
 	_p = nrn_prop_data_alloc(_mechtype, 25, _prop);
 	/*initialize range parameters*/
 	gbar = 0;
 	minfshift = 0;
 	hinfshift = 0;
 	sinfshift = 0;
 	mtaushift = 0;
 	htaushift = 0;
 	staushift = 0;
 	_prop->param = _p;
 	_prop->param_size = 25;
 	_ppvar = nrn_prop_datum_alloc(_mechtype, 4, _prop);
 	_prop->dparam = _ppvar;
 	/*connect ionic variables to this model*/
 prop_ion = need_memb(_na_sym);
 nrn_promote(prop_ion, 0, 1);
 	_ppvar[0]._pval = &prop_ion->param[0]; /* ena */
 	_ppvar[1]._pval = &prop_ion->param[3]; /* ina */
 	_ppvar[2]._pval = &prop_ion->param[4]; /* _ion_dinadv */
 
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

 void _newNaV8_reg() {
	int _vectorized = 1;
  _initlists();
 	ion_reg("na", -10000.);
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
  hoc_register_prop_size(_mechtype, 25, 4);
  hoc_register_dparam_semantics(_mechtype, 0, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 1, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 2, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 3, "cvodeieq");
 	hoc_register_cvode(_mechtype, _ode_count, _ode_map, _ode_spec, _ode_matsol);
 	hoc_register_tolerance(_mechtype, _hoc_state_tol, &_atollist);
 	hoc_register_var(hoc_scdoub, hoc_vdoub, hoc_intfunc);
 	ivoc_help("help ?1 newnav8 newNaV8.mod\n");
 hoc_register_limits(_mechtype, _hoc_parm_limits);
 hoc_register_units(_mechtype, _hoc_parm_units);
 }
 static double *_t_minf;
 static double *_t_hinf;
 static double *_t_sinf;
 static double *_t_tau_m;
 static double *_t_tau_h;
 static double *_t_tau_s;
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
 static int _slist1[3], _dlist1[3];
 static int states(_threadargsproto_);
 
/*CVODE*/
 static int _ode_spec1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {int _reset = 0; {
   rates ( _threadargscomma_ v ) ;
   Dm = ( minf - m ) / ( tau_m ) ;
   Dh = ( hinf - h ) / ( tau_h ) ;
   Ds = ( sinf - s ) / ( tau_s ) ;
   }
 return _reset;
}
 static int _ode_matsol1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
 rates ( _threadargscomma_ v ) ;
 Dm = Dm  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( tau_m ) )) ;
 Dh = Dh  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( tau_h ) )) ;
 Ds = Ds  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( tau_s ) )) ;
  return 0;
}
 /*END CVODE*/
 static int states (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) { {
   rates ( _threadargscomma_ v ) ;
    m = m + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( tau_m ))))*(- ( ( ( minf ) ) / ( tau_m ) ) / ( ( ( ( - 1.0 ) ) ) / ( tau_m ) ) - m) ;
    h = h + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( tau_h ))))*(- ( ( ( hinf ) ) / ( tau_h ) ) / ( ( ( ( - 1.0 ) ) ) / ( tau_h ) ) - h) ;
    s = s + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( tau_s ))))*(- ( ( ( sinf ) ) / ( tau_s ) ) / ( ( ( ( - 1.0 ) ) ) / ( tau_s ) ) - s) ;
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
    _t_hinf[_i] = hinf;
    _t_sinf[_i] = sinf;
    _t_tau_m[_i] = tau_m;
    _t_tau_h[_i] = tau_h;
    _t_tau_s[_i] = tau_s;
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
  hinf = _xi;
  sinf = _xi;
  tau_m = _xi;
  tau_h = _xi;
  tau_s = _xi;
  return;
 }
 if (_xi <= 0.) {
 minf = _t_minf[0];
 hinf = _t_hinf[0];
 sinf = _t_sinf[0];
 tau_m = _t_tau_m[0];
 tau_h = _t_tau_h[0];
 tau_s = _t_tau_s[0];
 return; }
 if (_xi >= 440.) {
 minf = _t_minf[440];
 hinf = _t_hinf[440];
 sinf = _t_sinf[440];
 tau_m = _t_tau_m[440];
 tau_h = _t_tau_h[440];
 tau_s = _t_tau_s[440];
 return; }
 _i = (int) _xi;
 _theta = _xi - (double)_i;
 minf = _t_minf[_i] + _theta*(_t_minf[_i+1] - _t_minf[_i]);
 hinf = _t_hinf[_i] + _theta*(_t_hinf[_i+1] - _t_hinf[_i]);
 sinf = _t_sinf[_i] + _theta*(_t_sinf[_i+1] - _t_sinf[_i]);
 tau_m = _t_tau_m[_i] + _theta*(_t_tau_m[_i+1] - _t_tau_m[_i]);
 tau_h = _t_tau_h[_i] + _theta*(_t_tau_h[_i+1] - _t_tau_h[_i]);
 tau_s = _t_tau_s[_i] + _theta*(_t_tau_s[_i+1] - _t_tau_s[_i]);
 }

 
static int  _f_rates ( _threadargsprotocomma_ double _lVm ) {
   double _lQ10 ;
  _lQ10 = pow( q10 , ( ( celsius - 22.0 ) / 10.0 ) ) ;
   minf = pow( ( 1.0 / ( 1.0 + exp ( - 1.0 * ( _lVm + 4.0 ) / 7.0 ) ) ) , ( 1.0 / 3.0 ) ) ;
   hinf = 1.0 / ( 1.0 + exp ( ( _lVm + 28.0 ) / 4.56 ) ) ;
   sinf = 1.0 / ( 1.0 + exp ( ( _lVm + 50.0 ) / 7.5 ) ) ;
   tau_m = 0.03 + .5 / ( exp ( ( _lVm + 0.0 ) / 12.0 ) + exp ( - 1.0 * ( _lVm + 29.0 ) / 18.0 ) ) ;
   tau_h = 2.63 + 250.0 / ( exp ( ( _lVm + 36.0 ) / 7.7 ) + exp ( - 1.0 * ( _lVm + 0.0 ) / 16.3 ) ) + 1.4 / ( 1.0 + exp ( - 1.0 * ( _lVm + 0.6 ) / 2.95 ) ) ;
   tau_s = 34.0 / ( exp ( ( _lVm + 2.0 ) / 16.0 ) + exp ( - 1.0 * ( _lVm + 108.0 ) / 8.0 ) ) + 160.0 / ( 1.0 + exp ( - 1.0 * ( _lVm + 110.0 ) / 75.0 ) ) ;
   tau_m = tau_m / _lQ10 / 2.0 ;
   tau_h = tau_h / _lQ10 ;
   tau_s = tau_s / _lQ10 ;
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
 
static int _ode_count(int _type){ return 3;}
 
static void _ode_spec(NrnThread* _nt, _Memb_list* _ml, int _type) {
   double* _p; Datum* _ppvar; Datum* _thread;
   Node* _nd; double _v; int _iml, _cntml;
  _cntml = _ml->_nodecount;
  _thread = _ml->_thread;
  for (_iml = 0; _iml < _cntml; ++_iml) {
    _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
    _nd = _ml->_nodelist[_iml];
    v = NODEV(_nd);
  ena = _ion_ena;
     _ode_spec1 (_p, _ppvar, _thread, _nt);
  }}
 
static void _ode_map(int _ieq, double** _pv, double** _pvdot, double* _pp, Datum* _ppd, double* _atol, int _type) { 
	double* _p; Datum* _ppvar;
 	int _i; _p = _pp; _ppvar = _ppd;
	_cvode_ieq = _ieq;
	for (_i=0; _i < 3; ++_i) {
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
  ena = _ion_ena;
 _ode_matsol_instance1(_threadargs_);
 }}
 extern void nrn_update_ion_pointer(Symbol*, Datum*, int, int);
 static void _update_ion_pointer(Datum* _ppvar) {
   nrn_update_ion_pointer(_na_sym, _ppvar, 0, 0);
   nrn_update_ion_pointer(_na_sym, _ppvar, 1, 3);
   nrn_update_ion_pointer(_na_sym, _ppvar, 2, 4);
 }

static void initmodel(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
  int _i; double _save;{
  h = h0;
  m = m0;
  s = s0;
 {
   rates ( _threadargscomma_ v ) ;
   m = minf ;
   h = hinf ;
   s = sinf ;
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
  ena = _ion_ena;
 initmodel(_p, _ppvar, _thread, _nt);
 }
}

static double _nrn_current(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, double _v){double _current=0.;v=_v;{ {
   gp = m * m * m * h * s ;
   g = gbar * gp ;
   ina = g * ( v - ena ) ;
   }
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
  ena = _ion_ena;
 _g = _nrn_current(_p, _ppvar, _thread, _nt, _v + .001);
 	{ double _dina;
  _dina = ina;
 _rhs = _nrn_current(_p, _ppvar, _thread, _nt, _v);
  _ion_dinadv += (_dina - ina)/.001 ;
 	}
 _g = (_g - _rhs)/.001;
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
  ena = _ion_ena;
 {   states(_p, _ppvar, _thread, _nt);
  } }}

}

static void terminal(){}

static void _initlists(){
 double _x; double* _p = &_x;
 int _i; static int _first = 1;
  if (!_first) return;
 _slist1[0] = m_columnindex;  _dlist1[0] = Dm_columnindex;
 _slist1[1] = h_columnindex;  _dlist1[1] = Dh_columnindex;
 _slist1[2] = s_columnindex;  _dlist1[2] = Ds_columnindex;
   _t_minf = makevector(441*sizeof(double));
   _t_hinf = makevector(441*sizeof(double));
   _t_sinf = makevector(441*sizeof(double));
   _t_tau_m = makevector(441*sizeof(double));
   _t_tau_h = makevector(441*sizeof(double));
   _t_tau_s = makevector(441*sizeof(double));
_first = 0;
}

#if defined(__cplusplus)
} /* extern "C" */
#endif

#if NMODL_TEXT
static const char* nmodl_filename = "newNaV8.mod";
static const char* nmodl_file_text = 
  ": This channels is implemented by Jenny Tigerholm. \n"
  ":The steady state curves are collected from Winkelman 2005 \n"
  ":The time constat is from Gold 1996 and Safron 1996\n"
  ": To plot this model run KA_Winkelman.m\n"
  ": Adopted and altered by Nathan Titus\n"
  "\n"
  "NEURON {\n"
  "	SUFFIX newnav8\n"
  "	USEION na READ ena WRITE ina\n"
  "	RANGE gbar, ena, ina\n"
  "	RANGE tau_m, minf, hinf,tau_h, sinf, tau_s, m,h,s\n"
  "	RANGE minfshift, hinfshift, mtaushift, htaushift, ina\n"
  "	RANGE sinfshift, staushift, gp, g\n"
  "}\n"
  "\n"
  "UNITS {\n"
  "	(S) = (siemens)\n"
  "	(mV) = (millivolts)\n"
  "	(mA) = (milliamp)\n"
  "}\n"
  "\n"
  "PARAMETER {\n"
  "	gbar 	(S/cm2) \n"
  "    q10 = 3\n"
  "    minfshift = 0 (mV)\n"
  "	hinfshift = 0 (mV)\n"
  "	sinfshift = 0 (mV)\n"
  "	mtaushift = 0 (ms)\n"
  "	htaushift = 0 (ms)\n"
  "	staushift = 0 (ms)\n"
  "}\n"
  "\n"
  "ASSIGNED {\n"
  "	v	(mV) : NEURON provides this\n"
  "	ina	(mA/cm2)\n"
  "	g	(S/cm2)\n"
  "	tau_m	(ms)\n"
  "    tau_h   (ms)\n"
  "	tau_s\n"
  "    minf\n"
  "    hinf\n"
  "	sinf\n"
  "	gp\n"
  "    ena	(mV)\n"
  "	celsius (degC)\n"
  "}\n"
  "\n"
  "STATE { h m s}\n"
  "\n"
  "BREAKPOINT {\n"
  "	SOLVE states METHOD cnexp\n"
  "	gp = m*m*m*h*s\n"
  "	g = gbar*gp\n"
  "	ina = g * (v-ena)\n"
  "}\n"
  "\n"
  "INITIAL {\n"
  "	: assume that equilibrium has been reached\n"
  "    rates(v)    \n"
  "	m=minf\n"
  "    h=hinf\n"
  "	s=sinf\n"
  "\n"
  "}\n"
  "\n"
  "DERIVATIVE states {\n"
  "	rates(v)\n"
  "	\n"
  "	m' = (minf - m)/(tau_m)\n"
  "    h' = (hinf - h)/(tau_h)\n"
  "	s' = (sinf - s)/(tau_s)\n"
  "          \n"
  "}\n"
  "\n"
  "? rates\n"
  "PROCEDURE rates(Vm (mV)) {  \n"
  "	LOCAL Q10\n"
  "	TABLE minf,hinf,sinf,tau_m,tau_h,tau_s DEPEND celsius FROM -120 TO 100 WITH 440\n"
  "	\n"
  "UNITSOFF\n"
  "		Q10 = q10^((celsius-22)/10)\n"
  "        :minf = 1/(1+exp(-1*(Vm+3.3)/5.7))\n"
  "		:hinf = 1/(1+exp((Vm+44)/6.5))\n"
  "		:sinf = 1/(1+exp((Vm+32)/4.9))\n"
  "		minf = (1/(1+exp(-1*(Vm+4)/7)))^(1/3)\n"
  "		hinf = 1/(1+exp((Vm+28)/4.56))\n"
  "		sinf = 1/(1+exp((Vm+50)/7.5))\n"
  "		tau_m = 0.03 + .5/(exp((Vm+0)/12)+exp(-1*(Vm+29)/18)) \n"
  "		:tau_h = 2.3+7.9/(exp((Vm+28)/17.6)+exp(-1*(Vm+54)/23.3))\n"
  "		tau_h = 2.63+250/(exp((Vm+36)/7.7)+exp(-1*(Vm+0)/16.3)) + 1.4/(1+exp(-1*(Vm+0.6)/2.95))\n"
  "		tau_s = 34/(exp((Vm+2)/16)+exp(-1*(Vm+108)/8)) + 160/(1+exp(-1*(Vm+110)/75))\n"
  "		\n"
  "        tau_m=tau_m/Q10/2\n"
  "        tau_h=tau_h/Q10\n"
  "        tau_s=tau_s/Q10\n"
  "UNITSON\n"
  "}\n"
  ;
#endif

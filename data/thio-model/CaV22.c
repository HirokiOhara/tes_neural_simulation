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
 
#define nrn_init _nrn_init__cav22
#define _nrn_initial _nrn_initial__cav22
#define nrn_cur _nrn_cur__cav22
#define _nrn_current _nrn_current__cav22
#define nrn_jacob _nrn_jacob__cav22
#define nrn_state _nrn_state__cav22
#define _net_receive _net_receive__cav22 
#define _f_rates _f_rates__cav22 
#define rates rates__cav22 
#define states states__cav22 
 
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
#define q10 _p[1]
#define q10_columnindex 1
#define g _p[2]
#define g_columnindex 2
#define gp _p[3]
#define gp_columnindex 3
#define minf _p[4]
#define minf_columnindex 4
#define mtau _p[5]
#define mtau_columnindex 5
#define hinf _p[6]
#define hinf_columnindex 6
#define htau _p[7]
#define htau_columnindex 7
#define sinf _p[8]
#define sinf_columnindex 8
#define stau _p[9]
#define stau_columnindex 9
#define ica _p[10]
#define ica_columnindex 10
#define m _p[11]
#define m_columnindex 11
#define h _p[12]
#define h_columnindex 12
#define s _p[13]
#define s_columnindex 13
#define eca _p[14]
#define eca_columnindex 14
#define Dm _p[15]
#define Dm_columnindex 15
#define Dh _p[16]
#define Dh_columnindex 16
#define Ds _p[17]
#define Ds_columnindex 17
#define v _p[18]
#define v_columnindex 18
#define _g _p[19]
#define _g_columnindex 19
#define _ion_eca	*_ppvar[0]._pval
#define _ion_ica	*_ppvar[1]._pval
#define _ion_dicadv	*_ppvar[2]._pval
 
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
 "setdata_cav22", _hoc_setdata,
 "rates_cav22", _hoc_rates,
 0, 0
};
 
static void _check_rates(double*, Datum*, Datum*, NrnThread*); 
static void _check_table_thread(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, int _type) {
   _check_rates(_p, _ppvar, _thread, _nt);
 }
 /* declare global and static user variables */
#define usetable usetable_cav22
 double usetable = 1;
 /* some parameters have upper and lower limits */
 static HocParmLimits _hoc_parm_limits[] = {
 "usetable_cav22", 0, 1,
 0,0,0
};
 static HocParmUnits _hoc_parm_units[] = {
 "gbar_cav22", "S/cm2",
 "g_cav22", "S/cm2",
 "ica_cav22", "mA/cm2",
 0,0
};
 static double delta_t = 0.01;
 static double h0 = 0;
 static double m0 = 0;
 static double s0 = 0;
 /* connect global user variables to hoc */
 static DoubScal hoc_scdoub[] = {
 "usetable_cav22", &usetable_cav22,
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
"cav22",
 "gbar_cav22",
 "q10_cav22",
 0,
 "g_cav22",
 "gp_cav22",
 "minf_cav22",
 "mtau_cav22",
 "hinf_cav22",
 "htau_cav22",
 "sinf_cav22",
 "stau_cav22",
 "ica_cav22",
 0,
 "m_cav22",
 "h_cav22",
 "s_cav22",
 0,
 0};
 static Symbol* _ca_sym;
 
extern Prop* need_memb(Symbol*);

static void nrn_alloc(Prop* _prop) {
	Prop *prop_ion;
	double *_p; Datum *_ppvar;
 	_p = nrn_prop_data_alloc(_mechtype, 20, _prop);
 	/*initialize range parameters*/
 	gbar = 6.5e-09;
 	q10 = 3;
 	_prop->param = _p;
 	_prop->param_size = 20;
 	_ppvar = nrn_prop_datum_alloc(_mechtype, 4, _prop);
 	_prop->dparam = _ppvar;
 	/*connect ionic variables to this model*/
 prop_ion = need_memb(_ca_sym);
 nrn_promote(prop_ion, 0, 1);
 	_ppvar[0]._pval = &prop_ion->param[0]; /* eca */
 	_ppvar[1]._pval = &prop_ion->param[3]; /* ica */
 	_ppvar[2]._pval = &prop_ion->param[4]; /* _ion_dicadv */
 
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

 void _CaV22_reg() {
	int _vectorized = 1;
  _initlists();
 	ion_reg("ca", -10000.);
 	_ca_sym = hoc_lookup("ca_ion");
 	register_mech(_mechanism, nrn_alloc,nrn_cur, nrn_jacob, nrn_state, nrn_init, hoc_nrnpointerindex, 1);
 _mechtype = nrn_get_mechtype(_mechanism[1]);
     _nrn_setdata_reg(_mechtype, _setdata);
     _nrn_thread_reg(_mechtype, 2, _update_ion_pointer);
     _nrn_thread_table_reg(_mechtype, _check_table_thread);
 #if NMODL_TEXT
  hoc_reg_nmodl_text(_mechtype, nmodl_file_text);
  hoc_reg_nmodl_filename(_mechtype, nmodl_filename);
#endif
  hoc_register_prop_size(_mechtype, 20, 4);
  hoc_register_dparam_semantics(_mechtype, 0, "ca_ion");
  hoc_register_dparam_semantics(_mechtype, 1, "ca_ion");
  hoc_register_dparam_semantics(_mechtype, 2, "ca_ion");
  hoc_register_dparam_semantics(_mechtype, 3, "cvodeieq");
 	hoc_register_cvode(_mechtype, _ode_count, _ode_map, _ode_spec, _ode_matsol);
 	hoc_register_tolerance(_mechtype, _hoc_state_tol, &_atollist);
 	hoc_register_var(hoc_scdoub, hoc_vdoub, hoc_intfunc);
 	ivoc_help("help ?1 cav22 CaV22.mod\n");
 hoc_register_limits(_mechtype, _hoc_parm_limits);
 hoc_register_units(_mechtype, _hoc_parm_units);
 }
 static double *_t_minf;
 static double *_t_hinf;
 static double *_t_sinf;
 static double *_t_mtau;
 static double *_t_htau;
 static double *_t_stau;
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
   Dm = ( minf - m ) / ( mtau ) ;
   Dh = ( hinf - h ) / ( htau ) ;
   Ds = ( sinf - s ) / ( stau ) ;
   }
 return _reset;
}
 static int _ode_matsol1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
 rates ( _threadargscomma_ v ) ;
 Dm = Dm  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( mtau ) )) ;
 Dh = Dh  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( htau ) )) ;
 Ds = Ds  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( stau ) )) ;
  return 0;
}
 /*END CVODE*/
 static int states (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) { {
   rates ( _threadargscomma_ v ) ;
    m = m + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( mtau ))))*(- ( ( ( minf ) ) / ( mtau ) ) / ( ( ( ( - 1.0 ) ) ) / ( mtau ) ) - m) ;
    h = h + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( htau ))))*(- ( ( ( hinf ) ) / ( htau ) ) / ( ( ( ( - 1.0 ) ) ) / ( htau ) ) - h) ;
    s = s + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( stau ))))*(- ( ( ( sinf ) ) / ( stau ) ) / ( ( ( ( - 1.0 ) ) ) / ( stau ) ) - s) ;
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
    _t_mtau[_i] = mtau;
    _t_htau[_i] = htau;
    _t_stau[_i] = stau;
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
  mtau = _xi;
  htau = _xi;
  stau = _xi;
  return;
 }
 if (_xi <= 0.) {
 minf = _t_minf[0];
 hinf = _t_hinf[0];
 sinf = _t_sinf[0];
 mtau = _t_mtau[0];
 htau = _t_htau[0];
 stau = _t_stau[0];
 return; }
 if (_xi >= 440.) {
 minf = _t_minf[440];
 hinf = _t_hinf[440];
 sinf = _t_sinf[440];
 mtau = _t_mtau[440];
 htau = _t_htau[440];
 stau = _t_stau[440];
 return; }
 _i = (int) _xi;
 _theta = _xi - (double)_i;
 minf = _t_minf[_i] + _theta*(_t_minf[_i+1] - _t_minf[_i]);
 hinf = _t_hinf[_i] + _theta*(_t_hinf[_i+1] - _t_hinf[_i]);
 sinf = _t_sinf[_i] + _theta*(_t_sinf[_i+1] - _t_sinf[_i]);
 mtau = _t_mtau[_i] + _theta*(_t_mtau[_i+1] - _t_mtau[_i]);
 htau = _t_htau[_i] + _theta*(_t_htau[_i+1] - _t_htau[_i]);
 stau = _t_stau[_i] + _theta*(_t_stau[_i+1] - _t_stau[_i]);
 }

 
static int  _f_rates ( _threadargsprotocomma_ double _lVm ) {
   double _lQ10 ;
  _lQ10 = pow( q10 , ( ( celsius - 22.0 ) / 10.0 ) ) ;
   minf = pow( ( 1.0 / ( 1.0 + exp ( - 1.0 * ( _lVm + 4.0 ) / 7.5 ) ) ) , ( 1.0 / 3.0 ) ) ;
   hinf = 1.0 / ( 1.0 + exp ( ( _lVm + 48.0 ) / 7.0 ) ) ;
   sinf = 1.0 / ( 1.0 + exp ( ( _lVm + 81.0 ) / 8.6 ) ) ;
   mtau = .1 + 0.5 / ( exp ( ( _lVm - 3.0 ) / 6.7 ) + exp ( - 1.0 * ( _lVm + 37.0 ) / 13.5 ) ) ;
   htau = 36.0 / ( exp ( ( _lVm - 35.0 ) / 15.4 ) + exp ( - 1.0 * ( _lVm + 134.0 ) / 26.6 ) ) + 19.0 + 50.0 / ( 1.0 + exp ( ( _lVm + 50.0 ) / 10.0 ) ) ;
   htau = 10.0 / ( exp ( ( _lVm - 54.0 ) / 23.0 ) + exp ( - 1.0 * ( _lVm + 150.0 ) / 35.0 ) ) ;
   stau = 50.0 + 30.0 / ( exp ( ( _lVm - 50.0 ) / 26.0 ) + exp ( - 1.0 * ( _lVm + 150.0 ) / 26.0 ) ) ;
   mtau = mtau / _lQ10 ;
   htau = htau / _lQ10 ;
   stau = stau / _lQ10 ;
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
  eca = _ion_eca;
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
  eca = _ion_eca;
 _ode_matsol_instance1(_threadargs_);
 }}
 extern void nrn_update_ion_pointer(Symbol*, Datum*, int, int);
 static void _update_ion_pointer(Datum* _ppvar) {
   nrn_update_ion_pointer(_ca_sym, _ppvar, 0, 0);
   nrn_update_ion_pointer(_ca_sym, _ppvar, 1, 3);
   nrn_update_ion_pointer(_ca_sym, _ppvar, 2, 4);
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
  eca = _ion_eca;
 initmodel(_p, _ppvar, _thread, _nt);
 }
}

static double _nrn_current(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, double _v){double _current=0.;v=_v;{ {
   gp = m * m * m * h * s ;
   g = gbar * gp ;
   ica = g * ( v - eca ) ;
   }
 _current += ica;

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
  eca = _ion_eca;
 _g = _nrn_current(_p, _ppvar, _thread, _nt, _v + .001);
 	{ double _dica;
  _dica = ica;
 _rhs = _nrn_current(_p, _ppvar, _thread, _nt, _v);
  _ion_dicadv += (_dica - ica)/.001 ;
 	}
 _g = (_g - _rhs)/.001;
  _ion_ica += ica ;
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
  eca = _ion_eca;
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
   _t_mtau = makevector(441*sizeof(double));
   _t_htau = makevector(441*sizeof(double));
   _t_stau = makevector(441*sizeof(double));
_first = 0;
}

#if defined(__cplusplus)
} /* extern "C" */
#endif

#if NMODL_TEXT
static const char* nmodl_filename = "CaV22.mod";
static const char* nmodl_file_text = 
  ": N-Type Voltage Dependent Calcium Channel NOT FOR VAGAL AFFERENTS\n"
  "\n"
  ": Coded and modified by Nathan Titus 2018\n"
  ": Development Notes: Almost definitely a second inactivation gate or\n"
  ": concentration dependency. Insufficient data exists so inactivation tau\n"
  ": should be updated when more is understood about these channels.\n"
  "\n"
  "NEURON {\n"
  "	SUFFIX cav22\n"
  "	USEION ca READ eca WRITE ica\n"
  "	RANGE ica\n"
  "	RANGE gbar, minf, mtau, hinf, htau, sinf, stau\n"
  "	RANGE q10, gp, g\n"
  "}\n"
  "\n"
  "UNITS {\n"
  "    (molar) = (1/liter)                     : moles do not appear in units\n"
  "    (mM)    = (millimolar)             	\n"
  "	(uA) = (microamp)\n"
  "	(mA) = (milliamp)\n"
  "	(mV) = (millivolt)\n"
  "	(um) = (micron)\n"
  "	(S) = (siemens)\n"
  "\n"
  "}\n"
  "\n"
  "PARAMETER {\n"
  "	gbar = 6.5e-9 (S/cm2) :from Schild et al 1994\n"
  "	q10 = 3\n"
  "}\n"
  "\n"
  "ASSIGNED {\n"
  "	v (mV)\n"
  "	celsius (degC)\n"
  "	g (S/cm2)\n"
  "	gp\n"
  "	minf\n"
  "	mtau\n"
  "	hinf\n"
  "	htau\n"
  "	sinf\n"
  "	stau\n"
  "	ica (mA/cm2)\n"
  "	eca (mV)\n"
  "}\n"
  "\n"
  "\n"
  "INITIAL {\n"
  "	rates(v)\n"
  "	m = minf\n"
  "	h = hinf\n"
  "	s = sinf\n"
  "}\n"
  "\n"
  "STATE {\n"
  "	m h s\n"
  "}\n"
  "\n"
  "BREAKPOINT {\n"
  "	SOLVE states METHOD cnexp\n"
  "	gp = m*m*m*h*s\n"
  "	g = gbar*gp\n"
  "	ica = g*(v-eca)\n"
  "\n"
  "}\n"
  "\n"
  "DERIVATIVE states {\n"
  "	rates(v)\n"
  "	m' = (minf - m)/(mtau)    \n"
  "	h' = (hinf - h)/(htau)   \n"
  "	s' = (sinf - s)/(stau)    \n"
  "}\n"
  "\n"
  "? rates\n"
  "PROCEDURE rates(Vm (mV)) {  \n"
  "	LOCAL Q10\n"
  "	TABLE minf,hinf,sinf,mtau,htau,stau DEPEND celsius FROM -120 TO 100 WITH 440\n"
  "	\n"
  "UNITSOFF\n"
  "	Q10 = q10^((celsius-22)/10)	\n"
  "	:minf = 1/(1 + exp(-1*(Vm - 1.5)/6))\n"
  "	minf = (1/(1 + exp(-1*(Vm + 4)/7.5)))^(1/3)\n"
  "	:hinf = 1/(1 + exp((Vm + 61.5)/12))\n"
  "	hinf = 1/(1 + exp((Vm + 48)/7))\n"
  "	sinf = 1/(1 + exp((Vm + 81)/8.6))\n"
  "	mtau = .1 + 0.5/(exp((Vm-3)/6.7)+exp(-1*(Vm+37)/13.5))\n"
  "	htau = 36/(exp((Vm-35)/15.4)+exp(-1*(Vm+134)/26.6)) + 19 + 50/(1+exp((Vm+50)/10))\n"
  "	htau = 10/(exp((Vm-54)/23)+exp(-1*(Vm+150)/35))\n"
  "	stau = 50 + 30/(exp((Vm-50)/26)+exp(-1*(Vm+150)/26))\n"
  "\n"
  "	mtau = mtau/Q10\n"
  "	htau = htau/Q10\n"
  "	stau = stau/Q10\n"
  "	\n"
  "}\n"
  "\n"
  "UNITSON\n"
  ;
#endif

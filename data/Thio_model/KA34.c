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
 
#define nrn_init _nrn_init__ka34
#define _nrn_initial _nrn_initial__ka34
#define nrn_cur _nrn_cur__ka34
#define _nrn_current _nrn_current__ka34
#define nrn_jacob _nrn_jacob__ka34
#define nrn_state _nrn_state__ka34
#define _net_receive _net_receive__ka34 
#define _f_rates _f_rates__ka34 
#define rates rates__ka34 
#define states states__ka34 
 
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
#define mtaushift _p[3]
#define mtaushift_columnindex 3
#define htaushift _p[4]
#define htaushift_columnindex 4
#define ik _p[5]
#define ik_columnindex 5
#define g _p[6]
#define g_columnindex 6
#define tau_m _p[7]
#define tau_m_columnindex 7
#define tau_h _p[8]
#define tau_h_columnindex 8
#define minf _p[9]
#define minf_columnindex 9
#define hinf _p[10]
#define hinf_columnindex 10
#define gp _p[11]
#define gp_columnindex 11
#define h _p[12]
#define h_columnindex 12
#define m _p[13]
#define m_columnindex 13
#define ek _p[14]
#define ek_columnindex 14
#define Dh _p[15]
#define Dh_columnindex 15
#define Dm _p[16]
#define Dm_columnindex 16
#define v _p[17]
#define v_columnindex 17
#define _g _p[18]
#define _g_columnindex 18
#define _ion_ek	*_ppvar[0]._pval
#define _ion_ik	*_ppvar[1]._pval
#define _ion_dikdv	*_ppvar[2]._pval
 
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
 "setdata_ka34", _hoc_setdata,
 "rates_ka34", _hoc_rates,
 0, 0
};
 
static void _check_rates(double*, Datum*, Datum*, NrnThread*); 
static void _check_table_thread(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, int _type) {
   _check_rates(_p, _ppvar, _thread, _nt);
 }
 /* declare global and static user variables */
#define q10 q10_ka34
 double q10 = 3;
#define usetable usetable_ka34
 double usetable = 1;
 /* some parameters have upper and lower limits */
 static HocParmLimits _hoc_parm_limits[] = {
 "usetable_ka34", 0, 1,
 0,0,0
};
 static HocParmUnits _hoc_parm_units[] = {
 "gbar_ka34", "S/cm2",
 "minfshift_ka34", "mV",
 "hinfshift_ka34", "mV",
 "mtaushift_ka34", "ms",
 "htaushift_ka34", "ms",
 "ik_ka34", "mA/cm2",
 "g_ka34", "S/cm2",
 "tau_m_ka34", "ms",
 "tau_h_ka34", "ms",
 0,0
};
 static double delta_t = 0.01;
 static double h0 = 0;
 static double m0 = 0;
 /* connect global user variables to hoc */
 static DoubScal hoc_scdoub[] = {
 "q10_ka34", &q10_ka34,
 "usetable_ka34", &usetable_ka34,
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
"ka34",
 "gbar_ka34",
 "minfshift_ka34",
 "hinfshift_ka34",
 "mtaushift_ka34",
 "htaushift_ka34",
 0,
 "ik_ka34",
 "g_ka34",
 "tau_m_ka34",
 "tau_h_ka34",
 "minf_ka34",
 "hinf_ka34",
 "gp_ka34",
 0,
 "h_ka34",
 "m_ka34",
 0,
 0};
 static Symbol* _k_sym;
 
extern Prop* need_memb(Symbol*);

static void nrn_alloc(Prop* _prop) {
	Prop *prop_ion;
	double *_p; Datum *_ppvar;
 	_p = nrn_prop_data_alloc(_mechtype, 19, _prop);
 	/*initialize range parameters*/
 	gbar = 0;
 	minfshift = 0;
 	hinfshift = 0;
 	mtaushift = 0;
 	htaushift = 0;
 	_prop->param = _p;
 	_prop->param_size = 19;
 	_ppvar = nrn_prop_datum_alloc(_mechtype, 4, _prop);
 	_prop->dparam = _ppvar;
 	/*connect ionic variables to this model*/
 prop_ion = need_memb(_k_sym);
 nrn_promote(prop_ion, 0, 1);
 	_ppvar[0]._pval = &prop_ion->param[0]; /* ek */
 	_ppvar[1]._pval = &prop_ion->param[3]; /* ik */
 	_ppvar[2]._pval = &prop_ion->param[4]; /* _ion_dikdv */
 
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

 void _KA34_reg() {
	int _vectorized = 1;
  _initlists();
 	ion_reg("k", -10000.);
 	_k_sym = hoc_lookup("k_ion");
 	register_mech(_mechanism, nrn_alloc,nrn_cur, nrn_jacob, nrn_state, nrn_init, hoc_nrnpointerindex, 1);
 _mechtype = nrn_get_mechtype(_mechanism[1]);
     _nrn_setdata_reg(_mechtype, _setdata);
     _nrn_thread_reg(_mechtype, 2, _update_ion_pointer);
     _nrn_thread_table_reg(_mechtype, _check_table_thread);
 #if NMODL_TEXT
  hoc_reg_nmodl_text(_mechtype, nmodl_file_text);
  hoc_reg_nmodl_filename(_mechtype, nmodl_filename);
#endif
  hoc_register_prop_size(_mechtype, 19, 4);
  hoc_register_dparam_semantics(_mechtype, 0, "k_ion");
  hoc_register_dparam_semantics(_mechtype, 1, "k_ion");
  hoc_register_dparam_semantics(_mechtype, 2, "k_ion");
  hoc_register_dparam_semantics(_mechtype, 3, "cvodeieq");
 	hoc_register_cvode(_mechtype, _ode_count, _ode_map, _ode_spec, _ode_matsol);
 	hoc_register_tolerance(_mechtype, _hoc_state_tol, &_atollist);
 	hoc_register_var(hoc_scdoub, hoc_vdoub, hoc_intfunc);
 	ivoc_help("help ?1 ka34 KA34.mod\n");
 hoc_register_limits(_mechtype, _hoc_parm_limits);
 hoc_register_units(_mechtype, _hoc_parm_units);
 }
 static double *_t_minf;
 static double *_t_hinf;
 static double *_t_tau_m;
 static double *_t_tau_h;
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
   Dh = ( hinf - h ) / ( tau_h ) ;
   }
 return _reset;
}
 static int _ode_matsol1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
 rates ( _threadargscomma_ v ) ;
 Dm = Dm  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( tau_m ) )) ;
 Dh = Dh  / (1. - dt*( ( ( ( - 1.0 ) ) ) / ( tau_h ) )) ;
  return 0;
}
 /*END CVODE*/
 static int states (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) { {
   rates ( _threadargscomma_ v ) ;
    m = m + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( tau_m ))))*(- ( ( ( minf ) ) / ( tau_m ) ) / ( ( ( ( - 1.0 ) ) ) / ( tau_m ) ) - m) ;
    h = h + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / ( tau_h ))))*(- ( ( ( hinf ) ) / ( tau_h ) ) / ( ( ( ( - 1.0 ) ) ) / ( tau_h ) ) - h) ;
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
    _t_tau_m[_i] = tau_m;
    _t_tau_h[_i] = tau_h;
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
  tau_m = _xi;
  tau_h = _xi;
  return;
 }
 if (_xi <= 0.) {
 minf = _t_minf[0];
 hinf = _t_hinf[0];
 tau_m = _t_tau_m[0];
 tau_h = _t_tau_h[0];
 return; }
 if (_xi >= 440.) {
 minf = _t_minf[440];
 hinf = _t_hinf[440];
 tau_m = _t_tau_m[440];
 tau_h = _t_tau_h[440];
 return; }
 _i = (int) _xi;
 _theta = _xi - (double)_i;
 minf = _t_minf[_i] + _theta*(_t_minf[_i+1] - _t_minf[_i]);
 hinf = _t_hinf[_i] + _theta*(_t_hinf[_i+1] - _t_hinf[_i]);
 tau_m = _t_tau_m[_i] + _theta*(_t_tau_m[_i+1] - _t_tau_m[_i]);
 tau_h = _t_tau_h[_i] + _theta*(_t_tau_h[_i+1] - _t_tau_h[_i]);
 }

 
static int  _f_rates ( _threadargsprotocomma_ double _lVm ) {
   double _lQ10 ;
  _lQ10 = pow( q10 , ( ( celsius - 22.0 ) / 10.0 ) ) ;
   minf = pow( ( 1.0 / ( 1.0 + exp ( - 1.0 * ( _lVm - 24.0 ) / 17.0 ) ) ) , ( 1.0 / 3.0 ) ) ;
   hinf = 1.0 / ( 1.0 + exp ( ( _lVm + 31.0 ) / 12.0 ) ) ;
   tau_m = ( 1.0 / ( exp ( ( _lVm - 39.0 ) / 13.0 ) + exp ( - 1.0 * ( _lVm + 134.0 ) / 47.0 ) ) ) / 2.0 ;
   tau_h = 15.0 + 1.0 / ( exp ( ( _lVm - 60.0 ) / 15.0 ) + exp ( - 1.0 * ( _lVm + 300.0 ) / 27.0 ) ) ;
   tau_m = tau_m / _lQ10 ;
   tau_h = tau_h / _lQ10 ;
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
 _ode_matsol_instance1(_threadargs_);
 }}
 extern void nrn_update_ion_pointer(Symbol*, Datum*, int, int);
 static void _update_ion_pointer(Datum* _ppvar) {
   nrn_update_ion_pointer(_k_sym, _ppvar, 0, 0);
   nrn_update_ion_pointer(_k_sym, _ppvar, 1, 3);
   nrn_update_ion_pointer(_k_sym, _ppvar, 2, 4);
 }

static void initmodel(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
  int _i; double _save;{
  h = h0;
  m = m0;
 {
   rates ( _threadargscomma_ v ) ;
   m = minf ;
   h = hinf ;
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
 initmodel(_p, _ppvar, _thread, _nt);
 }
}

static double _nrn_current(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, double _v){double _current=0.;v=_v;{ {
   gp = m * m * m * h ;
   g = gbar * gp ;
   ik = g * ( v - ek ) ;
   }
 _current += ik;

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
 _g = _nrn_current(_p, _ppvar, _thread, _nt, _v + .001);
 	{ double _dik;
  _dik = ik;
 _rhs = _nrn_current(_p, _ppvar, _thread, _nt, _v);
  _ion_dikdv += (_dik - ik)/.001 ;
 	}
 _g = (_g - _rhs)/.001;
  _ion_ik += ik ;
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
   _t_minf = makevector(441*sizeof(double));
   _t_hinf = makevector(441*sizeof(double));
   _t_tau_m = makevector(441*sizeof(double));
   _t_tau_h = makevector(441*sizeof(double));
_first = 0;
}

#if defined(__cplusplus)
} /* extern "C" */
#endif

#if NMODL_TEXT
static const char* nmodl_filename = "KA34.mod";
static const char* nmodl_file_text = 
  ": This channels is implemented by Jenny Tigerholm. \n"
  ":The steady state curves are collected from Winkelman 2005 \n"
  ":The time constat is from Gold 1996 and Safron 1996\n"
  ": To plot this model run KA_Winkelman.m\n"
  ": Adopted and altered by Nathan Titus\n"
  "\n"
  "NEURON {\n"
  "	SUFFIX ka34\n"
  "	USEION k READ ek WRITE ik\n"
  "	RANGE gbar, ek, ik\n"
  "	RANGE tau_m, minf, hinf,tau_h,m,h, gp, g\n"
  "	RANGE minfshift, hinfshift, mtaushift, htaushift, ik\n"
  "	\n"
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
  "	mtaushift = 0 (ms)\n"
  "	htaushift = 0 (ms)\n"
  "}\n"
  "\n"
  "ASSIGNED {\n"
  "	v	(mV) : NEURON provides this\n"
  "	ik	(mA/cm2)\n"
  "	g	(S/cm2)\n"
  "	tau_m	(ms)\n"
  "    tau_h   (ms)\n"
  "    minf\n"
  "    hinf\n"
  "	gp\n"
  "    ek	(mV)\n"
  "	celsius (degC)\n"
  "}\n"
  "\n"
  "STATE { h m }\n"
  "\n"
  "BREAKPOINT {\n"
  "	SOLVE states METHOD cnexp\n"
  "	gp = m*m*m*h\n"
  "	g = gbar*gp\n"
  "	ik = g * (v-ek)\n"
  "}\n"
  "\n"
  "INITIAL {\n"
  "	: assume that equilibrium has been reached\n"
  "    rates(v)    \n"
  "	m=minf\n"
  "    h=hinf\n"
  "\n"
  "}\n"
  "\n"
  "DERIVATIVE states {\n"
  "	rates(v)\n"
  "	m' = (minf - m)/(tau_m)\n"
  "    h' = (hinf - h)/(tau_h)\n"
  "          \n"
  "}\n"
  "\n"
  "? rates\n"
  "PROCEDURE rates(Vm (mV)) (/ms) {    \n"
  "	LOCAL Q10\n"
  "		TABLE minf,hinf,tau_m,tau_h DEPEND celsius FROM -120 TO 100 WITH 440\n"
  "UNITSOFF	\n"
  "		Q10 = q10^((celsius-22)/10)\n"
  "        :minf=1/(1+exp(-1*(Vm+16.8-minfshift)/20.7))\n"
  "		:minf=1/(1+exp(-1*(Vm-28-minfshift)/25.3))\n"
  "        :hinf=1/(1+exp((Vm+74-hinfshift)/14))\n"
  "		:hinf=1/(1+exp((Vm+29-hinfshift)/8))\n"
  "        :tau_m=6.09/(exp((Vm+33.64)/6.7)+exp(-1*(Vm+46.6)/14.71)) + 2.5/(1+exp((Vm-26.2)/21.55))\n"
  "        :tau_m=0.66 + 1/(0.13*exp((Vm-mtaushift)/13.0) + 0.04*exp(-1*(Vm-mtaushift)/39.3))\n"
  "		:tau_h= 1*(4 + 82.59/(exp((Vm+83.39)/9.046)^2 + exp(-1*(Vm+101.6)/30)) + 15/(1+exp((Vm+42.58)/20.79)))\n"
  "		:tau_h=9+24.04*exp(-1*(Vm-htaushift)/23.2)\n"
  "		:tau_h=10+33.51/(exp((Vm+0.03-htaushift)/12.6)+exp(-1*(Vm+128.7-htaushift)/7.824))\n"
  "		\n"
  "		minf = (1/(1+exp(-1*(Vm-24)/17)))^(1/3)\n"
  "		hinf = 1/(1+exp((Vm+31)/12))\n"
  "		tau_m = (1/(exp((Vm-39)/13)+exp(-1*(Vm+134)/47)))/2\n"
  "		tau_h = 15 + 1/(exp((Vm-60)/15)+exp(-1*(Vm+300)/27)) :The vertical offset seems too large compared to current plots\n"
  "		\n"
  "        tau_m=tau_m/Q10\n"
  "        tau_h=tau_h/Q10\n"
  "UNITSON\n"
  "\n"
  "}\n"
  ;
#endif

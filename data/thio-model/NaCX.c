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
 
#define nrn_init _nrn_init__nacx
#define _nrn_initial _nrn_initial__nacx
#define nrn_cur _nrn_cur__nacx
#define _nrn_current _nrn_current__nacx
#define nrn_jacob _nrn_jacob__nacx
#define nrn_state _nrn_state__nacx
#define _net_receive _net_receive__nacx 
 
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
#define knaca _p[0]
#define knaca_columnindex 0
#define dnaca _p[1]
#define dnaca_columnindex 1
#define R _p[2]
#define R_columnindex 2
#define F _p[3]
#define F_columnindex 3
#define gbar _p[4]
#define gbar_columnindex 4
#define ina _p[5]
#define ina_columnindex 5
#define ica _p[6]
#define ica_columnindex 6
#define icana _p[7]
#define icana_columnindex 7
#define nai _p[8]
#define nai_columnindex 8
#define nao _p[9]
#define nao_columnindex 9
#define cai _p[10]
#define cai_columnindex 10
#define cao _p[11]
#define cao_columnindex 11
#define inaca _p[12]
#define inaca_columnindex 12
#define v _p[13]
#define v_columnindex 13
#define _g _p[14]
#define _g_columnindex 14
#define _ion_nai	*_ppvar[0]._pval
#define _ion_nao	*_ppvar[1]._pval
#define _ion_ina	*_ppvar[2]._pval
#define _ion_dinadv	*_ppvar[3]._pval
#define _ion_cao	*_ppvar[4]._pval
#define _ion_cai	*_ppvar[5]._pval
#define _ion_ica	*_ppvar[6]._pval
#define _ion_dicadv	*_ppvar[7]._pval
 
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
 "setdata_nacx", _hoc_setdata,
 "rates_nacx", _hoc_rates,
 0, 0
};
#define rates rates_nacx
 extern double rates( _threadargsprotocomma_ double );
 /* declare global and static user variables */
 /* some parameters have upper and lower limits */
 static HocParmLimits _hoc_parm_limits[] = {
 0,0,0
};
 static HocParmUnits _hoc_parm_units[] = {
 "R_nacx", "mV",
 "gbar_nacx", "1/cm2",
 "ina_nacx", "mA/cm2",
 "ica_nacx", "mA/cm2",
 "icana_nacx", "mA/cm2",
 0,0
};
 /* connect global user variables to hoc */
 static DoubScal hoc_scdoub[] = {
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
 /* connect range variables in _p that hoc is supposed to know about */
 static const char *_mechanism[] = {
 "7.7.0",
"nacx",
 "knaca_nacx",
 "dnaca_nacx",
 "R_nacx",
 "F_nacx",
 "gbar_nacx",
 0,
 "ina_nacx",
 "ica_nacx",
 "icana_nacx",
 0,
 0,
 0};
 static Symbol* _na_sym;
 static Symbol* _ca_sym;
 
extern Prop* need_memb(Symbol*);

static void nrn_alloc(Prop* _prop) {
	Prop *prop_ion;
	double *_p; Datum *_ppvar;
 	_p = nrn_prop_data_alloc(_mechtype, 15, _prop);
 	/*initialize range parameters*/
 	knaca = 3.6e-08;
 	dnaca = 0.0036;
 	R = 8314;
 	F = 96500;
 	gbar = 316;
 	_prop->param = _p;
 	_prop->param_size = 15;
 	_ppvar = nrn_prop_datum_alloc(_mechtype, 8, _prop);
 	_prop->dparam = _ppvar;
 	/*connect ionic variables to this model*/
 prop_ion = need_memb(_na_sym);
 nrn_promote(prop_ion, 1, 0);
 	_ppvar[0]._pval = &prop_ion->param[1]; /* nai */
 	_ppvar[1]._pval = &prop_ion->param[2]; /* nao */
 	_ppvar[2]._pval = &prop_ion->param[3]; /* ina */
 	_ppvar[3]._pval = &prop_ion->param[4]; /* _ion_dinadv */
 prop_ion = need_memb(_ca_sym);
 nrn_promote(prop_ion, 1, 0);
 	_ppvar[4]._pval = &prop_ion->param[2]; /* cao */
 	_ppvar[5]._pval = &prop_ion->param[1]; /* cai */
 	_ppvar[6]._pval = &prop_ion->param[3]; /* ica */
 	_ppvar[7]._pval = &prop_ion->param[4]; /* _ion_dicadv */
 
}
 static void _initlists();
 static void _update_ion_pointer(Datum*);
 extern Symbol* hoc_lookup(const char*);
extern void _nrn_thread_reg(int, int, void(*)(Datum*));
extern void _nrn_thread_table_reg(int, void(*)(double*, Datum*, Datum*, NrnThread*, int));
extern void hoc_register_tolerance(int, HocStateTolerance*, Symbol***);
extern void _cvode_abstol( Symbol**, double*, int);

 void _NaCX_reg() {
	int _vectorized = 1;
  _initlists();
 	ion_reg("na", -10000.);
 	ion_reg("ca", -10000.);
 	_na_sym = hoc_lookup("na_ion");
 	_ca_sym = hoc_lookup("ca_ion");
 	register_mech(_mechanism, nrn_alloc,nrn_cur, nrn_jacob, nrn_state, nrn_init, hoc_nrnpointerindex, 1);
 _mechtype = nrn_get_mechtype(_mechanism[1]);
     _nrn_setdata_reg(_mechtype, _setdata);
     _nrn_thread_reg(_mechtype, 2, _update_ion_pointer);
 #if NMODL_TEXT
  hoc_reg_nmodl_text(_mechtype, nmodl_file_text);
  hoc_reg_nmodl_filename(_mechtype, nmodl_filename);
#endif
  hoc_register_prop_size(_mechtype, 15, 8);
  hoc_register_dparam_semantics(_mechtype, 0, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 1, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 2, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 3, "na_ion");
  hoc_register_dparam_semantics(_mechtype, 4, "ca_ion");
  hoc_register_dparam_semantics(_mechtype, 5, "ca_ion");
  hoc_register_dparam_semantics(_mechtype, 6, "ca_ion");
  hoc_register_dparam_semantics(_mechtype, 7, "ca_ion");
 	hoc_register_var(hoc_scdoub, hoc_vdoub, hoc_intfunc);
 	ivoc_help("help ?1 nacx NaCX.mod\n");
 hoc_register_limits(_mechtype, _hoc_parm_limits);
 hoc_register_units(_mechtype, _hoc_parm_units);
 }
static int _reset;
static char *modelname = "";

static int error;
static int _ninits = 0;
static int _match_recurse=1;
static void _modl_cleanup(){ _match_recurse=1;}
 
double rates ( _threadargsprotocomma_ double _lVm ) {
   double _lrates;
 double _lq10 , _lT , _ldfcain , _ldfcaout , _ls ;
 _lT = 273.0 + celsius ;
   _lq10 = ( 2.2 * ( _lT - 296.0 ) + ( 310.0 - _lT ) ) / 14.0 ;
   _ldfcain = pow( nai , 3.0 ) * cao * exp ( 0.5 * _lVm * F / ( R * _lT ) ) ;
   _ldfcaout = pow( nao , 3.0 ) * cai * exp ( - 0.5 * _lVm * F / ( R * _lT ) ) ;
   _ls = 1.0 + dnaca * ( cai * pow( nao , 3.0 ) + cao * pow( nai , 3.0 ) ) ;
   inaca = gbar * _lq10 * knaca * ( _ldfcain - _ldfcaout ) / _ls ;
   
return _lrates;
 }
 
static void _hoc_rates(void) {
  double _r;
   double* _p; Datum* _ppvar; Datum* _thread; NrnThread* _nt;
   if (_extcall_prop) {_p = _extcall_prop->param; _ppvar = _extcall_prop->dparam;}else{ _p = (double*)0; _ppvar = (Datum*)0; }
  _thread = _extcall_thread;
  _nt = nrn_threads;
 _r =  rates ( _p, _ppvar, _thread, _nt, *getarg(1) );
 hoc_retpushx(_r);
}
 extern void nrn_update_ion_pointer(Symbol*, Datum*, int, int);
 static void _update_ion_pointer(Datum* _ppvar) {
   nrn_update_ion_pointer(_na_sym, _ppvar, 0, 1);
   nrn_update_ion_pointer(_na_sym, _ppvar, 1, 2);
   nrn_update_ion_pointer(_na_sym, _ppvar, 2, 3);
   nrn_update_ion_pointer(_na_sym, _ppvar, 3, 4);
   nrn_update_ion_pointer(_ca_sym, _ppvar, 4, 2);
   nrn_update_ion_pointer(_ca_sym, _ppvar, 5, 1);
   nrn_update_ion_pointer(_ca_sym, _ppvar, 6, 3);
   nrn_update_ion_pointer(_ca_sym, _ppvar, 7, 4);
 }

static void initmodel(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
  int _i; double _save;{
 {
   rates ( _threadargscomma_ v ) ;
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
  nai = _ion_nai;
  nao = _ion_nao;
  cao = _ion_cao;
  cai = _ion_cai;
 initmodel(_p, _ppvar, _thread, _nt);
  }
}

static double _nrn_current(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, double _v){double _current=0.;v=_v;{ {
   rates ( _threadargscomma_ v ) ;
   icana = inaca ;
   ina = 3.0 * inaca ;
   ica = - 2.0 * inaca ;
   }
 _current += ina;
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
  nai = _ion_nai;
  nao = _ion_nao;
  cao = _ion_cao;
  cai = _ion_cai;
 _g = _nrn_current(_p, _ppvar, _thread, _nt, _v + .001);
 	{ double _dica;
 double _dina;
  _dina = ina;
  _dica = ica;
 _rhs = _nrn_current(_p, _ppvar, _thread, _nt, _v);
  _ion_dinadv += (_dina - ina)/.001 ;
  _ion_dicadv += (_dica - ica)/.001 ;
 	}
 _g = (_g - _rhs)/.001;
  _ion_ina += ina ;
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

}

static void terminal(){}

static void _initlists(){
 double _x; double* _p = &_x;
 int _i; static int _first = 1;
  if (!_first) return;
_first = 0;
}

#if defined(__cplusplus)
} /* extern "C" */
#endif

#if NMODL_TEXT
static const char* nmodl_filename = "NaCX.mod";
static const char* nmodl_file_text = 
  ": Based on Schild et al 1994\n"
  "\n"
  ": Sodium Calcium Exchanger\n"
  "\n"
  ": Coded and modified by Nathan Titus 2018\n"
  ": Development Notes: cao, nao, and ko are actually \n"
  ": concentrations in the perineuronal space\n"
  ":\n"
  ":\n"
  "\n"
  "NEURON {\n"
  "	SUFFIX nacx\n"
  "	USEION na READ nai,nao WRITE ina\n"
  "	USEION ca READ cao,cai WRITE ica\n"
  "	RANGE ina,ica, icana\n"
  "	RANGE knaca, dnaca, R, F, gbar\n"
  "}\n"
  "\n"
  "UNITS {\n"
  "    (molar) = (1/liter)                     : moles do not appear in units\n"
  "    (mM)    = (millimolar)             	\n"
  "	(uA) = (microamp)\n"
  "	(mA) = (milliamp)\n"
  "	(mV) = (millivolt)\n"
  "	(um) = (micron)\n"
  "\n"
  "}\n"
  "\n"
  "PARAMETER {\n"
  "	knaca = 36e-9 :(uA/(mM^4))\n"
  "	dnaca = .0036 :(1/(mM^4))\n"
  "	R = 8314 (mV)\n"
  "	F = 96500  \n"
  "	gbar = 316 (1/cm2) :converts from uA to mA/cm^2, 3 uA/cm^2 for cai=.0002 and cao=2\n"
  "\n"
  "}\n"
  "\n"
  "ASSIGNED {\n"
  "	v (mV)\n"
  "	nai (mM)\n"
  "	nao (mM)\n"
  "	cai (mM)\n"
  "	cao (mM)\n"
  "	ina (mA/cm2)\n"
  "	ica (mA/cm2)\n"
  "	celsius (degC)\n"
  "	icana (mA/cm2)\n"
  "	inaca (mA/cm2)\n"
  "}\n"
  "\n"
  "\n"
  "INITIAL {\n"
  "	rates(v)\n"
  "}\n"
  "\n"
  "BREAKPOINT {\n"
  "	rates(v)\n"
  "	icana = inaca\n"
  "	ina = 3*inaca		\n"
  "	ica = -2*inaca\n"
  "\n"
  "}\n"
  "\n"
  "UNITSOFF\n"
  "FUNCTION rates(Vm (mV)) {    \n"
  "	LOCAL q10, T, dfcain, dfcaout, s\n"
  "	T = 273 + celsius\n"
  "	q10 = (2.2*(T-296.0)+(310.0-T))/14.0\n"
  "	dfcain = nai^3*cao*exp(0.5*Vm*F/(R*T))\n"
  "	dfcaout = nao^3*cai*exp(-0.5*Vm*F/(R*T))\n"
  "	s = 1 + dnaca*(cai*nao^3 + cao*nai^3)\n"
  "	inaca = gbar*q10*knaca*(dfcain-dfcaout)/s\n"
  "}\n"
  "UNITSON\n"
  "\n"
  ;
#endif
